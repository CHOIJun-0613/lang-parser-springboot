"""
AI 분석 서비스 모듈
LLM을 사용하여 Class, Method, SQL의 특징을 분석합니다.
"""

import asyncio
import logging
import re
import time

from .ai_config import ai_config
from .ai_providers import ai_provider_manager
from .prompt import get_prompt

logger = logging.getLogger(__name__)


class AIAnalyzer:
    """AI 기반 코드 분석 서비스"""

    def __init__(self):
        """AI Analyzer 초기화"""
        self.config = ai_config
        self.provider_manager = ai_provider_manager
        self._llm = None
        self._is_available = False

        # AI 사용 여부 확인
        if not self.config.ai_use_analysis:
            logger.info("AI 분석이 비활성화되어 있습니다 (AI_USE_ANALYSIS=false)")
            return

        # LLM 초기화 시도
        try:
            self._llm = self.provider_manager.create_llm()
            self._is_available = True
            logger.info(f"AI 분석 초기화 완료: {self.config.ai_provider} / {self.config.get_current_model_name()}")
        except Exception as e:
            logger.warning(f"AI 분석 초기화 실패: {e}")
            self._is_available = False

    def is_available(self) -> bool:
        """AI 분석 사용 가능 여부 확인"""
        return self._is_available

    def _is_retryable_error(self, exception: Exception, error_msg: str) -> bool:
        """
        재시도 가능한 에러인지 확인합니다 (503, 429).

        Args:
            exception: 발생한 예외 객체
            error_msg: 에러 메시지

        Returns:
            재시도 가능한 에러이면 True, 아니면 False
        """
        error_msg_lower = error_msg.lower()

        # 1. 서비스 일시 불가 (503 UNAVAILABLE)
        if '503' in error_msg or 'unavailable' in error_msg_lower or 'service unavailable' in error_msg_lower:
            logger.warning("서비스 일시 불가 감지 (503 UNAVAILABLE)")
            logger.warning("  - Gemini 서비스가 일시적으로 사용 불가능합니다")
            logger.warning("  - 대기 후 자동으로 재시도합니다 (1회=10초, 2회=20초, 3회=30초)")
            return True

        # 2. Rate Limit 초과 (429 RESOURCE_EXHAUSTED)
        if '429' in error_msg or 'resource_exhausted' in error_msg_lower:
            logger.warning("Rate Limit 초과 감지 (429 RESOURCE_EXHAUSTED)")
            logger.warning("  - 분당 요청 수(RPM) 또는 분당 토큰 수(TPM) 초과")
            logger.warning("  - 대기 시간을 점진적으로 늘려 재시도합니다 (1회=10초, 2회=20초, 3회=30초)")
            return True

        return False

    def _is_non_retryable_error(self, exception: Exception, error_msg: str) -> bool:
        """
        재시도하면 안 되는 에러인지 확인합니다.

        Args:
            exception: 발생한 예외 객체
            error_msg: 에러 메시지

        Returns:
            재시도하면 안 되는 에러이면 True, 재시도 가능하면 False
        """
        # 에러 메시지를 소문자로 변환하여 검사
        error_msg_lower = error_msg.lower()

        # 1. 인증 실패 (401 UNAUTHENTICATED)
        if '401' in error_msg or 'unauthenticated' in error_msg_lower or 'unauthorized' in error_msg_lower:
            logger.warning("인증 실패 감지 (401 UNAUTHENTICATED)")
            logger.warning("  - API 키가 유효하지 않거나 만료되었습니다")
            logger.warning("  - .env 파일의 GOOGLE_API_KEY를 확인하세요")
            return True

        # 2. 권한 없음 (403 PERMISSION_DENIED)
        if '403' in error_msg or 'permission_denied' in error_msg_lower or 'forbidden' in error_msg_lower:
            logger.warning("권한 없음 감지 (403 PERMISSION_DENIED)")
            logger.warning("  - 해당 API를 사용할 권한이 없습니다")
            logger.warning("  - Google Cloud 프로젝트 설정을 확인하세요")
            return True

        # 3. 잘못된 요청 (400 INVALID_ARGUMENT)
        if '400' in error_msg or 'invalid_argument' in error_msg_lower or 'bad request' in error_msg_lower:
            logger.warning("잘못된 요청 감지 (400 INVALID_ARGUMENT)")
            logger.warning("  - 요청 형식이나 파라미터가 잘못되었습니다")
            return True

        # 4. API 키 관련 에러
        if 'api key' in error_msg_lower or 'api_key' in error_msg_lower:
            logger.warning("API 키 관련 에러 감지")
            logger.warning("  - .env 파일의 GOOGLE_API_KEY를 확인하세요")
            return True

        return False

    def _call_llm(self, input_text: str, max_retries: int = 3, retry_delay: int = 10) -> str:
        """
        LLM을 호출하여 결과를 반환합니다.
        Provider별로 다른 메서드를 시도합니다.

        Args:
            input_text: LLM에 전달할 입력 텍스트
            max_retries: 최대 재시도 횟수 (기본값: 3, 총 4회 시도)
            retry_delay: 재시도 기본 간격 (초, 기본값: 10, 재시도마다 10초씩 증가)
                - 1회 실패 → 10초 sleep → 2회 시도
                - 2회 실패 → 20초 sleep → 3회 시도
                - 3회 실패 → 30초 sleep → 4회 시도
                - 4회 실패 → 오류 처리

        Returns:
            LLM 응답 문자열
        """
        # 사용 가능한 모든 메서드 확인 (디버그용)
        all_methods = dir(self._llm)
        available_methods = [m for m in all_methods if callable(getattr(self._llm, m, None))]

        # 각 메서드 시도 결과 기록
        failed_attempts = []

        # Google ADK Gemini용 메서드 추가
        methods_to_try = [
            '__call__',              # Callable 객체 (우선순위 1)
            'generate_content',      # Google ADK Gemini 동기 메서드
            'invoke',                # LangChain 스타일
            'generate',              # 일반적인 메서드명
            'predict',               # 일반적인 메서드명
            'run',                   # 일반적인 메서드명
        ]

        for method_name in methods_to_try:
            if hasattr(self._llm, method_name):
                retry_count = 0

                while retry_count <= max_retries:
                    try:
                        method = getattr(self._llm, method_name)
                        if method_name == '__call__':
                            result = self._llm(input_text)
                        else:
                            result = method(input_text)

                        # 결과 추출
                        if hasattr(result, 'content'):
                            return result.content
                        elif hasattr(result, 'text'):
                            return result.text
                        elif isinstance(result, str):
                            return result
                        else:
                            return str(result)
                    except Exception as e:
                        error_type = type(e).__name__
                        error_msg = str(e)

                        # 재시도 가능한 에러 감지 (503, 429)
                        if self._is_retryable_error(e, error_msg):
                            if retry_count < max_retries:
                                retry_count += 1
                                # Linear backoff: 1회 실패=10초, 2회 실패=20초, 3회 실패=30초
                                wait_time = retry_delay * retry_count
                                logger.warning(f"재시도 {retry_count}/{max_retries}: {wait_time}초 대기 중...")
                                time.sleep(wait_time)
                                continue
                            else:
                                logger.error(f"최대 재시도 횟수 초과 ({max_retries}회): {error_type} - {error_msg[:200]}")
                                raise e

                        # 재시도하면 안 되는 에러 감지 (즉시 중단)
                        # 1. 인증 실패 (401 UNAUTHENTICATED)
                        # 2. 권한 없음 (403 PERMISSION_DENIED)
                        # 3. 잘못된 요청 (400 INVALID_ARGUMENT)
                        if self._is_non_retryable_error(e, error_msg):
                            logger.warning(f"LLM API 호출 실패 (재시도 불가): {error_type} - {error_msg[:200]}")
                            raise e

                        # 일반 에러는 다음 메서드 시도
                        failed_attempts.append(f"{method_name}: {error_type} - {error_msg[:100]}")
                        logger.debug(f"메서드 {method_name} 호출 실패: {e}")
                        break  # while 루프 종료, 다음 메서드 시도
            else:
                failed_attempts.append(f"{method_name}: 메서드 없음")

        # generate_content_async 메서드 - async generator 처리
        if hasattr(self._llm, 'generate_content_async'):
            try:
                import asyncio
                import inspect

                # async generator를 동기적으로 처리하는 함수
                async def collect_async_generator():
                    """async generator의 모든 내용을 수집합니다."""
                    content_parts = []
                    async for chunk in self._llm.generate_content_async(input_text):
                        # chunk가 문자열이면 직접 추가
                        if isinstance(chunk, str):
                            content_parts.append(chunk)
                        # chunk가 객체면 text나 content 속성 확인
                        elif hasattr(chunk, 'text'):
                            content_parts.append(chunk.text)
                        elif hasattr(chunk, 'content'):
                            content_parts.append(chunk.content)
                        else:
                            content_parts.append(str(chunk))
                    return ''.join(content_parts)

                # asyncio 이벤트 루프로 실행
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(collect_async_generator())
                loop.close()

                logger.debug(f"generate_content_async 결과 길이: {len(result)} 문자")
                return result

            except Exception as e:
                logger.error(f"generate_content_async 호출 실패: {e}")
                import traceback
                error_trace = traceback.format_exc()
                logger.error(f"상세 에러:\n{error_trace}")

                # Google ADK의 정확한 사용법을 위해 객체 속성 확인
                logger.error(f"LLM 객체 타입: {type(self._llm)}")
                logger.error(f"LLM 객체 속성: {vars(self._llm) if hasattr(self._llm, '__dict__') else 'N/A'}")

        # 모든 메서드 실패 시 에러
        # WARNING 레벨로 시도 내역 기록
        logger.warning(f"LLM 호출 실패 - 모든 메서드 시도 실패:")
        for attempt in failed_attempts:
            logger.warning(f"  - {attempt}")

        error_msg = (f"LLM 객체 호출 실패.\n"
                    f"타입: {type(self._llm)}\n"
                    f"시도한 메서드: {len(failed_attempts)}개\n"
                    f"사용 가능한 public 메서드: {[m for m in available_methods if not m.startswith('_')][:30]}")
        raise AttributeError(error_msg)

    def _clean_response(self, response: str) -> str:
        """
        LLM 응답 텍스트를 정제합니다.
        - <think>...</think> 태그 제거
        - ```markdown ... ``` 코드 블록 추출 (있는 경우)
        - 전체 markdown 내용 반환 (코드 블록 추출 로직 제거)

        Args:
            response: LLM 원본 응답 텍스트

        Returns:
            정제된 markdown 텍스트
        """
        # 1. <think>...</think> 패턴 제거 (멀티라인, non-greedy)
        cleaned = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL)

        # 2. ```markdown ... ``` 코드 블록 추출 (명시적으로 markdown 블록으로 감싼 경우만)
        markdown_match = re.search(r'```markdown\s*(.*?)\s*```', cleaned, flags=re.DOTALL)
        if markdown_match:
            # markdown 코드 블록이 있으면 그 내용만 반환
            return markdown_match.group(1).strip()

        # 3. 코드 블록이 없으면 전체 응답 반환
        # (일반 코드 블록 추출 로직 제거 - 첫 번째 코드 블록만 추출하는 버그 수정)
        return cleaned.strip()

    def analyze_class(self, source_code: str, class_name: str = "") -> str:
        """
        Java Class 소스 코드를 분석하여 AI description을 생성합니다.

        Args:
            source_code: Java 클래스 소스 코드
            class_name: 클래스명 (로깅용)

        Returns:
            AI 분석 결과 (Markdown 형식) 또는 빈 문자열
        """
        if not self.is_available():
            return ""

        try:
            prompt = get_prompt("class_doc")
            input_text = f"{prompt}\n\n```java\n{source_code}\n```"

            # LLM 호출
            raw_response = self._call_llm(input_text)

            # 응답 정제 (think 태그, markdown 블록 제거)
            ai_description = self._clean_response(raw_response)

            logger.debug(f"Class AI 분석 완료: {class_name}")
            return ai_description if ai_description else ""

        except Exception as e:
            # 상세한 오류 로그 기록
            error_type = type(e).__name__
            error_msg = str(e)
            logger.warning(f"Class AI 분석 실패 ({class_name}): {error_type} - {error_msg}")

            # 디버그 레벨로 전체 traceback 기록
            import traceback
            logger.debug(f"Class AI 분석 상세 오류 ({class_name}):\n{traceback.format_exc()}")
            return ""

    def analyze_method(self, source_code: str, method_name: str = "", class_name: str = "") -> str:
        """
        Java Method 소스 코드를 분석하여 AI description을 생성합니다.

        Args:
            source_code: Java 메서드 소스 코드
            method_name: 메서드명 (로깅용)
            class_name: 클래스명 (로깅용, 선택사항)

        Returns:
            AI 분석 결과 (Markdown 형식) 또는 빈 문자열
        """
        if not self.is_available():
            return ""

        try:
            prompt = get_prompt("method_doc")
            input_text = f"{prompt}\n\n```java\n{source_code}\n```"

            # LLM 호출
            raw_response = self._call_llm(input_text)

            # 응답 정제 (think 태그, markdown 블록 제거)
            ai_description = self._clean_response(raw_response)

            # 로깅용 식별자 생성
            identifier = f"{class_name}.{method_name}" if class_name else method_name
            logger.debug(f"Method AI 분석 완료: {identifier}")
            return ai_description if ai_description else ""

        except Exception as e:
            # 상세한 오류 로그 기록
            error_type = type(e).__name__
            error_msg = str(e)
            identifier = f"{class_name}.{method_name}" if class_name else method_name
            logger.warning(f"Method AI 분석 실패 ({identifier}): {error_type} - {error_msg}")

            # 디버그 레벨로 전체 traceback 기록
            import traceback
            logger.debug(f"Method AI 분석 상세 오류 ({identifier}):\n{traceback.format_exc()}")
            return ""

    def analyze_sql(self, sql_statement: str, sql_id: str = "") -> str:
        """
        SQL 문을 분석하여 AI description을 생성합니다.

        Args:
            sql_statement: SQL 문
            sql_id: SQL ID (로깅용)

        Returns:
            AI 분석 결과 (Markdown 형식) 또는 빈 문자열
        """
        if not self.is_available():
            return ""

        try:
            prompt = get_prompt("sql_doc")
            input_text = f"{prompt}\n\n```sql\n{sql_statement}\n```"

            # LLM 호출
            raw_response = self._call_llm(input_text)

            # 응답 정제 (think 태그, markdown 블록 제거)
            ai_description = self._clean_response(raw_response)

            logger.debug(f"SQL AI 분석 완료: {sql_id}")
            return ai_description if ai_description else ""

        except Exception as e:
            # 상세한 오류 로그 기록
            error_type = type(e).__name__
            error_msg = str(e)
            logger.warning(f"SQL AI 분석 실패 ({sql_id}): {error_type} - {error_msg}")

            # 디버그 레벨로 전체 traceback 기록
            import traceback
            logger.debug(f"SQL AI 분석 상세 오류 ({sql_id}):\n{traceback.format_exc()}")
            return ""

    # ========== 비동기 메서드 (병렬 처리용) ==========

    async def _call_llm_async(self, input_text: str, max_retries: int = 3, retry_delay: int = 10) -> str:
        """
        LLM을 비동기로 호출하여 결과를 반환합니다.

        Args:
            input_text: LLM에 전달할 입력 텍스트
            max_retries: 최대 재시도 횟수 (기본값: 3)
            retry_delay: 재시도 간격 (초, 기본값: 10)

        Returns:
            LLM 응답 문자열
        """
        # 동기 _call_llm을 별도 스레드에서 실행
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self._call_llm(input_text, max_retries, retry_delay)
        )

    async def analyze_class_async(self, source_code: str, class_name: str = "") -> str:
        """
        Java Class 소스 코드를 비동기로 분석하여 AI description을 생성합니다.

        Args:
            source_code: Java 클래스 소스 코드
            class_name: 클래스명 (로깅용)

        Returns:
            AI 분석 결과 (Markdown 형식) 또는 빈 문자열
        """
        if not self.is_available():
            return ""

        try:
            prompt = get_prompt("class_doc")
            input_text = f"{prompt}\n\n```java\n{source_code}\n```"

            # LLM 비동기 호출
            raw_response = await self._call_llm_async(input_text)

            # 응답 정제 (think 태그, markdown 블록 제거)
            ai_description = self._clean_response(raw_response)

            logger.debug(f"Class AI 분석 완료 (async): {class_name}")
            return ai_description if ai_description else ""

        except Exception as e:
            # 상세한 오류 로그 기록
            error_type = type(e).__name__
            error_msg = str(e)
            logger.warning(f"Class AI 분석 실패 (async, {class_name}): {error_type} - {error_msg}")

            # 디버그 레벨로 전체 traceback 기록
            import traceback
            logger.debug(f"Class AI 분석 상세 오류 (async, {class_name}):\n{traceback.format_exc()}")
            return ""

    async def analyze_method_async(self, source_code: str, method_name: str = "", class_name: str = "") -> str:
        """
        Java Method 소스 코드를 비동기로 분석하여 AI description을 생성합니다.

        Args:
            source_code: Java 메서드 소스 코드
            method_name: 메서드명 (로깅용)
            class_name: 클래스명 (로깅용, 선택사항)

        Returns:
            AI 분석 결과 (Markdown 형식) 또는 빈 문자열
        """
        if not self.is_available():
            return ""

        try:
            prompt = get_prompt("method_doc")
            input_text = f"{prompt}\n\n```java\n{source_code}\n```"

            # LLM 비동기 호출
            raw_response = await self._call_llm_async(input_text)

            # 응답 정제 (think 태그, markdown 블록 제거)
            ai_description = self._clean_response(raw_response)

            # 로깅용 식별자 생성
            identifier = f"{class_name}.{method_name}" if class_name else method_name
            logger.debug(f"Method AI 분석 완료 (async): {identifier}")
            return ai_description if ai_description else ""

        except Exception as e:
            # 상세한 오류 로그 기록
            error_type = type(e).__name__
            error_msg = str(e)
            identifier = f"{class_name}.{method_name}" if class_name else method_name
            logger.warning(f"Method AI 분석 실패 (async, {identifier}): {error_type} - {error_msg}")

            # 디버그 레벨로 전체 traceback 기록
            import traceback
            logger.debug(f"Method AI 분석 상세 오류 (async, {identifier}):\n{traceback.format_exc()}")
            return ""

    async def analyze_sql_async(self, sql_statement: str, sql_id: str = "") -> str:
        """
        SQL 문을 비동기로 분석하여 AI description을 생성합니다.

        Args:
            sql_statement: SQL 문
            sql_id: SQL ID (로깅용)

        Returns:
            AI 분석 결과 (Markdown 형식) 또는 빈 문자열
        """
        if not self.is_available():
            return ""

        try:
            prompt = get_prompt("sql_doc")
            input_text = f"{prompt}\n\n```sql\n{sql_statement}\n```"

            # LLM 비동기 호출
            raw_response = await self._call_llm_async(input_text)

            # 응답 정제 (think 태그, markdown 블록 제거)
            ai_description = self._clean_response(raw_response)

            logger.debug(f"SQL AI 분석 완료 (async): {sql_id}")
            return ai_description if ai_description else ""

        except Exception as e:
            # 상세한 오류 로그 기록
            error_type = type(e).__name__
            error_msg = str(e)
            logger.warning(f"SQL AI 분석 실패 (async, {sql_id}): {error_type} - {error_msg}")

            # 디버그 레벨로 전체 traceback 기록
            import traceback
            logger.debug(f"SQL AI 분석 상세 오류 (async, {sql_id}):\n{traceback.format_exc()}")
            return ""

    async def analyze_method_batch_async(self, method_items: list[dict]) -> dict[str, str]:
        """
        여러 메서드를 배치로 비동기 분석하여 AI description을 생성합니다.

        Args:
            method_items: 메서드 정보 리스트 [{"method_id": "Class.Method", "class_name": "...", "method_name": "...", "source": "..."}, ...]

        Returns:
            {method_id: ai_description} 딕셔너리
        """
        if not self.is_available():
            return {}

        if not method_items:
            return {}

        try:
            prompt = get_prompt("method_batch_doc")

            # 배치 입력 텍스트 생성
            method_sections = []
            for idx, item in enumerate(method_items, 1):
                method_id = item.get("method_id", f"unknown_{idx}")
                class_name = item.get("class_name", "Unknown")
                method_name = item.get("method_name", "Unknown")
                source = item.get("source", "")
                method_sections.append(
                    f"**Method #{idx}** (Class: {class_name}, Method: {method_name})\n```java\n{source}\n```\n**END #{idx}**\n"
                )

            input_text = f"{prompt}\n\n" + "\n".join(method_sections)

            # LLM 비동기 호출
            raw_response = await self._call_llm_async(input_text)

            # 응답 정제 (think 태그, markdown 블록 제거)
            cleaned_response = self._clean_response(raw_response)

            # 응답 파싱: ---Method#N---...---END#N--- 형식
            results = self._parse_batch_method_response(cleaned_response, method_items)

            logger.debug(f"Method 배치 AI 분석 완료: {len(results)}개 처리됨")
            return results

        except Exception as e:
            # 상세한 오류 로그 기록
            error_type = type(e).__name__
            error_msg = str(e)
            logger.warning(f"Method 배치 AI 분석 실패: {error_type} - {error_msg}")

            # 디버그 레벨로 전체 traceback 기록
            import traceback
            logger.debug(f"Method 배치 AI 분석 상세 오류:\n{traceback.format_exc()}")
            return {}

    async def analyze_sql_batch_async(self, sql_items: list[dict]) -> dict[str, str]:
        """
        여러 SQL 문을 배치로 비동기 분석하여 AI description을 생성합니다.

        Args:
            sql_items: SQL 정보 리스트 [{"sql_id": "...", "sql_content": "..."}, ...]

        Returns:
            {sql_id: ai_description} 딕셔너리
        """
        if not self.is_available():
            return {}

        if not sql_items:
            return {}

        try:
            prompt = get_prompt("sql_batch_doc")

            # 배치 입력 텍스트 생성
            sql_sections = []
            for idx, item in enumerate(sql_items, 1):
                sql_id = item.get("sql_id", f"unknown_{idx}")
                sql_content = item.get("sql_content", "")
                sql_sections.append(
                    f"**SQL #{idx}** (ID: {sql_id})\n```sql\n{sql_content}\n```\n**END #{idx}**\n"
                )

            input_text = f"{prompt}\n\n" + "\n".join(sql_sections)

            # LLM 비동기 호출
            raw_response = await self._call_llm_async(input_text)

            # 응답 정제 (think 태그, markdown 블록 제거)
            cleaned_response = self._clean_response(raw_response)

            # 응답 파싱: ---SQL#N---...---END#N--- 형식
            results = self._parse_batch_sql_response(cleaned_response, sql_items)

            logger.debug(f"SQL 배치 AI 분석 완료: {len(results)}개 처리됨")
            return results

        except Exception as e:
            # 상세한 오류 로그 기록
            error_type = type(e).__name__
            error_msg = str(e)
            logger.warning(f"SQL 배치 AI 분석 실패: {error_type} - {error_msg}")

            # 디버그 레벨로 전체 traceback 기록
            import traceback
            logger.debug(f"SQL 배치 AI 분석 상세 오류:\n{traceback.format_exc()}")
            return {}

    def _parse_batch_sql_response(self, response: str, sql_items: list[dict]) -> dict[str, str]:
        """
        배치 SQL 분석 응답을 파싱합니다.

        Args:
            response: LLM 응답 텍스트
            sql_items: 원본 SQL 정보 리스트

        Returns:
            {sql_id: ai_description} 딕셔너리
        """
        results = {}

        # 패턴 1: ---SQL#N---...---END#N--- (개선된 형식, 번호 포함)
        pattern1 = r'---SQL#(\d+)---(.*?)---END#\1---'
        matches1 = re.findall(pattern1, response, flags=re.DOTALL)

        logger.debug(f"패턴 1 (---END#N---): {len(matches1)}개 매칭")

        # 패턴 1로 매칭된 SQL 번호 기록
        matched_nums = set()
        for sql_num_str, description in matches1:
            sql_num = int(sql_num_str)
            matched_nums.add(sql_num)
            if 1 <= sql_num <= len(sql_items):
                sql_id = sql_items[sql_num - 1].get("sql_id", "")
                if sql_id:
                    results[sql_id] = description.strip()
                    logger.debug(f"  SQL#{sql_num} ({sql_id}): {len(description)}자 추출")

        # 매칭되지 않은 SQL 처리 (END 태그 없는 경우)
        if len(matches1) < len(sql_items):
            logger.debug(f"패턴 2 (유연한 파싱) 시도: 미처리 {len(sql_items) - len(matches1)}개")
            # 패턴 2: ---SQL#N---부터 다음 ---SQL# 또는 문자열 끝까지
            pattern2 = r'---SQL#(\d+)---(.*?)(?=---SQL#\d+---|$)'
            matches2 = re.findall(pattern2, response, flags=re.DOTALL)

            for sql_num_str, description in matches2:
                sql_num = int(sql_num_str)
                # 패턴 1에서 이미 처리되지 않은 것만 처리
                if sql_num not in matched_nums and 1 <= sql_num <= len(sql_items):
                    sql_id = sql_items[sql_num - 1].get("sql_id", "")
                    if sql_id:
                        # ---END#N--- 태그 제거 (있을 경우)
                        desc_clean = re.sub(r'---END#?\d*---', '', description).strip()
                        results[sql_id] = desc_clean
                        logger.debug(f"  SQL#{sql_num} ({sql_id}): {len(desc_clean)}자 추출 (유연한 파싱)")

        # 이전 fallback 패턴들은 제거
        if False:
            # 패턴 2: ---SQL#N---...---END--- (이전 형식, 번호 없음)
            pattern2 = r'---SQL#(\d+)---(.*?)---END---'
            matches = re.findall(pattern2, response, flags=re.DOTALL)

            if matches:
                logger.debug(f"패턴 2 (---END---) 매칭: {len(matches)}개")
                for sql_num_str, description in matches:
                    sql_num = int(sql_num_str)
                    if 1 <= sql_num <= len(sql_items):
                        sql_id = sql_items[sql_num - 1].get("sql_id", "")
                        if sql_id:
                            results[sql_id] = description.strip()
            else:
                # 패턴 3: ---SQL#N--- 또는 ---SQLN--- (# 기호 선택적, END 태그 없음)
                # 다음 SQL 시작까지 또는 문자열 끝까지를 하나의 SQL로 간주
                pattern3 = r'---SQL#?(\d+)---(.*?)(?=---SQL#?\d+---|$)'
                matches = re.findall(pattern3, response, flags=re.DOTALL)

                if matches:
                    logger.debug(f"패턴 3 (유연한 파싱) 매칭: {len(matches)}개")
                    for sql_num_str, description in matches:
                        sql_num = int(sql_num_str)
                        if 1 <= sql_num <= len(sql_items):
                            sql_id = sql_items[sql_num - 1].get("sql_id", "")
                            if sql_id:
                                # ---END#N--- 또는 ---END--- 태그 제거 (있을 경우)
                                desc_clean = re.sub(r'---END#?\d*---', '', description).strip()
                                results[sql_id] = desc_clean

        # 결과 검증
        if len(results) < len(sql_items):
            logger.warning(
                f"SQL 배치 분석 응답 파싱 불완전: "
                f"{len(results)}/{len(sql_items)}개만 파싱됨"
            )
            logger.debug(f"응답 내용 (첫 1000자):\n{response[:1000]}")

        return results

    def _parse_batch_method_response(self, response: str, method_items: list[dict]) -> dict[str, str]:
        """
        배치 Method 분석 응답을 파싱합니다.

        Args:
            response: LLM 응답 텍스트
            method_items: 원본 Method 정보 리스트

        Returns:
            {method_id: ai_description} 딕셔너리
        """
        results = {}

        # 패턴 1: ---Method#N---...---END#N--- (개선된 형식, 번호 포함)
        pattern1 = r'---Method#(\d+)---(.*?)---END#\1---'
        matches1 = re.findall(pattern1, response, flags=re.DOTALL)

        logger.debug(f"패턴 1 (---END#N---): {len(matches1)}개 매칭")

        # 패턴 1로 매칭된 Method 번호 기록
        matched_nums = set()
        for method_num_str, description in matches1:
            method_num = int(method_num_str)
            matched_nums.add(method_num)
            if 1 <= method_num <= len(method_items):
                method_id = method_items[method_num - 1].get("method_id", "")
                if method_id:
                    results[method_id] = description.strip()
                    logger.debug(f"  Method#{method_num} ({method_id}): {len(description)}자 추출")

        # 매칭되지 않은 Method 처리 (END 태그 없는 경우)
        if len(matches1) < len(method_items):
            logger.debug(f"패턴 2 (유연한 파싱) 시도: 미처리 {len(method_items) - len(matches1)}개")
            # 패턴 2: ---Method#N---부터 다음 ---Method# 또는 문자열 끝까지
            pattern2 = r'---Method#(\d+)---(.*?)(?=---Method#\d+---|$)'
            matches2 = re.findall(pattern2, response, flags=re.DOTALL)

            for method_num_str, description in matches2:
                method_num = int(method_num_str)
                # 패턴 1에서 이미 처리되지 않은 것만 처리
                if method_num not in matched_nums and 1 <= method_num <= len(method_items):
                    method_id = method_items[method_num - 1].get("method_id", "")
                    if method_id:
                        # ---END#N--- 태그 제거 (있을 경우)
                        desc_clean = re.sub(r'---END#?\d*---', '', description).strip()
                        results[method_id] = desc_clean
                        logger.debug(f"  Method#{method_num} ({method_id}): {len(desc_clean)}자 추출 (유연한 파싱)")

        # 결과 검증
        if len(results) < len(method_items):
            logger.warning(
                f"Method 배치 분석 응답 파싱 불완전: "
                f"{len(results)}/{len(method_items)}개만 파싱됨"
            )
            logger.debug(f"응답 내용 (첫 1000자):\n{response[:1000]}")

        return results


# 전역 AI Analyzer 인스턴스
_ai_analyzer = None


def get_ai_analyzer() -> AIAnalyzer:
    """
    전역 AI Analyzer 인스턴스를 반환합니다.

    Returns:
        AIAnalyzer 인스턴스
    """
    global _ai_analyzer
    if _ai_analyzer is None:
        _ai_analyzer = AIAnalyzer()
    return _ai_analyzer
