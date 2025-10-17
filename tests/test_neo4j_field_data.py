"""
Step 1: Neo4j Field 데이터 검증 및 샘플 쿼리 테스트

이 스크립트는 Neo4j에 저장된 Field 노드 데이터를 검증합니다.
- Field 노드 존재 여부 확인
- injection 어노테이션(@Autowired, @Inject, @Resource) 확인
- Bean과 Field의 연결 관계 확인
"""
import os
import sys
import json
from dotenv import load_dotenv

# 프로젝트 루트를 Python path에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from csa.services.graph_db import GraphDB
from csa.utils.logger import get_logger

# 환경 변수 로드
load_dotenv()

logger = get_logger(__name__)


def test_field_nodes_exist(db: GraphDB, project_name: str):
    """Field 노드가 존재하는지 확인"""
    logger.info("=" * 80)
    logger.info("Test 1: Field 노드 존재 여부 확인")
    logger.info("=" * 80)

    query = """
    MATCH (f:Field {project_name: $project_name})
    RETURN count(f) as field_count
    """

    with db._driver.session() as session:
        result = session.run(query, project_name=project_name)
        record = result.single()
        field_count = record["field_count"] if record else 0

        logger.info(f"✓ 발견된 Field 노드 개수: {field_count}")

        if field_count > 0:
            logger.info("✅ Field 노드가 존재합니다.")
            return True
        else:
            logger.error("❌ Field 노드가 존재하지 않습니다.")
            return False


def test_field_with_injection_annotations(db: GraphDB, project_name: str):
    """injection 어노테이션이 있는 Field 조회"""
    logger.info("\n" + "=" * 80)
    logger.info("Test 2: injection 어노테이션이 있는 Field 목록 조회")
    logger.info("=" * 80)

    query = """
    MATCH (f:Field {project_name: $project_name})
    WHERE f.annotations_json IS NOT NULL
      AND (f.annotations_json CONTAINS '"Autowired"'
           OR f.annotations_json CONTAINS '"Inject"'
           OR f.annotations_json CONTAINS '"Resource"')
    RETURN f.name as field_name,
           f.type as field_type,
           f.class_name as class_name,
           f.annotations_json as annotations
    LIMIT 10
    """

    with db._driver.session() as session:
        result = session.run(query, project_name=project_name)
        records = list(result)

        logger.info(f"✓ injection 어노테이션이 있는 Field: {len(records)}개")

        if len(records) > 0:
            logger.info("\n상위 10개 Field 상세 정보:")
            for idx, record in enumerate(records, 1):
                field_name = record["field_name"]
                field_type = record["field_type"]
                class_name = record["class_name"]
                annotations_json = record["annotations"]

                logger.info(f"\n  [{idx}] Class: {class_name}")
                logger.info(f"      Field: {field_name} (Type: {field_type})")

                # annotations JSON 파싱
                try:
                    annotations = json.loads(annotations_json)
                    for ann in annotations:
                        if ann.get('name') in ['Autowired', 'Inject', 'Resource']:
                            logger.info(f"      Annotation: @{ann.get('name')}")
                except Exception as e:
                    logger.warning(f"      Annotation JSON 파싱 실패: {e}")

            logger.info("\n✅ injection 어노테이션이 있는 Field를 발견했습니다.")
            return True
        else:
            logger.warning("⚠️  injection 어노테이션이 있는 Field를 찾지 못했습니다.")
            return False


def test_bean_field_relationship(db: GraphDB, project_name: str):
    """Bean과 Field의 연결 관계 확인"""
    logger.info("\n" + "=" * 80)
    logger.info("Test 3: Bean → Class → Field 연결 관계 확인")
    logger.info("=" * 80)

    query = """
    MATCH (bean:Bean {project_name: $project_name})
    MATCH (class:Class {name: bean.class_name})-[:HAS_FIELD]->(field:Field)
    WHERE field.annotations_json CONTAINS '"Autowired"'
       OR field.annotations_json CONTAINS '"Inject"'
       OR field.annotations_json CONTAINS '"Resource"'
    RETURN bean.name as bean_name,
           bean.class_name as class_name,
           field.name as field_name,
           field.type as field_type
    LIMIT 10
    """

    with db._driver.session() as session:
        result = session.run(query, project_name=project_name)
        records = list(result)

        logger.info(f"✓ Bean → Field 연결 관계: {len(records)}개")

        if len(records) > 0:
            logger.info("\n상위 10개 Bean-Field 관계:")
            for idx, record in enumerate(records, 1):
                bean_name = record["bean_name"]
                class_name = record["class_name"]
                field_name = record["field_name"]
                field_type = record["field_type"]

                logger.info(f"  [{idx}] Bean: {bean_name} ({class_name})")
                logger.info(f"      ↓ has field")
                logger.info(f"      Field: {field_name} (Type: {field_type})")

            logger.info("\n✅ Bean → Class → Field 연결 관계가 정상적으로 구축되어 있습니다.")
            return True
        else:
            logger.warning("⚠️  Bean → Class → Field 연결 관계를 찾지 못했습니다.")
            return False


