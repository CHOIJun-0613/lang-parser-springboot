"""
Summary and statistics helpers for the analysis service.
"""
from __future__ import annotations

from datetime import datetime
from typing import Iterable, Optional

from csa.cli.core.lifecycle import format_duration, format_number
from csa.models.analysis import DatabaseAnalysisStats, JavaAnalysisStats
from csa.utils.logger import get_logger


def get_java_stats_from_neo4j(
    graph_db,
    project_name: str,
    logger,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
) -> JavaAnalysisStats:
    """
    스트리밍 모드용: Neo4j에서 직접 통계를 조회하여 JavaAnalysisStats 생성

    Args:
        graph_db: Neo4j GraphDB 인스턴스
        project_name: 프로젝트명
        logger: 로거 인스턴스
        start_time: 분석 시작 시간 (선택사항)
        end_time: 분석 종료 시간 (선택사항)

    Returns:
        JavaAnalysisStats: 통계 정보
    """
    if start_time is None:
        start_time = datetime.now()
    if end_time is None:
        end_time = datetime.now()

    try:
        # Neo4j에서 프로젝트별 통계 조회
        stats = graph_db.get_database_statistics(project_name)
        node_counts = stats.get("node_counts_by_label", {})

        # 각 라벨별 카운트 추출
        packages = node_counts.get("Package", 0)
        classes = node_counts.get("Class", 0)
        methods = node_counts.get("Method", 0)
        fields = node_counts.get("Field", 0)
        beans = node_counts.get("Bean", 0)
        endpoints = node_counts.get("Endpoint", 0)
        mybatis_mappers = node_counts.get("MyBatisMapper", 0)
        jpa_entities = node_counts.get("JpaEntity", 0)
        jpa_repositories = node_counts.get("JpaRepository", 0)
        jpa_queries = node_counts.get("JpaQuery", 0)
        config_files = node_counts.get("ConfigFile", 0)
        test_classes = node_counts.get("TestClass", 0)
        sql_statements = node_counts.get("SqlStatement", 0)

        logger.info("Neo4j에서 통계 조회 완료:")
        logger.info(f"  - Packages: {packages}")
        logger.info(f"  - Classes: {classes}")
        logger.info(f"  - Methods: {methods}")
        logger.info(f"  - Fields: {fields}")
        logger.info(f"  - Beans: {beans}")
        logger.info(f"  - Endpoints: {endpoints}")

        return JavaAnalysisStats(
            project_name=project_name,
            total_files=0,  # 스트리밍 모드에서는 파일 카운트 추적 안 함
            processed_files=0,
            error_files=0,
            packages=packages,
            classes=classes,
            methods=methods,
            fields=fields,
            beans=beans,
            endpoints=endpoints,
            mybatis_mappers=mybatis_mappers,
            jpa_entities=jpa_entities,
            jpa_repositories=jpa_repositories,
            jpa_queries=jpa_queries,
            config_files=config_files,
            test_classes=test_classes,
            sql_statements=sql_statements,
            start_time=start_time,
            end_time=end_time,
        )

    except Exception as e:
        logger.error(f"Neo4j 통계 조회 실패: {e}")
        # 빈 통계 반환
        return JavaAnalysisStats(
            project_name=project_name,
            packages=0,
            classes=0,
            methods=0,
            fields=0,
            beans=0,
            endpoints=0,
            mybatis_mappers=0,
            jpa_entities=0,
            jpa_repositories=0,
            jpa_queries=0,
            config_files=0,
            test_classes=0,
            sql_statements=0,
        )


def calculate_java_statistics(
    packages: Iterable[object],
    classes: Iterable[object],
    beans: Iterable[object],
    endpoints: Iterable[object],
    mappers: Iterable[object],
    entities: Iterable[object],
    repos: Iterable[object],
    queries: Iterable[object],
    config_files: Iterable[object],
    test_classes: Iterable[object],
    sql_statements: Iterable[object],
) -> JavaAnalysisStats:
    """Calculate aggregated statistics for Java analysis results."""
    packages_list = list(packages)
    classes_list = list(classes)
    beans_list = list(beans)
    endpoints_list = list(endpoints)
    mappers_list = list(mappers)
    entities_list = list(entities)
    repos_list = list(repos)
    queries_list = list(queries)
    config_list = list(config_files)
    tests_list = list(test_classes)
    sql_statements_list = list(sql_statements)
    total_methods = sum(len(class_obj.methods) for class_obj in classes_list)
    total_fields = sum(len(class_obj.properties) for class_obj in classes_list)

    return JavaAnalysisStats(
        packages=len(packages_list),
        classes=len(classes_list),
        methods=total_methods,
        fields=total_fields,
        beans=len(beans_list),
        endpoints=len(endpoints_list),
        mybatis_mappers=len(mappers_list),
        jpa_entities=len(entities_list),
        jpa_repositories=len(repos_list),
        jpa_queries=len(queries_list),
        config_files=len(config_list),
        test_classes=len(tests_list),
        sql_statements=len(sql_statements_list),
    )


