"""
개선된 로그 형식 테스트
LOG_LEVEL=INFO에서 WARNING이 제대로 출력되는지 확인
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

def main():
    """개선된 로그 형식 테스트"""
    print("=" * 80)
    print("개선된 AI 분석 오류 로그 테스트 (LOG_LEVEL=INFO)")
    print("=" * 80)

    try:
        from csa.aiwork.ai_analyzer import AIAnalyzer
        from unittest.mock import Mock

        # AI Analyzer 생성
        analyzer = AIAnalyzer()
        analyzer._is_available = True

        # LLM을 의도적으로 오류 발생시키도록 설정
        def raise_error(prompt):
            raise RuntimeError("의도적 오류: Google API 응답 실패")

        analyzer._llm = Mock()
        analyzer._llm.__call__ = raise_error

        # 테스트용 Java 메서드
        sample_method = """
    public int getUserVehicleCount(Long userId) {
        return vehicleMapper.countByUserId(userId);
    }
"""

        print(f"\n[INFO] LOG_LEVEL=INFO 설정됨")
        print(f"[INFO] 테스트 메서드: VehicleService.getUserVehicleCount")
        print(f"\n[실행] AI 분석 시작...\n")

        # AI 분석 실행 (오류 발생 예상)
        result = analyzer.analyze_method(
            sample_method,
            method_name="getUserVehicleCount",
            class_name="VehicleService"
        )

        print(f"\n\n[INFO] 반환 결과: '{result}' (빈 문자열 예상)")

        print("\n" + "=" * 80)
        print("[결과 확인]")
        print("위 로그에서 다음 항목들이 출력되었는지 확인하세요:")
        print("  1. [WARNING] LLM 호출 실패 - 모든 메서드 시도 실패:")
        print("  2. [WARNING]   - __call__: RuntimeError - 의도적 오류: Google API 응답 실패")
        print("  3. [WARNING] Method AI 분석 실패 (VehicleService.getUserVehicleCount): AttributeError - ...")
        print("=" * 80)
        return True

    except Exception as e:
        print(f"\n[FAIL] 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
