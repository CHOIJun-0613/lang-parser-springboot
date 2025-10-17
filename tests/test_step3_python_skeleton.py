"""
Step 3: Python 함수 스켈레톤 테스트

이 스크립트는 bean_dependency_resolver.py 모듈의 스켈레톤 함수들이
에러 없이 import되고 호출되는지 테스트합니다.
"""
import os
import sys
from dotenv import load_dotenv

# 프로젝트 루트를 Python path에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from csa.services.graph_db import GraphDB
from csa.services.java_analysis.bean_dependency_resolver import (
    resolve_bean_dependencies_from_neo4j
)
from csa.utils.logger import get_logger

# 환경 변수 로드
load_dotenv()

logger = get_logger(__name__)


def test_module_import():
    """모듈 import 테스트"""
    logger.info("=" * 80)
    logger.info("Test 1: 모듈 import 테스트")
    logger.info("=" * 80)

    try:
        # 이미 import 완료
        logger.info("✓ bean_dependency_resolver 모듈 import 성공")
        logger.info("✓ resolve_bean_dependencies_from_neo4j 함수 import 성공")
        return True
    except Exception as e:
        logger.error(f"✗ 모듈 import 실패: {e}")
        return False


def test_function_signature():
    """함수 시그니처 테스트"""
    logger.info("\n" + "=" * 80)
    logger.info("Test 2: 함수 시그니처 테스트")
    logger.info("=" * 80)

    try:
        # 함수 시그니처 확인
        import inspect
        sig = inspect.signature(resolve_bean_dependencies_from_neo4j)

        logger.info(f"✓ 함수 시그니처: {sig}")

        # 파라미터 확인
        params = list(sig.parameters.keys())
        expected_params = ['db', 'project_name', 'logger']

        logger.info(f"✓ 파라미터: {params}")

        if params == expected_params:
            logger.info("✓ 파라미터 이름이 예상과 일치합니다.")
            return True
        else:
            logger.warning(f"⚠️  파라미터 이름이 예상({expected_params})과 다릅니다.")
            return False

    except Exception as e:
        logger.error(f"✗ 함수 시그니처 확인 실패: {e}")
        return False


def test_function_docstring():
    """함수 docstring 테스트"""
    logger.info("\n" + "=" * 80)
    logger.info("Test 3: 함수 docstring 테스트")
    logger.info("=" * 80)

    try:
        docstring = resolve_bean_dependencies_from_neo4j.__doc__

        if docstring:
            logger.info("✓ Docstring이 존재합니다.")
            logger.info("\n" + "-" * 80)
            # 첫 5줄만 출력
            lines = docstring.strip().split('\n')[:5]
            for line in lines:
                logger.info(f"  {line}")
            logger.info("  ...")
            logger.info("-" * 80)
            return True
        else:
            logger.warning("⚠️  Docstring이 없습니다.")
            return False

    except Exception as e:
        logger.error(f"✗ Docstring 확인 실패: {e}")
        return False


def test_function_execution(db: GraphDB, project_name: str):
    """함수 실행 테스트 (스켈레톤)"""
    logger.info("\n" + "=" * 80)
    logger.info("Test 4: 함수 실행 테스트")
    logger.info("=" * 80)

    try:
        logger.info("resolve_bean_dependencies_from_neo4j() 함수 호출 중...")
        logger.info("")

        # 함수 호출
        resolve_bean_dependencies_from_neo4j(db, project_name, logger)

        logger.info("")
        logger.info("✓ 함수가 에러 없이 실행되었습니다.")
        logger.info("  (현재는 스켈레톤만 구현되어 있어 실제 작업은 수행하지 않음)")
        return True

    except Exception as e:
        logger.error(f"✗ 함수 실행 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """메인 테스트 실행 함수"""
    logger.info("\n")
    logger.info("╔" + "=" * 78 + "╗")
    logger.info("║" + " " * 20 + "Step 3: Python 함수 스켈레톤 테스트" + " " * 23 + "║")
    logger.info("╚" + "=" * 78 + "╝")
    logger.info("\n")

    # Neo4j 연결 정보
    neo4j_uri = os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687")
    neo4j_user = os.getenv("NEO4J_USER", "csauser")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "csauser123")
    neo4j_database = os.getenv("NEO4J_DATABASE", "csadb01")
    project_name = os.getenv("TEST_PROJECT_NAME", "car-center-devlab")

    logger.info(f"연결 정보:")
    logger.info(f"  - URI: {neo4j_uri}")
    logger.info(f"  - Database: {neo4j_database}")
    logger.info(f"  - Project: {project_name}")
    logger.info("\n")

    try:
        # 테스트 실행
        test_results = []

        # Test 1: 모듈 import
        test_results.append(("모듈 import", test_module_import()))

        # Test 2: 함수 시그니처
        test_results.append(("함수 시그니처", test_function_signature()))

        # Test 3: 함수 docstring
        test_results.append(("함수 docstring", test_function_docstring()))

        # Test 4: 함수 실행 (Neo4j 연결 필요)
        logger.info("Neo4j에 연결 중...")
        db = GraphDB(neo4j_uri, neo4j_user, neo4j_password, neo4j_database)
        logger.info("✓ Neo4j 연결 성공\n")

        test_results.append(("함수 실행 (스켈레톤)", test_function_execution(db, project_name)))

        # Neo4j 연결 종료
        db.close()

        # 결과 요약
        logger.info("\n" + "=" * 80)
        logger.info("테스트 결과 요약")
        logger.info("=" * 80)

        for test_name, result in test_results:
            status = "✅ PASS" if result else "❌ FAIL"
            logger.info(f"{status} - {test_name}")

        total_tests = len(test_results)
        passed_tests = sum(1 for _, result in test_results if result)

        logger.info("\n" + "-" * 80)
        logger.info(f"총 {total_tests}개 테스트 중 {passed_tests}개 통과")
        logger.info("-" * 80)

        if passed_tests == total_tests:
            logger.info("\n🎉 Step 3 완료!")
            logger.info("   Python 함수 스켈레톤이 정상적으로 작성되었습니다.")
            logger.info("   - 모듈 import 성공")
            logger.info("   - 함수 시그니처 정상")
            logger.info("   - Docstring 존재")
            logger.info("   - 함수 실행 에러 없음")
            logger.info("\n   Step 4(Cypher 쿼리 통합)로 진행할 준비가 되었습니다.")
        else:
            logger.error("\n❌ 일부 테스트 실패. 코드를 확인하세요.")

    except Exception as e:
        logger.error(f"\n❌ 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
