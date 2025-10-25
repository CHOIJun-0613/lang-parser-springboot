"""
GoogleAIProvider 수정 사항 테스트
API 호출 없이 객체 초기화와 메서드 존재 여부만 확인합니다.
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

def test_google_ai_provider_initialization():
    """GoogleAIProvider 초기화 테스트"""
    print("=" * 80)
    print("GoogleAIProvider 초기화 테스트 시작")
    print("=" * 80)

    try:
        from csa.aiwork.ai_providers import GoogleAIProvider

        # Provider 생성
        provider = GoogleAIProvider()
        print(f"✓ GoogleAIProvider 생성 성공")
        print(f"  - API 키 설정 여부: {'설정됨' if provider.api_key else '미설정'}")
        print(f"  - 모델명: {provider.model_name}")
        print(f"  - 사용 가능 여부: {provider.is_available()}")

        if not provider.is_available():
            print("\n⚠ Google API 키가 설정되지 않았거나 라이브러리가 설치되지 않았습니다.")
            return False

        # LLM 객체 생성
        llm = provider.create_llm()
        print(f"\n✓ LLM 객체 생성 성공")
        print(f"  - 타입: {type(llm)}")

        # 메서드 존재 여부 확인
        all_methods = dir(llm)
        available_methods = [m for m in all_methods if callable(getattr(llm, m, None))]
        public_methods = [m for m in available_methods if not m.startswith('_')]

        print(f"\n✓ 사용 가능한 메서드 확인:")
        print(f"  - 전체 메서드 수: {len(available_methods)}")
        print(f"  - Public 메서드: {public_methods}")
        print(f"  - __call__ 메서드 존재: {hasattr(llm, '__call__')}")

        # __call__ 메서드 호출 가능 여부 확인 (실제 호출하지 않음)
        if hasattr(llm, '__call__'):
            print(f"\n✓ __call__ 메서드가 존재하여 직접 호출 가능합니다.")
            print(f"  - 예시: llm('프롬프트 텍스트')")
        else:
            print(f"\n✗ __call__ 메서드가 없습니다!")
            return False

        print("\n" + "=" * 80)
        print("✓ 모든 테스트 통과!")
        print("=" * 80)
        return True

    except Exception as e:
        print(f"\n✗ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_google_ai_simple_call():
    """GoogleAIProvider 실제 API 호출 테스트 (선택적)"""
    print("\n" + "=" * 80)
    print("GoogleAIProvider 실제 API 호출 테스트")
    print("=" * 80)

    try:
        from csa.aiwork.ai_providers import GoogleAIProvider

        provider = GoogleAIProvider()

        if not provider.is_available():
            print("⚠ Google API를 사용할 수 없어 테스트를 건너뜁니다.")
            return True

        llm = provider.create_llm()

        # 간단한 프롬프트로 테스트
        test_prompt = "Hello, please respond with 'OK' in one word."
        print(f"\n테스트 프롬프트: {test_prompt}")

        try:
            result = llm(test_prompt)
            print(f"\n✓ API 호출 성공!")
            print(f"  - 응답 타입: {type(result)}")
            print(f"  - 응답 길이: {len(result)} 문자")
            print(f"  - 응답 내용 (처음 100자): {result[:100]}")
            return True
        except Exception as e:
            print(f"\n✗ API 호출 실패: {e}")
            import traceback
            traceback.print_exc()
            return False

    except Exception as e:
        print(f"\n✗ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # 1. 초기화 테스트
    success1 = test_google_ai_provider_initialization()

    # 2. 실제 API 호출 테스트
    # 환경변수로 제어 (기본값: 실행하지 않음)
    run_api_test = os.getenv("RUN_API_TEST", "no").lower() in ["yes", "y", "true", "1"]

    if run_api_test:
        success2 = test_google_ai_simple_call()
    else:
        print("\n[INFO] 실제 API 호출 테스트를 건너뜁니다.")
        print("[INFO] API 호출 테스트를 실행하려면 환경변수 RUN_API_TEST=yes 설정 후 재실행하세요.")
        success2 = True

    # 결과 출력
    print("\n" + "=" * 80)
    print("테스트 결과 요약")
    print("=" * 80)
    print(f"  - 초기화 테스트: {'[PASS]' if success1 else '[FAIL]'}")
    print(f"  - API 호출 테스트: {'[PASS]' if success2 else '[SKIP]' if not run_api_test else '[FAIL]'}")
    print("=" * 80)

    sys.exit(0 if (success1 and success2) else 1)
