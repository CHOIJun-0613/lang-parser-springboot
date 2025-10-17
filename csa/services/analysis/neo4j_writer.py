"""
Helpers for persisting analysis results into Neo4j.
"""
from __future__ import annotations

import os
import time
from contextlib import contextmanager
from datetime import datetime
from typing import Optional, Sequence

from csa.cli.core.lifecycle import format_duration
from csa.models.analysis import JavaAnalysisArtifacts, JavaAnalysisStats
from csa.models.graph_entities import Project
from csa.services.analysis.summary import calculate_java_statistics
from csa.services.graph_db import GraphDB
from csa.services.java_parser import (
    analyze_bean_dependencies,
    extract_beans_from_classes,
    extract_endpoints_from_classes,
    extract_jpa_entities_from_classes,
    extract_mybatis_mappers_from_classes,
    extract_sql_statements_from_mappers,
    extract_test_classes_from_classes,
)
from csa.dbwork.connection_pool import get_connection_pool


def connect_to_neo4j_db(
    neo4j_uri: str,
    neo4j_user: str,
    neo4j_password: str,
    neo4j_database: str,
    logger,
) -> GraphDB:
    """Initialise (or reuse) a Neo4j connection pool and GraphDB instance."""
    logger.info("Connecting to Neo4j at %s...", neo4j_uri)
    pool = get_connection_pool()
    if not pool.is_initialized():
        pool_size = int(os.getenv("NEO4J_POOL_SIZE", "10"))
        logger.info("Initializing Neo4j connection pool with %s connections...", pool_size)
        pool.initialize(neo4j_uri, neo4j_user, neo4j_password, neo4j_database, pool_size)
        logger.info("Connected to Neo4j at %s (database: %s)", neo4j_uri, neo4j_database)
    else:
        logger.info("Using existing connection pool (database: %s)", neo4j_database)

    return GraphDB(neo4j_uri, neo4j_user, neo4j_password, neo4j_database)


@contextmanager
def _session_scope(db: GraphDB):
    """Yield a Neo4j session, preferring the shared connection pool when available."""
    pool = get_connection_pool()
    if pool.is_initialized():
        with pool.session() as session:
            yield session
    else:
        with db._driver.session() as session:  # pylint: disable=protected-access
            yield session


def clean_java_objects(db: GraphDB, logger) -> None:
    """Remove previously stored Java-related nodes."""
    logger.info("Cleaning Java objects...")
    def _execute(session):
        session.run("MATCH (n:Package) DETACH DELETE n")
        session.run("MATCH (n:Class) DETACH DELETE n")
        session.run("MATCH (n:Method) DETACH DELETE n")
        session.run("MATCH (n:Field) DETACH DELETE n")
        session.run("MATCH (n:Bean) DETACH DELETE n")
        session.run("MATCH (n:Endpoint) DETACH DELETE n")
        session.run("MATCH (n:MyBatisMapper) DETACH DELETE n")
        session.run("MATCH (n:JpaEntity) DETACH DELETE n")
        session.run("MATCH (n:ConfigFile) DETACH DELETE n")
        session.run("MATCH (n:TestClass) DETACH DELETE n")
        session.run("MATCH (n:SqlStatement) DETACH DELETE n")

    with _session_scope(db) as session:
        _execute(session)


def clean_db_objects(db: GraphDB, logger) -> None:
    """Remove previously stored database-related nodes."""
    logger.info("Cleaning database objects...")
    def _execute(session):
        session.run("MATCH (n:Database) DETACH DELETE n")
        session.run("MATCH (n:Table) DETACH DELETE n")
        session.run("MATCH (n:Column) DETACH DELETE n")
        session.run("MATCH (n:Index) DETACH DELETE n")
        session.run("MATCH (n:Constraint) DETACH DELETE n")

    with _session_scope(db) as session:
        _execute(session)


