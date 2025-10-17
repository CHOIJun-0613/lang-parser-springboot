"""
Step 2: Field Injection Cypher 쿼리 테스트

이 스크립트는 Neo4j에서 Field injection 기반 Bean 의존성을 해결하는
Cypher 쿼리를 실행하고 결과를 검증합니다.
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


def load_cypher_query(file_path: str) -> str:
    """Cypher 쿼리 파일 로드"""
    with open(file_path, 'r', encoding='utf-8') as f:
        # 주석 제거 및 쿼리 추출
        lines = []
        for line in f:
            line = line.strip()
            # 주석 라인 제거 (// 시작)
            if line.startswith('//'):
                continue
            lines.append(line)
        return '\n'.join(lines)


def count_existing_dependencies(db: GraphDB, project_name: str) -> int:
    """기존 DEPENDS_ON 관계 개수 확인"""
    query = """
    MATCH (source:Bean {project_name: $project_name})-[r:DEPENDS_ON]->(target:Bean)
    RETURN count(r) as dependency_count
    """

    with db._driver.session() as session:
        result = session.run(query, project_name=project_name)
        record = result.single()
        return record["dependency_count"] if record else 0


def execute_field_injection_query(db: GraphDB, project_name: str, cypher_query: str):
    """Field injection Cypher 쿼리 실행"""
    logger.info("=" * 80)
    logger.info("Field Injection Cypher 쿼리 실행")
    logger.info("=" * 80)

    with db._driver.session() as session:
        result = session.run(cypher_query, project_name=project_name)
        records = list(result)

        logger.info(f"✓ 생성된 DEPENDS_ON 관계: {len(records)}개")

        if len(records) > 0:
            logger.info("\n생성된 Bean 의존성 상세 정보:")
            for idx, record in enumerate(records, 1):
                source_bean = record["source_bean"]
                source_class = record["source_class"]
                field_name = record["field_name"]
                field_type = record["field_type"]
                target_bean = record["target_bean"]
                target_class = record["target_class"]

                logger.info(f"\n  [{idx}] {source_bean} ({source_class})")
                logger.info(f"      ↓ @Autowired {field_name} : {field_type}")
                logger.info(f"      {target_bean} ({target_class})")
                logger.info(f"      → DEPENDS_ON 관계 생성됨")

            logger.info("\n✅ Field injection 기반 Bean 의존성 해결 성공!")
            return len(records)
        else:
            logger.warning("⚠️  생성된 DEPENDS_ON 관계가 없습니다.")
            logger.info("   → Field type과 Bean class_name이 매칭되는 경우가 없거나")
            logger.info("   → 이미 DEPENDS_ON 관계가 존재할 수 있습니다.")
            return 0


def verify_dependencies(db: GraphDB, project_name: str):
    """생성된 DEPENDS_ON 관계 검증"""
    logger.info("\n" + "=" * 80)
    logger.info("생성된 DEPENDS_ON 관계 검증")
    logger.info("=" * 80)

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
    """

    with db._driver.session() as session:
        result = session.run(query, project_name=project_name)
        records = list(result)

        logger.info(f"✓ Neo4j resolver로 생성된 의존성: {len(records)}개")

        if len(records) > 0:
            logger.info("\n검증 결과:")
            for idx, record in enumerate(records, 1):
                source_bean = record["source_bean"]
                injection_type = record["injection_type"]
                field_name = record["field_name"]
                target_bean = record["target_bean"]

                logger.info(f"  [{idx}] {source_bean} -[DEPENDS_ON]-> {target_bean}")
                logger.info(f"      injection_type: {injection_type}")
                logger.info(f"      field_name: {field_name}")

            logger.info("\n✅ 검증 완료: 모든 관계가 정상적으로 저장되었습니다.")
            return True
        else:
            logger.warning("⚠️  Neo4j resolver로 생성된 의존성을 찾지 못했습니다.")
            return False


def show_neo4j_browser_guide():
    """Neo4j Browser에서 확인하는 방법 안내"""
    logger.info("\n" + "=" * 80)
    logger.info("Neo4j Browser에서 직접 확인하기")
    logger.info("=" * 80)

    logger.info("\n1. Neo4j Browser 접속:")
    logger.info("   http://localhost:7474")

    logger.info("\n2. 생성된 DEPENDS_ON 관계 확인 쿼리:")
    logger.info("   " + "-" * 76)
    logger.info("""
   MATCH (source:Bean)-[r:DEPENDS_ON]->(target:Bean)
   WHERE r.created_by = 'neo4j_resolver'
   RETURN source, r, target
   """)
    logger.info("   " + "-" * 76)

    logger.info("\n3. 시각화:")
    logger.info("   위 쿼리를 실행하면 Bean 의존성 그래프를 시각적으로 확인할 수 있습니다.")


def main():
    """메인 테스트 실행 함수"""
    logger.info("\n")
    logger.info("╔" + "=" * 78 + "╗")
    logger.info("║" + " " * 18 + "Step 2: Field Injection Cypher 쿼리 테스트" + " " * 18 + "║")
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

        # Cypher 쿼리 로드
        cypher_file = os.path.join(
            os.path.dirname(__file__),
            "cypher_queries",
            "step2_field_injection.cypher"
        )

        if not os.path.exists(cypher_file):
            logger.error(f"❌ Cypher 쿼리 파일을 찾을 수 없습니다: {cypher_file}")
            sys.exit(1)

        logger.info(f"Cypher 쿼리 로드: {cypher_file}")
        cypher_query = load_cypher_query(cypher_file)
        logger.info("✓ Cypher 쿼리 로드 성공\n")

        # 기존 의존성 개수 확인
        logger.info("기존 DEPENDS_ON 관계 개수 확인...")
        before_count = count_existing_dependencies(db, project_name)
        logger.info(f"✓ 기존 DEPENDS_ON 관계: {before_count}개\n")

        # Field injection 쿼리 실행
        created_count = execute_field_injection_query(db, project_name, cypher_query)

        # 실행 후 의존성 개수 확인
        logger.info("\n실행 후 DEPENDS_ON 관계 개수 확인...")
        after_count = count_existing_dependencies(db, project_name)
        logger.info(f"✓ 현재 DEPENDS_ON 관계: {after_count}개")
        logger.info(f"✓ 증가분: {after_count - before_count}개\n")

        # 생성된 관계 검증
        verify_dependencies(db, project_name)

        # Neo4j Browser 안내
        show_neo4j_browser_guide()

        # 결과 요약
        logger.info("\n" + "=" * 80)
        logger.info("테스트 결과 요약")
        logger.info("=" * 80)
        logger.info(f"✓ 기존 DEPENDS_ON 관계: {before_count}개")
        logger.info(f"✓ 새로 생성된 관계: {created_count}개")
        logger.info(f"✓ 최종 DEPENDS_ON 관계: {after_count}개")

        if created_count > 0:
            logger.info("\n🎉 Step 2 완료!")
            logger.info("   Field injection 기반 Bean 의존성 해결 Cypher 쿼리가 정상 작동합니다.")
            logger.info("   Step 3(Python 함수 작성)으로 진행할 준비가 되었습니다.")
        else:
            logger.info("\n✅ Cypher 쿼리는 정상 작동하지만 새로 생성된 관계가 없습니다.")
            logger.info("   → 이미 DEPENDS_ON 관계가 존재하거나")
            logger.info("   → Field type과 Bean class_name이 매칭되지 않을 수 있습니다.")

        # Neo4j 연결 종료
        db.close()

    except Exception as e:
        logger.error(f"\n❌ 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
