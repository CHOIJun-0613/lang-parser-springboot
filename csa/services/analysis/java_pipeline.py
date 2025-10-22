"""
Java parsing pipeline helpers.
"""
from __future__ import annotations

import os
from typing import Optional, Tuple

from csa.models.analysis import JavaAnalysisArtifacts
from csa.services.analysis.options import determine_project_name
from csa.services.graph_db import GraphDB
from csa.services.java_parser import parse_java_project_full


def analyze_full_project_java(
    java_source_folder: str,
    project_name: Optional[str],
    logger,
    graph_db: Optional[GraphDB] = None,
) -> Tuple[JavaAnalysisArtifacts, str]:
    """
    Parse Java sources and resolve the effective project name.

    Args:
        java_source_folder: Java 소스 디렉토리 경로
        project_name: 프로젝트명 (선택사항)
        logger: 로거 인스턴스
        graph_db: Neo4j GraphDB 인스턴스 (스트리밍 모드에 필요)

    Returns:
        Tuple[JavaAnalysisArtifacts, str]: 분석 결과 및 프로젝트명

    Environment Variables:
        USE_STREAMING_PARSE: 'true'로 설정 시 스트리밍 모드 사용 (기본값: 'false')
    """
    # 스트리밍 모드 확인
    use_streaming = os.getenv("USE_STREAMING_PARSE", "false").lower() == "true"

    if use_streaming:
        logger.info("Using STREAMING parsing mode (memory efficient)")
        return _analyze_with_streaming(java_source_folder, project_name, graph_db, logger)
    else:
        logger.info("Using BATCH parsing mode (traditional)")
        return _analyze_with_batch(java_source_folder, project_name, logger)


def _analyze_with_streaming(
    java_source_folder: str,
    project_name: Optional[str],
    graph_db: Optional[GraphDB],
    logger,
) -> Tuple[JavaAnalysisArtifacts, str]:
    """
    스트리밍 방식으로 Java 프로젝트 분석.

    파일을 하나씩 파싱하고 즉시 Neo4j에 저장하여 메모리 효율성을 극대화합니다.

    Args:
        java_source_folder: Java 소스 디렉토리 경로
        project_name: 프로젝트명 (선택사항)
        graph_db: Neo4j GraphDB 인스턴스 (필수)
        logger: 로거 인스턴스

    Returns:
        Tuple[JavaAnalysisArtifacts, str]: 분석 결과 및 프로젝트명
    """
    if not graph_db:
        raise ValueError("GraphDB instance is required for streaming mode")

    from csa.services.java_analysis.project import parse_java_project_streaming, extract_project_name

    # 프로젝트명 결정
    detected_project_name = extract_project_name(java_source_folder)
    final_project_name = determine_project_name(project_name, detected_project_name, logger)

    logger.info("Project name: %s", final_project_name)
    logger.info("Parsing Java project at: %s", java_source_folder)

    # 시작 시간 기록
    from datetime import datetime
    start_time = datetime.now()

    # 스트리밍 파싱 실행
    stats = parse_java_project_streaming(
        java_source_folder,
        graph_db,
        final_project_name,
    )

    # 종료 시간 기록
    end_time = datetime.now()
    stats['start_time'] = start_time
    stats['end_time'] = end_time

    logger.info("Streaming parsing complete:")
    logger.info("  - Packages: %s", stats['packages'])
    logger.info("  - Classes: %s", stats['classes'])
    logger.info("  - Beans: %s", stats['beans'])
    logger.info("  - Endpoints: %s", stats['endpoints'])

    # Method -> SqlStatement CALLS 관계 생성 (스트리밍 모드)
    if stats.get('sql_statements', 0) > 0:
        logger.info("")
        logger.info("Creating Method -> SqlStatement CALLS relationships...")
        relationships_created = graph_db.create_method_sql_relationships(final_project_name)
        logger.info("Created %s Method -> SqlStatement relationships", relationships_created)

    # JavaAnalysisArtifacts 생성 (빈 리스트로, 실제 데이터는 Neo4j에 있음)
    artifacts = JavaAnalysisArtifacts(
        packages=[],  # 스트리밍 모드에서는 메모리에 저장하지 않음
        classes=[],
        class_to_package_map={},
        beans=[],
        dependencies=[],
        endpoints=[],
        mybatis_mappers=[],
        jpa_entities=[],
        jpa_repositories=[],
        jpa_queries=[],
        config_files=[],
        test_classes=[],
        sql_statements=[],
        project_name=final_project_name,
        metadata={
            'start_time': start_time,
            'end_time': end_time,
            'total_files': stats.get('total_files', 0),
            'processed_files': stats.get('processed_files', 0),
        },
    )

    return artifacts, final_project_name


def _analyze_with_batch(
    java_source_folder: str,
    project_name: Optional[str],
    logger,
) -> Tuple[JavaAnalysisArtifacts, str]:
    """
    배치 방식으로 Java 프로젝트 분석 (기존 방식).

    모든 클래스를 메모리에 로드한 후 일괄 처리합니다.

    Args:
        java_source_folder: Java 소스 디렉토리 경로
        project_name: 프로젝트명 (선택사항)
        logger: 로거 인스턴스

    Returns:
        Tuple[JavaAnalysisArtifacts, str]: 분석 결과 및 프로젝트명
    """
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