def _log_quick_summary(
    overall_start_time: datetime,
    java_stats: Optional[JavaAnalysisStats],
    db_stats: Optional[DatabaseAnalysisStats],
) -> None:
    """Emit a concise analysis summary to the logger."""
    logger = get_logger(__name__, command="analyze")
    overall_end_time = datetime.now()
    overall_duration = (overall_end_time - overall_start_time).total_seconds()

    logger.info("")
    logger.info("=" * 80)
    logger.info("ANALYSIS SUMMARY")
    logger.info("=" * 80)

    if java_stats:
        logger.info("Java Analysis:")
        logger.info(f"  - Packages: {java_stats.packages}")
        logger.info(f"  - Classes: {java_stats.classes}")
        logger.info(f"  - Methods: {java_stats.methods}")
        logger.info(f"  - Fields: {java_stats.fields}")
        logger.info(f"  - Spring Beans: {java_stats.beans}")
        logger.info(f"  - REST Endpoints: {java_stats.endpoints}")
        logger.info(f"  - MyBatis Mappers: {java_stats.mybatis_mappers}")
        logger.info(f"  - JPA Entities: {java_stats.jpa_entities}")
        logger.info(f"  - JPA Repositories: {java_stats.jpa_repositories}")
        logger.info(f"  - JPA Queries: {java_stats.jpa_queries}")
        logger.info(f"  - Config Files: {java_stats.config_files}")
        logger.info(f"  - Test Classes: {java_stats.test_classes}")
        logger.info(f"  - SQL Statements: {java_stats.sql_statements}")

    if db_stats:
        logger.info("Database Analysis:")
        logger.info(f"  - Databases: {db_stats.databases}")
        logger.info(f"  - Tables: {db_stats.tables}")
        logger.info(f"  - Columns: {db_stats.columns}")
        logger.info(f"  - Indexes: {db_stats.indexes}")
        logger.info(f"  - Constraints: {db_stats.constraints}")

    logger.info(f"Total Analysis Time: {format_duration(overall_duration)}")
    logger.info("=" * 80)
    logger.info("====== analyze 작업 종료 ======")
    logger.info("")


