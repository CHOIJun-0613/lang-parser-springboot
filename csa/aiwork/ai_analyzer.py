"""
AI 분석 서비스 모듈
LLM을 사용하여 Class, Method, SQL의 특징을 분석합니다.
"""

import logging
import re

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

    def _call_llm(self, input_text: str) -> str:
        """
        LLM을 호출하여 결과를 반환합니다.
        Provider별로 다른 메서드를 시도합니다.
        """
        # 사용 가능한 모든 메서드 확인 (디버그용)
        all_methods = dir(self._llm)
        available_methods = [m for m in all_methods if callable(getattr(self._llm, m, None))]

        # Google ADK Gemini용 메서드 추가
        methods_to_try = [
            'generate_content',      # Google ADK Gemini 동기 메서드
            'invoke',                # LangChain 스타일
            'generate',              # 일반적인 메서드명
            'predict',               # 일반적인 메서드명
            'run',                   # 일반적인 메서드명
            '__call__'               # Callable 객체
        ]

        for method_name in methods_to_try:
            if hasattr(self._llm, method_name):
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
                    logger.debug(f"메서드 {method_name} 호출 실패: {e}")
                    continue

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
        error_msg = (f"LLM 객체 호출 실패.\n"
                    f"타입: {type(self._llm)}\n"
                    f"사용 가능한 메서드 (처음 30개): {[m for m in available_methods if not m.startswith('_')][:30]}")
        raise AttributeError(error_msg)

    def _clean_response(self, response: str) -> str:
        """
        LLM 응답 텍스트를 정제합니다.
        - <think>...</think> 태그 제거
        - ```markdown ... ``` 코드 블록 추출
        - 실제 markdown 내용만 반환

        Args:
            response: LLM 원본 응답 텍스트

        Returns:
            정제된 markdown 텍스트
        """
        # 1. <think>...</think> 패턴 제거 (멀티라인, non-greedy)
        cleaned = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL)

        # 2. ```markdown ... ``` 코드 블록 추출
        markdown_match = re.search(r'```markdown\s*(.*?)\s*```', cleaned, flags=re.DOTALL)
        if markdown_match:
            # markdown 코드 블록이 있으면 그 내용만 반환
            return markdown_match.group(1).strip()

        # 3. ``` ... ``` 일반 코드 블록 추출 (markdown 키워드 없는 경우)
        code_block_match = re.search(r'```\s*(.*?)\s*```', cleaned, flags=re.DOTALL)
        if code_block_match:
            return code_block_match.group(1).strip()

        # 4. 코드 블록이 없으면 정제된 텍스트 반환
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
            logger.warning(f"Class AI 분석 실패 ({class_name}): {e}")
            return ""

    def analyze_method(self, source_code: str, method_name: str = "") -> str:
        """
        Java Method 소스 코드를 분석하여 AI description을 생성합니다.

        Args:
            source_code: Java 메서드 소스 코드
            method_name: 메서드명 (로깅용)

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

            logger.debug(f"Method AI 분석 완료: {method_name}")
            return ai_description if ai_description else ""

        except Exception as e:
            logger.warning(f"Method AI 분석 실패 ({method_name}): {e}")
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
            logger.warning(f"SQL AI 분석 실패 ({sql_id}): {e}")
            return ""


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
