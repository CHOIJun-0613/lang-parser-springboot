"""
실제 Google AI API 호출 테스트
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

def main():
    """실제 API 호출 테스트"""
    print("=" * 80)
    print("Google AI API 호출 테스트")
    print("=" * 80)

    try:
        from csa.aiwork.ai_providers import GoogleAIProvider

        # Provider 생성
        provider = GoogleAIProvider()

        if not provider.is_available():
            print("[ERROR] Google API를 사용할 수 없습니다.")
            print("  - API 키를 .env 파일에 설정했는지 확인하세요.")
            return False

        print(f"[INFO] Provider 초기화 완료")
        print(f"  - 모델명: {provider.model_name}")

        # LLM 객체 생성
        llm = provider.create_llm()
        print(f"[INFO] LLM 객체 생성 완료")

        # 간단한 프롬프트로 테스트
        test_prompt = "Say 'Hello' in one word."
        print(f"\n[TEST] 프롬프트: {test_prompt}")

        result = llm(test_prompt)

        print(f"\n[SUCCESS] API 호출 성공!")
        print(f"  - 응답 타입: {type(result)}")
        print(f"  - 응답 길이: {len(result)} 문자")
        print(f"  - 응답 내용:")
        print("  " + "-" * 76)
        print(f"  {result}")
        print("  " + "-" * 76)

        print("\n" + "=" * 80)
        print("[PASS] 테스트 성공!")
        print("=" * 80)
        return True

    except Exception as e:
        print(f"\n[FAIL] API 호출 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
