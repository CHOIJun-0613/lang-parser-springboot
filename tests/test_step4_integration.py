"""
Step 4: Cypher 쿼리 통합 테스트

이 스크립트는 bean_dependency_resolver.py의 _resolve_field_injections() 함수가
실제로 Neo4j에 DEPENDS_ON 관계를 생성하는지 테스트합니다.
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


def count_neo4j_resolver_dependencies(db: GraphDB, project_name: str) -> int:
    """Neo4j resolver로 생성된 DEPENDS_ON 관계 개수 확인"""
    query = """
    MATCH (source:Bean {project_name: $project_name})-[r:DEPENDS_ON]->(target:Bean)
    WHERE r.created_by = 'neo4j_resolver'
    RETURN count(r) as dependency_count
    """

    with db._driver.session() as session:
        result = session.run(query, project_name=project_name)
        record = result.single()
        return record["dependency_count"] if record else 0


def get_all_dependencies(db: GraphDB, project_name: str):
    """모든 Neo4j resolver 의존성 조회"""
    query = """
    MATCH (source:Bean {project_name: $project_name})-[r:DEPENDS_ON]->(target:Bean)
    WHERE r.created_by = 'neo4j_resolver'
    RETURN source.name as source_bean,
           source.class_name as source_class,
           r.injection_type as injection_type,
           r.field_name as field_name,
           r.field_type as field_type,
           target.name as target_bean,
           target.class_name as target_class
    ORDER BY source_bean, field_name
    """

    with db._driver.session() as session:
        result = session.run(query, project_name=project_name)
        return list(result)


def delete_neo4j_resolver_dependencies(db: GraphDB, project_name: str) -> int:
    """Neo4j resolver로 생성된 DEPENDS_ON 관계 삭제 (테스트 초기화)"""
    query = """
    MATCH (source:Bean {project_name: $project_name})-[r:DEPENDS_ON]->(target:Bean)
    WHERE r.created_by = 'neo4j_resolver'
    DELETE r
    RETURN count(r) as deleted_count
    """

    with db._driver.session() as session:
        result = session.run(query, project_name=project_name)
        record = result.single()
        return record["deleted_count"] if record else 0


def test_integration():
    """통합 테스트 실행"""
    logger.info("\n")
    logger.info("╔" + "=" * 78 + "╗")
    logger.info("║" + " " * 22 + "Step 4: Cypher 쿼리 통합 테스트" + " " * 25 + "║")
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
        # Neo4j 연결
        logger.info("Neo4j에 연결 중...")
        db = GraphDB(neo4j_uri, neo4j_user, neo4j_password, neo4j_database)
        logger.info("✓ Neo4j 연결 성공\n")

        # Step 1: 테스트 초기화 (기존 Neo4j resolver 의존성 삭제)
        logger.info("=" * 80)
        logger.info("Step 1: 테스트 초기화")
        logger.info("=" * 80)
        deleted_count = delete_neo4j_resolver_dependencies(db, project_name)
        logger.info(f"✓ 기존 Neo4j resolver 의존성 {deleted_count}개 삭제됨")
        logger.info("")

        # Step 2: 초기화 후 의존성 개수 확인
        before_count = count_neo4j_resolver_dependencies(db, project_name)
        logger.info(f"✓ 현재 Neo4j resolver 의존성: {before_count}개 (0개여야 정상)")
        logger.info("")

        # Step 3: resolve_bean_dependencies_from_neo4j() 실행
        logger.info("=" * 80)
        logger.info("Step 2: resolve_bean_dependencies_from_neo4j() 실행")
        logger.info("=" * 80)
        logger.info("")

        resolve_bean_dependencies_from_neo4j(db, project_name, logger)

        logger.info("")

        # Step 4: 실행 후 의존성 개수 확인
        logger.info("=" * 80)
        logger.info("Step 3: 실행 결과 검증")
        logger.info("=" * 80)

        after_count = count_neo4j_resolver_dependencies(db, project_name)
        created_count = after_count - before_count

        logger.info(f"✓ 실행 전 의존성: {before_count}개")
        logger.info(f"✓ 실행 후 의존성: {after_count}개")
        logger.info(f"✓ 새로 생성된 의존성: {created_count}개")
        logger.info("")

        # Step 5: 생성된 의존성 상세 조회
        if created_count > 0:
            logger.info("생성된 의존성 상세 정보:")
            logger.info("-" * 80)

            dependencies = get_all_dependencies(db, project_name)
            for idx, dep in enumerate(dependencies, 1):
                logger.info(f"\n  [{idx}] {dep['source_bean']} ({dep['source_class']})")
                logger.info(f"      ↓ @{dep['injection_type'].capitalize()}: {dep['field_name']} ({dep['field_type']})")
                logger.info(f"      {dep['target_bean']} ({dep['target_class']})")

            logger.info("\n" + "-" * 80)

        # 결과 요약
        logger.info("\n" + "=" * 80)
        logger.info("테스트 결과 요약")
        logger.info("=" * 80)

        if created_count > 0:
            logger.info(f"✅ 성공: {created_count}개의 DEPENDS_ON 관계가 생성되었습니다.")
            logger.info("\n🎉 Step 4 완료!")
            logger.info("   Cypher 쿼리가 Python 함수에 성공적으로 통합되었습니다.")
            logger.info("   - Field injection 의존성 해결 정상 작동")
            logger.info("   - Neo4j DEPENDS_ON 관계 생성 확인")
            logger.info("\n   Step 5(기존 코드 연결)로 진행할 준비가 되었습니다.")
        else:
            logger.warning("⚠️  경고: DEPENDS_ON 관계가 생성되지 않았습니다.")
            logger.info("   → Field type과 Bean class_name이 매칭되지 않거나")
            logger.info("   → injection 어노테이션이 있는 Field가 없을 수 있습니다.")
            logger.info("\n   Step 1의 테스트 결과를 다시 확인해주세요.")

        # Neo4j 연결 종료
        db.close()

    except Exception as e:
        logger.error(f"\n❌ 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    test_integration()
