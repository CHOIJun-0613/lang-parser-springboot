"""
AI 분석 오류 로그 테스트
"""

import sys
import os
from pathlib import Path
import logging

# Windows 콘솔 인코딩 설정
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def setup_logger():
    """테스트용 로거 설정"""
    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # 콘솔 핸들러
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    return root_logger


def test_method_error_with_class_name():
    """Method AI 분석 실패 로그 테스트 (Class.Method 형식)"""
    print("=" * 80)
    print("Method AI 분석 오류 로그 테스트 (Class.Method 형식)")
    print("=" * 80)

    setup_logger()

    try:
        from csa.aiwork.ai_analyzer import AIAnalyzer
        from unittest.mock import Mock

        # AI Analyzer 생성
        analyzer = AIAnalyzer()
        analyzer._is_available = True

        # LLM을 의도적으로 오류 발생시키도록 설정
        def raise_error(prompt):
            raise RuntimeError("테스트용 의도적 오류: API 호출 실패")

        analyzer._llm = Mock()
        analyzer._llm.__call__ = raise_error

        # 테스트용 Java 메서드
        sample_method = """
    public Brand getBrandById(Long id) {
        return brandMapper.selectBrandById(id);
    }
"""

        print(f"\n[TEST] 테스트 메서드: getBrandById")
        print(f"[TEST] 클래스명: BrandService")

        # AI 분석 실행 (오류 발생 예상)
        result = analyzer.analyze_method(
            sample_method,
            method_name="getBrandById",
            class_name="BrandService"
        )

        print(f"\n[INFO] 반환 결과: '{result}' (빈 문자열 예상)")

        print("\n" + "=" * 80)
        print("[SUCCESS] 오류 로그 테스트 완료")
        print("위 로그에 'Method AI 분석 실패 (BrandService.getBrandById): RuntimeError - ...' 형식이 나타나야 합니다.")
        print("=" * 80)
        return True

    except Exception as e:
        print(f"\n[FAIL] 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_class_error():
    """Class AI 분석 실패 로그 테스트"""
    print("\n\n" + "=" * 80)
    print("Class AI 분석 오류 로그 테스트")
    print("=" * 80)

    try:
        from csa.aiwork.ai_analyzer import AIAnalyzer
        from unittest.mock import Mock

        # AI Analyzer 생성
        analyzer = AIAnalyzer()
        analyzer._is_available = True

        # LLM을 의도적으로 오류 발생시키도록 설정
        def raise_error(prompt):
            raise ValueError("테스트용 의도적 오류: 잘못된 입력 값")

        analyzer._llm = Mock()
        analyzer._llm.__call__ = raise_error

        # 테스트용 Java 클래스
        sample_class = """
public class BrandService {
    private final BrandMapper brandMapper;
}
"""

        print(f"\n[TEST] 테스트 클래스: BrandService")

        # AI 분석 실행 (오류 발생 예상)
        result = analyzer.analyze_class(
            sample_class,
            class_name="BrandService"
        )

        print(f"\n[INFO] 반환 결과: '{result}' (빈 문자열 예상)")

        print("\n" + "=" * 80)
        print("[SUCCESS] 오류 로그 테스트 완료")
        print("위 로그에 'Class AI 분석 실패 (BrandService): ValueError - ...' 형식이 나타나야 합니다.")
        print("=" * 80)
        return True

    except Exception as e:
        print(f"\n[FAIL] 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success1 = test_method_error_with_class_name()
    success2 = test_class_error()

    print("\n\n" + "=" * 80)
    print("테스트 결과 요약")
    print("=" * 80)
    print(f"  - Method 오류 로그 테스트: {'[PASS]' if success1 else '[FAIL]'}")
    print(f"  - Class 오류 로그 테스트: {'[PASS]' if success2 else '[FAIL]'}")
    print("=" * 80)

    sys.exit(0 if (success1 and success2) else 1)
