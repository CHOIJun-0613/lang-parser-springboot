"""
Summary and statistics helpers for the analysis service.
"""
from __future__ import annotations

from datetime import datetime
from typing import Iterable, Optional

from csa.cli.core.lifecycle import format_duration, format_number
from csa.models.analysis import DatabaseAnalysisStats, JavaAnalysisStats
from csa.utils.logger import get_logger


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

    _log_quick_summary(overall_start_time, java_stats, db_stats)