def _log_progress(prefix: str, current: int, total: int, last_percent: int, logger) -> int:
    """Log percentage progress in 10%% steps and return updated percentage."""
    percent = int((current / total) * 100) if total else 100
    if percent >= last_percent + 10 or current == total:
        last_percent = percent
        logger.info("   - %s 진행률 [%s/%s] (%s%%)", prefix, current, total, percent)
    return last_percent


def _log_duration(message: str, item_count: int, start_time: float, logger) -> None:
    """Helper to log duration for batched operations."""
    elapsed = time.time() - start_time
    logger.info("? %s %s개 처리 (%.2fs)", message, item_count, elapsed)


def add_springboot_objects(
    db: GraphDB,
    beans: Sequence[object],
    dependencies: Sequence[object],
    endpoints: Sequence[object],
    mybatis_mappers: Sequence[object],
    jpa_entities: Sequence[object],
    jpa_repositories: Sequence[object],
    jpa_queries: Sequence[object],
    config_files: Sequence[object],
    test_classes: Sequence[object],
    sql_statements: Sequence[object],
    project_name: str,
    logger,
) -> None:
    """Persist Spring Boot–related artifacts to Neo4j."""
    if beans:
        logger.info("DB 저장 -  %s Spring Beans to database...", len(beans))
        start_time = time.time()
        last_percent = 0
        for idx, bean in enumerate(beans, 1):
            db.add_bean(bean, project_name)
            last_percent = _log_progress("beans 저장", idx, len(beans), last_percent, logger)
        _log_duration("Added Spring Beans", len(beans), start_time, logger)

    if dependencies:
        logger.info("DB 저장 -  %s Bean dependencies to database...", len(dependencies))
        start_time = time.time()
        for dependency in dependencies:
            db.add_bean_dependency(dependency, project_name)
        _log_duration("Added Bean dependencies", len(dependencies), start_time, logger)

    if endpoints:
        logger.info("DB 저장 -  %s REST endpoints to database...", len(endpoints))
        start_time = time.time()
        for endpoint in endpoints:
            db.add_endpoint(endpoint, project_name)
        _log_duration("Added REST endpoints", len(endpoints), start_time, logger)

    if mybatis_mappers:
        logger.info("DB 저장 -  %s MyBatis mappers to database...", len(mybatis_mappers))
        start_time = time.time()
        for mapper in mybatis_mappers:
            db.add_mybatis_mapper(mapper, project_name)
        _log_duration("Added MyBatis mappers", len(mybatis_mappers), start_time, logger)

    if jpa_entities:
        logger.info("DB 저장 -  %s JPA entities to database...", len(jpa_entities))
        start_time = time.time()
        for entity in jpa_entities:
            db.add_jpa_entity(entity, project_name)
        _log_duration("Added JPA entities", len(jpa_entities), start_time, logger)

    if jpa_repositories:
        logger.info("DB 저장 -  %s JPA repositories to database...", len(jpa_repositories))
        start_time = time.time()
        for repository in jpa_repositories:
            db.add_jpa_repository(repository, project_name)
        _log_duration("Added JPA repositories", len(jpa_repositories), start_time, logger)

    if jpa_queries:
        logger.info("DB 저장 -  %s JPA queries to database...", len(jpa_queries))
        start_time = time.time()
        last_percent = 0
        for idx, query in enumerate(jpa_queries, 1):
            db.add_jpa_query(query, project_name)
            last_percent = _log_progress("jpa_queries 저장", idx, len(jpa_queries), last_percent, logger)
        _log_duration("Added JPA queries", len(jpa_queries), start_time, logger)

    if config_files:
        logger.info("DB 저장 -  %s configuration files to database...", len(config_files))
        start_time = time.time()
        for config in config_files:
            db.add_config_file(config, project_name)
        _log_duration("Added configuration files", len(config_files), start_time, logger)

    if test_classes:
        logger.info("DB 저장 -  %s test classes to database...", len(test_classes))
        start_time = time.time()
        for test_class in test_classes:
            db.add_test_class(test_class, project_name)
        _log_duration("Added test classes", len(test_classes), start_time, logger)

    if sql_statements:
        logger.info("DB 저장 -  %s SQL statements to database...", len(sql_statements))
        start_time = time.time()
        last_percent = 0
        for idx, sql_statement in enumerate(sql_statements, 1):
            db.add_sql_statement(sql_statement, project_name)
            with _session_scope(db) as session:
                session.execute_write(
                    db._create_mapper_sql_relationship_tx,  # pylint: disable=protected-access
                    sql_statement.mapper_name,
                    sql_statement.id,
                    project_name,
                )

            last_percent = _log_progress("sql_statements 저장", idx, len(sql_statements), last_percent, logger)
        _log_duration("Added SQL statements", len(sql_statements), start_time, logger)


