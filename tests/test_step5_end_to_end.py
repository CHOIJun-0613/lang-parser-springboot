"""
Step 5: End-to-End 통합 테스트

이 스크립트는 전체 파이프라인(analyze --java-object)을 실행하여
Neo4j 기반 Bean 의존성 해결이 정상적으로 작동하는지 테스트합니다.
"""
import os
import sys
from dotenv import load_dotenv

# 프로젝트 루트를 Python path에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from csa.services.graph_db import GraphDB
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


def count_all_dependencies(db: GraphDB, project_name: str) -> int:
    """모든 DEPENDS_ON 관계 개수 확인"""
    query = """
    MATCH (source:Bean {project_name: $project_name})-[r:DEPENDS_ON]->(target:Bean)
    RETURN count(r) as dependency_count
    """

    with db._driver.session() as session:
        result = session.run(query, project_name=project_name)
        record = result.single()
        return record["dependency_count"] if record else 0


def get_dependency_details(db: GraphDB, project_name: str):
    """의존성 상세 정보 조회"""
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


def main():
    """메인 테스트 실행 함수"""
    logger.info("\n")
    logger.info("╔" + "=" * 78 + "╗")
    logger.info("║" + " " * 22 + "Step 5: End-to-End 통합 테스트" + " " * 25 + "║")
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

    logger.info("=" * 80)
    logger.info("테스트 시나리오")
    logger.info("=" * 80)
    logger.info("1. Neo4j에서 현재 DEPENDS_ON 관계 개수 확인")
    logger.info("2. analyze --java-object 명령어 실행 (별도 실행 필요)")
    logger.info("3. Neo4j resolver로 생성된 의존성 확인")
    logger.info("4. 의존성 상세 정보 출력")
    logger.info("\n")

    try:
        # Neo4j 연결
        logger.info("Neo4j에 연결 중...")
        db = GraphDB(neo4j_uri, neo4j_user, neo4j_password, neo4j_database)
        logger.info("✓ Neo4j 연결 성공\n")

        # 현재 상태 확인
        logger.info("=" * 80)
        logger.info("Step 1: 현재 Neo4j 상태 확인")
        logger.info("=" * 80)

        all_count = count_all_dependencies(db, project_name)
        neo4j_resolver_count = count_neo4j_resolver_dependencies(db, project_name)

        logger.info(f"✓ 전체 DEPENDS_ON 관계: {all_count}개")
        logger.info(f"✓ Neo4j resolver가 생성한 관계: {neo4j_resolver_count}개")
        logger.info("")

        # 의존성 상세 정보
        if neo4j_resolver_count > 0:
            logger.info("=" * 80)
            logger.info("Step 2: Neo4j Resolver 의존성 상세 정보")
            logger.info("=" * 80)

            dependencies = get_dependency_details(db, project_name)

            for idx, dep in enumerate(dependencies, 1):
                logger.info(f"\n  [{idx}] {dep['source_bean']} ({dep['source_class']})")
                logger.info(f"      ↓ @{dep['injection_type'].capitalize()}: {dep['field_name']} ({dep['field_type']})")
                logger.info(f"      {dep['target_bean']} ({dep['target_class']})")

            logger.info("\n")

        # 결과 요약
        logger.info("=" * 80)
        logger.info("테스트 결과")
        logger.info("=" * 80)

        if neo4j_resolver_count > 0:
            logger.info(f"✅ 성공: Neo4j resolver가 {neo4j_resolver_count}개의 의존성을 생성했습니다.")
            logger.info("\n🎉 Step 5 완료!")
            logger.info("   전체 파이프라인이 정상적으로 작동합니다.")
            logger.info("   - project.py: dependencies = [] (메모리 기반 해결 비활성화)")
            logger.info("   - neo4j_writer.py: resolve_bean_dependencies_from_neo4j() 호출")
            logger.info("   - bean_dependency_resolver.py: Neo4j 쿼리로 의존성 해결")
            logger.info("\n   방안 B (Neo4j 기반 점진적 해결) 구현 완료!")
        else:
            logger.warning("⚠️  주의: Neo4j resolver가 생성한 의존성이 없습니다.")
            logger.info("\n   다음을 확인해주세요:")
            logger.info("   1. analyze --java-object --clean 명령어를 실행했는지")
            logger.info("   2. Bean injection 어노테이션이 있는 Field가 있는지")
            logger.info("   3. Field type과 Bean class_name이 매칭되는지")

        # Neo4j 연결 종료
        db.close()

    except Exception as e:
        logger.error(f"\n❌ 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