def print_analysis_summary(
    overall_start_time: datetime,
    overall_end_time: datetime,
    java_stats: Optional[JavaAnalysisStats],
    db_stats: Optional[DatabaseAnalysisStats],
    dry_run: bool,
    graph_db=None,
    project_name: Optional[str] = None,
) -> None:
    """
    Print a detailed summary of the analysis execution.
    """
    logger = get_logger(__name__, command="analyze")

    title = "분석 작업 결과 [dry-run 모드]" if dry_run else "분석 작업 결과"
    total_duration = (overall_end_time - overall_start_time).total_seconds()

    logger.info("=" * 80)
    logger.info(f"                          {title}")
    logger.info("=" * 80)
    logger.info("")
    logger.info(
        "전체 작업 시간: %s ~ %s",
        overall_start_time.strftime("%Y-%m-%d %H:%M:%S"),
        overall_end_time.strftime("%Y-%m-%d %H:%M:%S"),
    )
    logger.info("총 소요 시간: %s", format_duration(total_duration))
    logger.info("")

    if java_stats:
        duration = java_stats.duration_seconds
        logger.info("-" * 80)
        logger.info("[Java Object 분석 결과]")
        logger.info("-" * 80)
        if java_stats.start_time and java_stats.end_time:
            logger.info(
                "작업 시간: %s ~ %s",
                java_stats.start_time.strftime("%Y-%m-%d %H:%M:%S"),
                java_stats.end_time.strftime("%Y-%m-%d %H:%M:%S"),
            )
        if duration is not None:
            logger.info("소요 시간: %s", format_duration(duration))
        logger.info("")
        logger.info("분석 결과:")
        logger.info("  - Project: %s", java_stats.project_name or "N/A")

        if java_stats.total_files > 0:
            success_rate = (
                java_stats.processed_files / java_stats.total_files * 100
                if java_stats.total_files
                else 0.0
            )
            logger.info(
                "  - Java 파일: %s/%s개 (성공률: %.1f%%)",
                format_number(java_stats.processed_files),
                format_number(java_stats.total_files),
                success_rate,
            )
            if java_stats.error_files > 0:
                logger.info(
                    "  - 오류 파일: %s개",
                    format_number(java_stats.error_files),
                )

        logger.info("  - Packages: %s개", format_number(java_stats.packages))
        logger.info("  - Classes: %s개", format_number(java_stats.classes))
        logger.info("  - Methods: %s개", format_number(java_stats.methods))
        logger.info("  - Fields: %s개", format_number(java_stats.fields))
        logger.info("  - Spring Beans: %s개", format_number(java_stats.beans))
        logger.info("  - REST Endpoints: %s개", format_number(java_stats.endpoints))
        logger.info("  - MyBatis Mappers: %s개", format_number(java_stats.mybatis_mappers))
        logger.info("  - JPA Entities: %s개", format_number(java_stats.jpa_entities))
        logger.info("  - JPA Repositories: %s개", format_number(java_stats.jpa_repositories))
        logger.info("  - SQL Statements: %s개", format_number(java_stats.sql_statements))

    if db_stats:
        logger.info("")
        logger.info("-" * 80)
        logger.info("[Database Object 분석 결과]")
        logger.info("-" * 80)
        if db_stats.start_time and db_stats.end_time:
            logger.info(
                "작업 시간: %s ~ %s",
                db_stats.start_time.strftime("%Y-%m-%d %H:%M:%S"),
                db_stats.end_time.strftime("%Y-%m-%d %H:%M:%S"),
            )
            duration = db_stats.duration_seconds
            if duration is not None:
                logger.info("소요 시간: %s", format_duration(duration))

        logger.info("  - DDL 파일: %s개", format_number(db_stats.ddl_files))
        logger.info("  - Databases: %s개", format_number(db_stats.databases))
        logger.info("  - Tables: %s개", format_number(db_stats.tables))
        logger.info("  - Columns: %s개", format_number(db_stats.columns))
        logger.info("  - Indexes: %s개", format_number(db_stats.indexes))
        logger.info("  - Constraints: %s개", format_number(db_stats.constraints))

    # Neo4j 실제 저장 통계 출력
    if graph_db and not dry_run:
        logger.info("")
        logger.info("-" * 80)
        logger.info("[Neo4j Database 저장 현황]")
        logger.info("-" * 80)

        try:
            # 전체 DB 통계 조회
            all_stats = graph_db.get_database_statistics(None)

            logger.info("전체 데이터베이스 저장 객체:")
            logger.info("  - 총 노드 수: %s개", format_number(all_stats["total_nodes"]))
            logger.info("  - 총 관계 수: %s개", format_number(all_stats["total_relationships"]))

            # 프로젝트별 통계가 의미있는 경우에만 추가 표시
            if project_name:
                project_stats = graph_db.get_database_statistics(project_name)
                if project_stats["total_nodes"] > 0:
                    logger.info("")
                    logger.info(f"현재 프로젝트({project_name}) 저장 객체:")
                    logger.info("  - 노드 수: %s개", format_number(project_stats["total_nodes"]))
                    logger.info("  - 관계 수: %s개", format_number(project_stats["total_relationships"]))

            if all_stats["node_counts_by_label"]:
                logger.info("")
                logger.info("라벨별 노드 수 (전체):")
                for label, count in all_stats["node_counts_by_label"].items():
                    logger.info("  - %s: %s개", label, format_number(count))

            if all_stats["relationship_counts_by_type"]:
                logger.info("")
                logger.info("관계 타입별 수 (전체):")
                for rel_type, count in all_stats["relationship_counts_by_type"].items():
                    logger.info("  - %s: %s개", rel_type, format_number(count))

        except Exception as e:  # pylint: disable=broad-except
            logger.warning("Neo4j 통계 조회 실패: %s", str(e))

    _log_quick_summary(overall_start_time, java_stats, db_stats)