def add_single_class_objects(
    db: GraphDB,
    class_node,
    package_name: str,
    project_name: str,
    logger,
) -> None:
    """Persist artifacts derived from a single class node."""
    classes_list = [class_node]
    beans = extract_beans_from_classes(classes_list)
    dependencies = analyze_bean_dependencies(classes_list, beans)
    endpoints = extract_endpoints_from_classes(classes_list)
    mybatis_mappers = extract_mybatis_mappers_from_classes(classes_list)
    jpa_entities = extract_jpa_entities_from_classes(classes_list)
    test_classes = extract_test_classes_from_classes(classes_list)
    sql_statements = extract_sql_statements_from_mappers(mybatis_mappers, project_name)

    if beans:
        logger.info("DB 저장 -  %s Spring Beans to database...", len(beans))
        for bean in beans:
            db.add_bean(bean, project_name)

    if dependencies:
        logger.info("DB 저장 -  %s Bean dependencies to database...", len(dependencies))
        for dependency in dependencies:
            db.add_bean_dependency(dependency, project_name)

    if endpoints:
        logger.info("DB 저장 -  %s REST endpoints to database...", len(endpoints))
        for endpoint in endpoints:
            db.add_endpoint(endpoint, project_name)

    if mybatis_mappers:
        logger.info("DB 저장 -  %s MyBatis mappers to database...", len(mybatis_mappers))
        for mapper in mybatis_mappers:
            db.add_mybatis_mapper(mapper, project_name)

    if jpa_entities:
        logger.info("DB 저장 -  %s JPA entities to database...", len(jpa_entities))
        for entity in jpa_entities:
            db.add_jpa_entity(entity, project_name)

    if test_classes:
        logger.info("DB 저장 -  %s test classes to database...", len(test_classes))
        for test_class in test_classes:
            db.add_test_class(test_class, project_name)

    if sql_statements:
        logger.info("DB 저장 -  %s SQL statements to database...", len(sql_statements))
        for sql_statement in sql_statements:
            db.add_sql_statement(sql_statement, project_name)

            with _session_scope(db) as session:
                session.execute_write(
                    db._create_mapper_sql_relationship_tx,  # pylint: disable=protected-access
                    sql_statement.mapper_name,
                    sql_statement.id,
                    project_name,
                )


