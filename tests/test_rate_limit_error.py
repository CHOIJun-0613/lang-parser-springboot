"""
Rate Limit 에러 처리 테스트
429 RESOURCE_EXHAUSTED 발생 시 즉시 중단하는지 확인
"""

import sys
import os
from pathlib import Path

# Windows 콘솔 인코딩 설정
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# LOG_LEVEL을 INFO로 설정
os.environ["LOG_LEVEL"] = "INFO"


def test_rate_limit_error():
    """Rate Limit 에러 발생 시 즉시 중단 테스트"""
    print("=" * 80)
    print("Rate Limit 에러 처리 테스트 (429 RESOURCE_EXHAUSTED)")
    print("=" * 80)

    try:
        from csa.aiwork.ai_analyzer import AIAnalyzer
        from unittest.mock import Mock

        # AI Analyzer 생성
        analyzer = AIAnalyzer()
        analyzer._is_available = True

        # 429 Rate Limit 에러를 발생시키는 Mock LLM
        mock_llm = Mock()
        mock_llm.side_effect = RuntimeError(
            "429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': "
            "'You exceeded your current quota, please check your plan and billing details.'}}"
        )

        analyzer._llm = mock_llm

        # 테스트용 Java 메서드
        sample_method = """
    public void processData() {
        // 데이터 처리
    }
"""

        print(f"\n[INFO] 테스트 시나리오: Rate Limit 초과 에러 발생")
        print(f"[INFO] 예상 동작: 첫 번째 메서드(__call__)에서 429 에러 발생 → 즉시 중단")
        print(f"\n[실행] AI 분석 시작...\n")

        # AI 분석 실행 (429 에러 발생 예상)
        # analyze_method는 예외를 잡아서 빈 문자열을 반환함
        result = analyzer.analyze_method(
            sample_method,
            method_name="processData",
            class_name="DataService"
        )

        print(f"\n[RESULT] 반환값: '{result}'")

        if result == "":
            print(f"[PASS] 빈 문자열 반환됨 (에러 발생 후 정상 처리)")
        else:
            print(f"[FAIL] 예상하지 못한 결과 반환")
            return False

        print("\n" + "=" * 80)
        print("[결과 확인]")
        print("위 로그에서 다음 항목들이 출력되었는지 확인하세요:")
        print("  1. [W] : Rate Limit 초과 감지 (429 RESOURCE_EXHAUSTED)")
        print("  2. [W] :   - 분당 요청 수(RPM) 또는 분당 토큰 수(TPM) 초과")
        print("  3. [W] :   - 잠시 후 다시 시도하거나 API 할당량을 확인하세요")
        print("  4. [W] : LLM API 호출 실패 (재시도 불가): RuntimeError - ...")
        print("  5. 다른 메서드를 시도하지 않고 즉시 중단되어야 함")
        print("=" * 80)
        return True

    except Exception as e:
        print(f"\n[FAIL] 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_auth_error():
    """인증 실패 에러 처리 테스트"""
    print("\n\n" + "=" * 80)
    print("인증 실패 에러 처리 테스트 (401 UNAUTHENTICATED)")
    print("=" * 80)

    try:
        from csa.aiwork.ai_analyzer import AIAnalyzer
        from unittest.mock import Mock

        # AI Analyzer 생성
        analyzer = AIAnalyzer()
        analyzer._is_available = True

        # 401 인증 실패 에러를 발생시키는 Mock LLM
        mock_llm = Mock()
        mock_llm.side_effect = RuntimeError(
            "401 UNAUTHENTICATED. API key not valid. Please pass a valid API key."
        )

        analyzer._llm = mock_llm

        # 테스트용 Java 메서드
        sample_method = "public void test() {}"

        print(f"\n[INFO] 테스트 시나리오: 인증 실패 에러 발생")
        print(f"[INFO] 예상 동작: 첫 번째 메서드에서 401 에러 발생 → 즉시 중단")
        print(f"\n[실행] AI 분석 시작...\n")

        # AI 분석 실행
        result = analyzer.analyze_method(
            sample_method,
            method_name="test",
            class_name="TestService"
        )

        print(f"\n[RESULT] 반환값: '{result}'")

        if result == "":
            print(f"[PASS] 빈 문자열 반환됨 (에러 발생 후 정상 처리)")
        else:
            print(f"[FAIL] 예상하지 못한 결과 반환")
            return False

        print("\n" + "=" * 80)
        print("[결과 확인]")
        print("위 로그에서 다음 항목들이 출력되었는지 확인하세요:")
        print("  1. [W] : 인증 실패 감지 (401 UNAUTHENTICATED)")
        print("  2. [W] :   - API 키가 유효하지 않거나 만료되었습니다")
        print("  3. [W] :   - .env 파일의 GOOGLE_API_KEY를 확인하세요")
        print("=" * 80)
        return True

    except Exception as e:
        print(f"\n[FAIL] 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success1 = test_rate_limit_error()
    success2 = test_auth_error()

    print("\n\n" + "=" * 80)
    print("테스트 결과 요약")
    print("=" * 80)
    print(f"  - Rate Limit 에러 테스트: {'[PASS]' if success1 else '[FAIL]'}")
    print(f"  - 인증 실패 에러 테스트: {'[PASS]' if success2 else '[FAIL]'}")
    print("=" * 80)

    sys.exit(0 if (success1 and success2) else 1)
