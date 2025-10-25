"""
Python 캐시 파일 삭제 스크립트
"""
import os
import shutil
from pathlib import Path

def clean_cache(root_dir):
    """Python 캐시 파일 및 디렉터리 삭제"""
    count = 0
    root_path = Path(root_dir)

    # __pycache__ 디렉터리 찾기
    for pycache_dir in root_path.rglob("__pycache__"):
        try:
            shutil.rmtree(pycache_dir)
            print(f"삭제: {pycache_dir}")
            count += 1
        except Exception as e:
            print(f"삭제 실패: {pycache_dir} - {e}")

    # .pyc 파일 찾기
    for pyc_file in root_path.rglob("*.pyc"):
        try:
            pyc_file.unlink()
            print(f"삭제: {pyc_file}")
            count += 1
        except Exception as e:
            print(f"삭제 실패: {pyc_file} - {e}")

    return count

if __name__ == "__main__":
    # csa 모듈의 캐시 삭제
    csa_dir = Path(__file__).parent / "csa"

    print("=" * 80)
    print("Python 캐시 삭제 중...")
    print("=" * 80)

    count = clean_cache(csa_dir)

    print("\n" + "=" * 80)
    print(f"완료: {count}개 항목 삭제됨")
    print("=" * 80)
