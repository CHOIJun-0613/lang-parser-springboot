"""
AI Method 분석 통합 테스트
실제 Java 메서드를 AI로 분석하는 전체 흐름을 테스트합니다.
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
    """AI Method 분석 통합 테스트"""
    print("=" * 80)
    print("AI Method 분석 통합 테스트")
    print("=" * 80)

    try:
        from csa.aiwork.ai_analyzer import get_ai_analyzer

        # AI Analyzer 초기화
        analyzer = get_ai_analyzer()

        if not analyzer.is_available():
            print("[ERROR] AI Analyzer를 사용할 수 없습니다.")
            print("  - .env 파일의 AI_USE_ANALYSIS=true 설정을 확인하세요.")
            print("  - API 키가 올바르게 설정되었는지 확인하세요.")
            return False

        print(f"[INFO] AI Analyzer 초기화 완료")

        # 테스트용 Java 메서드 코드
        sample_method = """
    public Brand createBrand(Brand brand) {
        // 브랜드명 중복 체크
        if (brandMapper.existsByName(brand.getName())) {
            throw new BusinessException("이미 존재하는 브랜드명입니다.");
        }

        // 브랜드 저장
        brandMapper.insertBrand(brand);
        return brand;
    }
"""

        print(f"\n[TEST] 테스트 메서드:")
        print("  " + "-" * 76)
        for line in sample_method.strip().split('\n'):
            print(f"  {line}")
        print("  " + "-" * 76)

        # AI 분석 실행
        print(f"\n[INFO] AI 분석 시작...")
        result = analyzer.analyze_method(sample_method, method_name="createBrand")

        if result:
            print(f"\n[SUCCESS] AI 분석 완료!")
            print(f"  - 결과 길이: {len(result)} 문자")
            print(f"\n  [AI 분석 결과]")
            print("  " + "=" * 76)
            for line in result.split('\n'):
                print(f"  {line}")
            print("  " + "=" * 76)
        else:
            print(f"\n[FAIL] AI 분석 결과가 비어있습니다.")
            return False

        print("\n" + "=" * 80)
        print("[PASS] 통합 테스트 성공!")
        print("=" * 80)
        return True

    except Exception as e:
        print(f"\n[FAIL] 통합 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