def add_single_class_objects_streaming(
    db: GraphDB,
    class_node,
    package_name: str,
    project_name: str,
    logger,
) -> dict:
    """
    파일별 즉시 저장 (스트리밍 방식)

    파일 하나를 파싱한 후 즉시 Neo4j에 저장합니다.
    Bean 의존성은 Neo4j 쿼리로 해결하므로 여기서는 생성하지 않습니다.

    Args:
        db: Neo4j GraphDB 인스턴스
        class_node: 파싱된 클래스 노드
        package_name: 패키지명
        project_name: 프로젝트명
        logger: 로거 인스턴스

    Returns:
        dict: 처리 통계
            {
                'beans': int,
                'endpoints': int,
                'jpa_entities': int,
                'jpa_repositories': int,
                'jpa_queries': int,
                'test_classes': int,
                'mybatis_mappers': int,
                'sql_statements': int,
            }
    """
    from .jpa import extract_jpa_queries_from_repositories, extract_jpa_repositories_from_classes

    classes_list = [class_node]
    stats = {
        'beans': 0,
        'endpoints': 0,
        'jpa_entities': 0,
        'jpa_repositories': 0,
        'jpa_queries': 0,
        'test_classes': 0,
        'mybatis_mappers': 0,
        'sql_statements': 0,
    }

    # Bean 추출 및 저장 (의존성 해결은 제외)
    beans = extract_beans_from_classes(classes_list)
    if beans:
        for bean in beans:
            db.add_bean(bean, project_name)
        stats['beans'] = len(beans)
        logger.debug(f"  → Bean {len(beans)}개 저장")

    # Endpoint 추출 및 저장
    endpoints = extract_endpoints_from_classes(classes_list)
    if endpoints:
        for endpoint in endpoints:
            db.add_endpoint(endpoint, project_name)
        stats['endpoints'] = len(endpoints)
        logger.debug(f"  → Endpoint {len(endpoints)}개 저장")

    # JPA Entity 추출 및 저장
    jpa_entities = extract_jpa_entities_from_classes(classes_list)
    if jpa_entities:
        for entity in jpa_entities:
            db.add_jpa_entity(entity, project_name)
        stats['jpa_entities'] = len(jpa_entities)
        logger.debug(f"  → JPA Entity {len(jpa_entities)}개 저장")

    # JPA Repository 추출 및 저장 + Queries 즉시 추출
    jpa_repositories = extract_jpa_repositories_from_classes(classes_list)
    if jpa_repositories:
        for repo in jpa_repositories:
            db.add_jpa_repository(repo, project_name)
        stats['jpa_repositories'] = len(jpa_repositories)
        logger.debug(f"  → JPA Repository {len(jpa_repositories)}개 저장")

        # JPA Queries 즉시 추출 및 저장
        jpa_queries = extract_jpa_queries_from_repositories(jpa_repositories)
        if jpa_queries:
            for query in jpa_queries:
                db.add_jpa_query(query, project_name)
            stats['jpa_queries'] = len(jpa_queries)
            logger.debug(f"  → JPA Query {len(jpa_queries)}개 저장")

    # Test 추출 및 저장
    test_classes = extract_test_classes_from_classes(classes_list)
    if test_classes:
        for test_class in test_classes:
            db.add_test_class(test_class, project_name)
        stats['test_classes'] = len(test_classes)
        logger.debug(f"  → Test Class {len(test_classes)}개 저장")

    # MyBatis Mapper 추출 및 저장 + SQL Statements 즉시 추출
    mybatis_mappers = extract_mybatis_mappers_from_classes(classes_list)
    if mybatis_mappers:
        for mapper in mybatis_mappers:
            db.add_mybatis_mapper(mapper, project_name)
        stats['mybatis_mappers'] = len(mybatis_mappers)
        logger.debug(f"  → MyBatis Mapper {len(mybatis_mappers)}개 저장")

        # SQL Statements 즉시 추출 및 저장
        sql_statements = extract_sql_statements_from_mappers(mybatis_mappers, project_name)
        if sql_statements:
            for sql_statement in sql_statements:
                db.add_sql_statement(sql_statement, project_name)

                with _session_scope(db) as session:
                    session.execute_write(
                        db._create_mapper_sql_relationship_tx,  # pylint: disable=protected-access
                        sql_statement.mapper_name,
                        sql_statement.id,
                        project_name,
                    )
            stats['sql_statements'] = len(sql_statements)
            logger.debug(f"  → SQL Statement {len(sql_statements)}개 저장")

    return stats


def _add_packages(db: GraphDB, packages: Sequence[object], project_name: str, logger) -> None:
    """Helper for writing package nodes."""
    logger.info("DB 저장 -  %s packages...", len(packages))
    for package in packages:
        db.add_package(package, project_name)


