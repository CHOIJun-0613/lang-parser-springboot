"""
Neo4j 기반 Bean 의존성 해결 모듈

이 모듈은 Neo4j에 저장된 Bean과 Field 정보를 사용하여
Bean 간의 의존성 관계(DEPENDS_ON)를 생성합니다.

주요 기능:
- Field injection: @Autowired, @Inject, @Resource 어노테이션이 있는 필드
- Constructor injection: 생성자 파라미터를 통한 의존성 주입 (향후 구현)
- Setter injection: setter 메서드를 통한 의존성 주입 (향후 구현)

사용 방법:
    from csa.services.graph_db import GraphDB
    from csa.services.java_analysis.bean_dependency_resolver import (
        resolve_bean_dependencies_from_neo4j
    )

    db = GraphDB(uri, user, password, database)
    resolve_bean_dependencies_from_neo4j(db, "my-project", logger)
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from csa.services.graph_db import GraphDB
    from logging import Logger


def resolve_bean_dependencies_from_neo4j(
    db: "GraphDB",
    project_name: str,
    logger: "Logger"
) -> None:
    """
    Neo4j에 저장된 Bean과 Field 정보를 사용하여 의존성 관계를 생성합니다.

    이 함수는 다음 단계로 Bean 의존성을 해결합니다:
    1. Field injection (필드 주입) - @Autowired, @Inject, @Resource
    2. Constructor injection (생성자 주입) - 향후 구현
    3. Setter injection (setter 메서드 주입) - 향후 구현

    Args:
        db: Neo4j GraphDB 인스턴스
        project_name: 프로젝트명 (예: "car-center-devlab")
        logger: 로거 인스턴스

    Returns:
        None (DEPENDS_ON 관계를 Neo4j에 생성)

    Raises:
        Exception: Neo4j 쿼리 실행 중 오류 발생 시

    Example:
        >>> from csa.services.graph_db import GraphDB
        >>> from csa.utils.logger import get_logger
        >>>
        >>> db = GraphDB("bolt://localhost:7687", "neo4j", "password", "neo4j")
        >>> logger = get_logger(__name__)
        >>> resolve_bean_dependencies_from_neo4j(db, "my-project", logger)
    """
    logger.info("=" * 80)
    logger.info("Bean 의존성 해결 시작 (Neo4j 기반)")
    logger.info("=" * 80)
    logger.info(f"프로젝트: {project_name}")
    logger.info("")

    # Phase 1: Field injection 해결
    logger.info("Phase 1: Field injection 의존성 해결 중...")
    field_count = _resolve_field_injections(db, project_name, logger)
    logger.info(f"✓ Field injection 완료: {field_count}개 의존성 생성")
    logger.info("")

    # Phase 2: Constructor injection 해결
    logger.info("Phase 2: Constructor injection 의존성 해결 중...")
    constructor_count = _resolve_constructor_injections(db, project_name, logger)
    logger.info(f"✓ Constructor injection 완료: {constructor_count}개 의존성 생성")
    logger.info("")

    # Phase 3: Setter injection 해결
    logger.info("Phase 3: Setter injection 의존성 해결 중...")
    setter_count = _resolve_setter_injections(db, project_name, logger)
    logger.info(f"✓ Setter injection 완료: {setter_count}개 의존성 생성")
    logger.info("")

    total_count = field_count + constructor_count + setter_count
    logger.info("=" * 80)
    logger.info(f"Bean 의존성 해결 완료: 총 {total_count}개 의존성 생성")
    logger.info("=" * 80)


def _resolve_field_injections(
    db: "GraphDB",
    project_name: str,
    logger: "Logger"
) -> int:
    """
    Field 주입 방식의 Bean 의존성을 해결합니다.

    @Autowired, @Inject, @Resource 어노테이션이 있는 Field를 찾아서
    Field type과 Bean class_name을 매칭하여 DEPENDS_ON 관계를 생성합니다.

    Args:
        db: Neo4j GraphDB 인스턴스
        project_name: 프로젝트명
        logger: 로거 인스턴스

    Returns:
        int: 생성된 DEPENDS_ON 관계의 개수

    Raises:
        Exception: Neo4j 쿼리 실행 중 오류 발생 시
    """
    logger.debug("  → Field injection 의존성 쿼리 실행 중...")

    # Field injection 의존성 해결 Cypher 쿼리
    # Step 2에서 검증된 쿼리 통합
    query = """
    // 1. Bean이 포함된 클래스의 Field 찾기
    MATCH (sourceClass:Class)-[:HAS_FIELD]->(field:Field {project_name: $project_name})
    MATCH (sourceBean:Bean {class_name: sourceClass.name, project_name: $project_name})

    // 2. Field에 injection 어노테이션이 있는지 확인
    WHERE field.annotations_json IS NOT NULL
      AND (field.annotations_json CONTAINS '"Autowired"'
           OR field.annotations_json CONTAINS '"Inject"'
           OR field.annotations_json CONTAINS '"Resource"')

    // 3. Field type과 일치하는 Bean 찾기 (class_name으로 매칭)
    MATCH (targetBean:Bean {project_name: $project_name})
    WHERE targetBean.class_name = field.type

    // 4. DEPENDS_ON 관계 생성 (중복 방지를 위해 MERGE 사용)
    MERGE (sourceBean)-[r:DEPENDS_ON]->(targetBean)
    SET r.injection_type = 'field',
        r.field_name = field.name,
        r.field_type = field.type,
        r.created_by = 'neo4j_resolver'

    // 5. 생성된 의존성 정보 반환
    RETURN sourceBean.name as source_bean,
           sourceBean.class_name as source_class,
           field.name as field_name,
           field.type as field_type,
           targetBean.name as target_bean,
           targetBean.class_name as target_class
    """

    created_count = 0

    try:
        with db._driver.session() as session:
            result = session.run(query, project_name=project_name)
            records = list(result)
            created_count = len(records)

            # 생성된 의존성 상세 로깅 (DEBUG 레벨)
            if created_count > 0:
                logger.debug(f"  → {created_count}개의 Field injection 의존성 생성됨:")
                for idx, record in enumerate(records, 1):
                    source_bean = record["source_bean"]
                    field_name = record["field_name"]
                    target_bean = record["target_bean"]
                    logger.debug(
                        f"     [{idx}] {source_bean} --(@Autowired {field_name})--> {target_bean}"
                    )
            else:
                logger.debug("  → Field injection 의존성이 생성되지 않음 (매칭되는 Bean 없음)")

    except Exception as e:
        logger.error(f"  ✗ Field injection 의존성 해결 중 오류: {e}")
        raise

    return created_count


def _resolve_constructor_injections(
    db: "GraphDB",
    project_name: str,
    logger: "Logger"
) -> int:
    """
    Constructor 주입 방식의 Bean 의존성을 해결합니다.

    생성자 파라미터에 @Autowired 어노테이션이 있거나
    Spring Boot의 암묵적 생성자 주입을 사용하는 경우
    파라미터 타입과 Bean class_name을 매칭하여 DEPENDS_ON 관계를 생성합니다.

    Args:
        db: Neo4j GraphDB 인스턴스
        project_name: 프로젝트명
        logger: 로거 인스턴스

    Returns:
        int: 생성된 DEPENDS_ON 관계의 개수
    """
    import json

    logger.debug("  → Constructor injection 의존성 쿼리 실행 중...")

    # Step 1: 생성자 정보 조회 쿼리
    query_constructors = """
    MATCH (sourceClass:Class)-[:HAS_METHOD]->(constructor:Method {project_name: $project_name})
    MATCH (sourceBean:Bean {class_name: sourceClass.name, project_name: $project_name})
    WHERE constructor.name = sourceClass.name
      AND constructor.parameters IS NOT NULL
    RETURN sourceBean.name as source_bean,
           sourceBean.class_name as source_class,
           constructor.name as constructor_name,
           constructor.parameters as parameters_json
    ORDER BY source_bean
    """

    # Step 2: DEPENDS_ON 관계 생성 쿼리
    query_create_dependency = """
    MATCH (sourceBean:Bean {name: $source_bean, project_name: $project_name})
    MATCH (targetBean:Bean {class_name: $param_type, project_name: $project_name})
    MERGE (sourceBean)-[r:DEPENDS_ON]->(targetBean)
    SET r.injection_type = 'constructor',
        r.parameter_name = $param_name,
        r.parameter_type = $param_type,
        r.parameter_order = $param_order,
        r.created_by = 'neo4j_resolver'
    RETURN targetBean.name as target_bean
    """

    created_count = 0

    try:
        with db._driver.session() as session:
            # 생성자 정보 조회
            result = session.run(query_constructors, project_name=project_name)
            records = list(result)

            # 각 생성자의 파라미터 처리
            for record in records:
                source_bean = record["source_bean"]
                parameters_json = record["parameters_json"]

                # JSON 파싱
                try:
                    parameters = json.loads(parameters_json)
                except json.JSONDecodeError:
                    logger.warning(f"  ⚠ {source_bean}: parameters JSON 파싱 실패")
                    continue

                # 각 파라미터에 대해 Bean 매칭 시도
                for param in parameters:
                    param_name = param.get("name")
                    param_type = param.get("type")
                    param_order = param.get("order", 0)

                    if not param_type:
                        continue

                    # DEPENDS_ON 관계 생성
                    dep_result = session.run(
                        query_create_dependency,
                        source_bean=source_bean,
                        param_type=param_type,
                        param_name=param_name,
                        param_order=param_order,
                        project_name=project_name
                    )

                    dep_record = dep_result.single()
                    if dep_record:
                        target_bean = dep_record["target_bean"]
                        logger.debug(
                            f"     {source_bean} --(@Constructor {param_name})--> {target_bean}"
                        )
                        created_count += 1

            if created_count > 0:
                logger.debug(f"  → {created_count}개의 Constructor injection 의존성 생성됨")
            else:
                logger.debug("  → Constructor injection 의존성이 생성되지 않음")

    except Exception as e:
        logger.error(f"  ✗ Constructor injection 의존성 해결 중 오류: {e}")
        raise

    return created_count


def _resolve_setter_injections(
    db: "GraphDB",
    project_name: str,
    logger: "Logger"
) -> int:
    """
    Setter 주입 방식의 Bean 의존성을 해결합니다.

    setter 메서드에 @Autowired 어노테이션이 있는 경우
    파라미터 타입과 Bean class_name을 매칭하여 DEPENDS_ON 관계를 생성합니다.

    Args:
        db: Neo4j GraphDB 인스턴스
        project_name: 프로젝트명
        logger: 로거 인스턴스

    Returns:
        int: 생성된 DEPENDS_ON 관계의 개수
    """
    import json

    logger.debug("  → Setter injection 의존성 쿼리 실행 중...")

    # Step 1: setter 정보 조회 쿼리
    query_setters = """
    MATCH (sourceClass:Class)-[:HAS_METHOD]->(setter:Method {project_name: $project_name})
    MATCH (sourceBean:Bean {class_name: sourceClass.name, project_name: $project_name})
    WHERE setter.name STARTS WITH 'set'
      AND setter.parameters IS NOT NULL
      AND setter.annotations_json IS NOT NULL
      AND setter.annotations_json CONTAINS '"Autowired"'
    RETURN sourceBean.name as source_bean,
           sourceBean.class_name as source_class,
           setter.name as setter_name,
           setter.parameters as parameters_json
    ORDER BY source_bean, setter_name
    """

    # Step 2: DEPENDS_ON 관계 생성 쿼리
    query_create_dependency = """
    MATCH (sourceBean:Bean {name: $source_bean, project_name: $project_name})
    MATCH (targetBean:Bean {class_name: $param_type, project_name: $project_name})
    MERGE (sourceBean)-[r:DEPENDS_ON]->(targetBean)
    SET r.injection_type = 'setter',
        r.parameter_name = $param_name,
        r.parameter_type = $param_type,
        r.setter_name = $setter_name,
        r.created_by = 'neo4j_resolver'
    RETURN targetBean.name as target_bean
    """

    created_count = 0

    try:
        with db._driver.session() as session:
            # setter 정보 조회
            result = session.run(query_setters, project_name=project_name)
            records = list(result)

            # 각 setter의 파라미터 처리
            for record in records:
                source_bean = record["source_bean"]
                setter_name = record["setter_name"]
                parameters_json = record["parameters_json"]

                # JSON 파싱
                try:
                    parameters = json.loads(parameters_json)
                except json.JSONDecodeError:
                    logger.warning(f"  ⚠ {source_bean}.{setter_name}: parameters JSON 파싱 실패")
                    continue

                # 각 파라미터에 대해 Bean 매칭 시도 (setter는 일반적으로 파라미터 1개)
                for param in parameters:
                    param_name = param.get("name")
                    param_type = param.get("type")

                    if not param_type:
                        continue

                    # DEPENDS_ON 관계 생성
                    dep_result = session.run(
                        query_create_dependency,
                        source_bean=source_bean,
                        param_type=param_type,
                        param_name=param_name,
                        setter_name=setter_name,
                        project_name=project_name
                    )

                    dep_record = dep_result.single()
                    if dep_record:
                        target_bean = dep_record["target_bean"]
                        logger.debug(
                            f"     {source_bean} --(@Autowired {setter_name})--> {target_bean}"
                        )
                        created_count += 1

            if created_count > 0:
                logger.debug(f"  → {created_count}개의 Setter injection 의존성 생성됨")
            else:
                logger.debug("  → Setter injection 의존성이 생성되지 않음")

    except Exception as e:
        logger.error(f"  ✗ Setter injection 의존성 해결 중 오류: {e}")
        raise

    return created_count


__all__ = [
    "resolve_bean_dependencies_from_neo4j",
]
