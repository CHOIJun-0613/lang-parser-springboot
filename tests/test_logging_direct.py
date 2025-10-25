"""
로그 출력 직접 테스트
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

# LOG_LEVEL을 INFO로 설정
os.environ["LOG_LEVEL"] = "INFO"

def main():
    """로그 출력 직접 테스트"""
    print("=" * 80)
    print("로그 레벨 테스트 (LOG_LEVEL=INFO)")
    print("=" * 80)

    from csa.utils.logger import get_logger

    logger = get_logger(__name__)

    print(f"\n[TEST] 로거 레벨: {logging.getLevelName(logger.level)}")
    print(f"[TEST] 핸들러 수: {len(logger.handlers)}")
    for i, handler in enumerate(logger.handlers):
        print(f"[TEST] 핸들러 {i+1}: {type(handler).__name__}, 레벨={logging.getLevelName(handler.level)}")

    print(f"\n[실행] 다양한 레벨의 로그 출력...\n")

    logger.debug("DEBUG 레벨 로그 (보이지 않아야 함)")
    logger.info("INFO 레벨 로그")
    logger.warning("WARNING 레벨 로그")
    logger.error("ERROR 레벨 로그")
    logger.critical("CRITICAL 레벨 로그")

    print("\n" + "=" * 80)
    print("[결과 확인]")
    print("위에서 다음 로그들이 출력되었는지 확인하세요:")
    print("  - [I] : INFO 레벨 로그")
    print("  - [W] : WARNING 레벨 로그")
    print("  - [E] : ERROR 레벨 로그")
    print("  - [C] : CRITICAL 레벨 로그")
    print("DEBUG는 보이지 않아야 합니다.")
    print("=" * 80)


if __name__ == "__main__":
    main()