def test_potential_bean_dependencies(db: GraphDB, project_name: str):
    """잠재적 Bean 의존성 매칭 테스트"""
    logger.info("\n" + "=" * 80)
    logger.info("Test 4: 잠재적 Bean 의존성 매칭 (Field type = Bean class)")
    logger.info("=" * 80)

    query = """
    MATCH (sourceClass:Class)-[:HAS_FIELD]->(field:Field {project_name: $project_name})
    MATCH (sourceBean:Bean {class_name: sourceClass.name, project_name: $project_name})
    WHERE field.annotations_json CONTAINS '"Autowired"'
       OR field.annotations_json CONTAINS '"Inject"'
       OR field.annotations_json CONTAINS '"Resource"'

    MATCH (targetBean:Bean {project_name: $project_name})
    WHERE targetBean.class_name = field.type

    RETURN sourceBean.name as source_bean,
           field.name as field_name,
           field.type as field_type,
           targetBean.name as target_bean,
           targetBean.class_name as target_class
    LIMIT 10
    """

    with db._driver.session() as session:
        result = session.run(query, project_name=project_name)
        records = list(result)

        logger.info(f"✓ 매칭 가능한 Bean 의존성: {len(records)}개")

        if len(records) > 0:
            logger.info("\n상위 10개 Bean 의존성:")
            for idx, record in enumerate(records, 1):
                source_bean = record["source_bean"]
                field_name = record["field_name"]
                field_type = record["field_type"]
                target_bean = record["target_bean"]
                target_class = record["target_class"]

                logger.info(f"  [{idx}] {source_bean}")
                logger.info(f"      ↓ @Autowired {field_name} ({field_type})")
                logger.info(f"      {target_bean} ({target_class})")

            logger.info("\n✅ Field type과 Bean class_name이 매칭되는 의존성을 발견했습니다!")
            logger.info("   → 이 데이터로 DEPENDS_ON 관계를 생성할 수 있습니다.")
            return True
        else:
            logger.warning("⚠️  매칭 가능한 Bean 의존성을 찾지 못했습니다.")
            return False


def main():
    """메인 테스트 실행 함수"""
    logger.info("\n")
    logger.info("╔" + "=" * 78 + "╗")
    logger.info("║" + " " * 20 + "Step 1: Neo4j Field 데이터 검증" + " " * 24 + "║")
    logger.info("╚" + "=" * 78 + "╝")
    logger.info("\n")

    # Neo4j 연결 정보
    neo4j_uri = os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687")
    neo4j_user = os.getenv("NEO4J_USER", "csauser")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "csauser123")
    neo4j_database = os.getenv("NEO4J_DATABASE", "csadb01")

    # 프로젝트명 (환경 변수 또는 기본값)
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

        # 테스트 실행
        test_results = []

        test_results.append(("Field 노드 존재 여부",
                            test_field_nodes_exist(db, project_name)))

        test_results.append(("injection 어노테이션 Field",
                            test_field_with_injection_annotations(db, project_name)))

        test_results.append(("Bean-Field 연결 관계",
                            test_bean_field_relationship(db, project_name)))

        test_results.append(("잠재적 Bean 의존성 매칭",
                            test_potential_bean_dependencies(db, project_name)))

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
            logger.info("\n🎉 모든 테스트 통과! Neo4j Field 데이터가 정상적으로 저장되어 있습니다.")
            logger.info("   Step 2로 진행할 준비가 되었습니다.")
        elif passed_tests >= total_tests - 1:
            logger.info("\n⚠️  대부분의 테스트 통과. 일부 데이터 확인 필요.")
        else:
            logger.error("\n❌ 테스트 실패. Neo4j 데이터를 확인하세요.")

        # Neo4j 연결 종료
        db.close()

    except Exception as e:
        logger.error(f"\n❌ 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