def _add_classes(
    db: GraphDB,
    classes: Sequence[object],
    class_to_package_map: dict,
    project_name: str,
    concurrent: bool,
    workers: Optional[int],
    logger,
) -> None:
    """Persist class nodes, optionally using concurrent helpers on GraphDB."""
    if concurrent:
        logger.info("DB 저장 -  %s classes with concurrent processing...", len(classes))
        db.add_classes_concurrent(classes, class_to_package_map, project_name, workers)
        return

    total = len(classes)
    logger.info("DB 저장 -  %s classes...", total)
    last_percent = 0
    for idx, class_obj in enumerate(classes, 1):
        package_name = class_to_package_map.get(class_obj.name, "unknown")
        db.add_class(class_obj, package_name, project_name)
        last_percent = _log_progress("classes 저장", idx, total, last_percent, logger)


def save_java_objects_to_neo4j(
    db: Optional[GraphDB],
    artifacts: JavaAnalysisArtifacts,
    project_name: str,
    clean: bool,
    concurrent: bool,
    workers: Optional[int],
    logger,
) -> JavaAnalysisStats:
    """Persist Java analysis artifacts to Neo4j and return corresponding stats."""
    java_start_time = datetime.now()

    java_stats = calculate_java_statistics(
        artifacts.packages,
        artifacts.classes,
        artifacts.beans,
        artifacts.endpoints,
        artifacts.mybatis_mappers,
        artifacts.jpa_entities,
        artifacts.jpa_repositories,
        artifacts.jpa_queries,
        artifacts.config_files,
        artifacts.test_classes,
        artifacts.sql_statements,
    )
    java_stats.project_name = project_name

    if db is None:
        logger.info("Connecting to Neo4j...")
        neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        neo4j_password = os.getenv("NEO4J_PASSWORD")
        neo4j_database = os.getenv("NEO4J_DATABASE", "neo4j")

        if not neo4j_password:
            logger.error("NEO4J_PASSWORD not set - cannot connect to database")
            raise ValueError("NEO4J_PASSWORD environment variable is required")

        db = connect_to_neo4j_db(neo4j_uri, neo4j_user, neo4j_password, neo4j_database, logger)

    logger.info("DB 저장 -  project: %s", project_name)
    project = Project(
        name=project_name,
        display_name=project_name,
        description=f"Java project: {project_name}",
        repository_url="",
        language="Java",
        framework="Spring Boot",
        version="1.0",
        ai_description="",
        created_at=datetime.now().strftime("%Y/%m/%d %H:%M:%S.%f")[:-3],
    )
    db.add_project(project)

    _add_packages(db, artifacts.packages, project_name, logger)
    _add_classes(db, artifacts.classes, artifacts.class_to_package_map, project_name, concurrent, workers, logger)
    add_springboot_objects(
        db,
        artifacts.beans,
        artifacts.dependencies,
        artifacts.endpoints,
        artifacts.mybatis_mappers,
        artifacts.jpa_entities,
        artifacts.jpa_repositories,
        artifacts.jpa_queries,
        artifacts.config_files,
        artifacts.test_classes,
        artifacts.sql_statements,
        project_name,
        logger,
    )

    # Bean 의존성 해결 (Neo4j 기반)
    # artifacts.beans가 Neo4j에 저장된 후 실행
    if artifacts.beans:
        logger.info("")
        from csa.services.java_analysis.bean_dependency_resolver import (
            resolve_bean_dependencies_from_neo4j
        )
        resolve_bean_dependencies_from_neo4j(db, project_name, logger)

    java_end_time = datetime.now()
    java_stats.start_time = java_start_time
    java_stats.end_time = java_end_time
    logger.info("Java object analysis completed in %s", format_duration((java_end_time - java_start_time).total_seconds()))

    return java_stats


__all__ = [
    "add_single_class_objects",
    "add_single_class_objects_streaming",
    "add_springboot_objects",
    "clean_db_objects",
    "clean_java_objects",
    "connect_to_neo4j_db",
    "save_java_objects_to_neo4j",
]
