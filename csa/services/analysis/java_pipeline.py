"""
Java parsing pipeline helpers.
"""
from __future__ import annotations

from typing import Optional, Tuple

from csa.models.analysis import JavaAnalysisArtifacts
from csa.services.analysis.options import determine_project_name
from csa.services.java_parser import parse_java_project_full


def analyze_full_project_java(
    java_source_folder: str,
    project_name: Optional[str],
    logger,
) -> Tuple[JavaAnalysisArtifacts, str]:
    """Parse Java sources and resolve the effective project name."""
    logger.info("Parsing Java project at: %s", java_source_folder)
    (
        packages_to_add,
        classes_to_add,
        class_to_package_map,
        beans,
        dependencies,
        endpoints,
        mybatis_mappers,
        jpa_entities,
        jpa_repositories,
        jpa_queries,
        config_files,
        test_classes,
        sql_statements,
        detected_project_name,
    ) = parse_java_project_full(java_source_folder)

    final_project_name = determine_project_name(project_name, detected_project_name, logger)
    logger.info("Project name: %s", final_project_name)
    logger.info("Found %s packages and %s classes.", len(packages_to_add), len(classes_to_add))

    artifacts = JavaAnalysisArtifacts(
        packages=packages_to_add,
        classes=classes_to_add,
        class_to_package_map=class_to_package_map,
        beans=beans,
        dependencies=dependencies,
        endpoints=endpoints,
        mybatis_mappers=mybatis_mappers,
        jpa_entities=jpa_entities,
        jpa_repositories=jpa_repositories,
        jpa_queries=jpa_queries,
    config_files=config_files,
    test_classes=test_classes,
    sql_statements=sql_statements,
    project_name=final_project_name,
)

    return artifacts, final_project_name


def parse_java_with_concurrency(
    java_source_folder: str,
    concurrent: bool,
    workers: Optional[int],
    logger,
) -> JavaAnalysisArtifacts:
    """Placeholder for concurrent parsing; falls back to single-threaded parsing."""
    if concurrent:
        logger.warning("Concurrent processing requested but not yet implemented. Using single-threaded processing.")
        logger.info("Using single-threaded processing")

    artifacts, _ = analyze_full_project_java(java_source_folder, None, logger)
    return artifacts


__all__ = [
    "analyze_full_project_java",
    "parse_java_with_concurrency",
]
