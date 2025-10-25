"""
High-level orchestration for project analysis.
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Dict, Optional

from csa.models.analysis import AnalysisResult, DatabaseAnalysisStats, JavaAnalysisStats
from csa.models.graph_entities import Project
from csa.services.analysis.db_pipeline import analyze_full_project_db
from csa.services.analysis.java_pipeline import analyze_full_project_java
from csa.services.analysis.neo4j_writer import save_java_objects_to_neo4j
from csa.services.analysis.summary import print_analysis_summary
from csa.services.graph_db import GraphDB


def _prepare_database(
    dry_run: bool,
    clean: bool,
    all_objects: bool,
    java_object: bool,
    db_object: bool,
    neo4j_uri: str,
    neo4j_user: str,
    neo4j_password: Optional[str],
    neo4j_database: str,
    logger,
) -> Optional[GraphDB]:
    """Initialise GraphDB connection and perform optional cleanup."""
    if dry_run:
        logger.info("Running in dry-run mode - no database operations will be performed")
        return None

    if not neo4j_password:
        raise ValueError("NEO4J_PASSWORD is required for database operations")

    db = GraphDB(neo4j_uri, neo4j_user, neo4j_password, neo4j_database)

    if clean:
        # 인덱스는 유지 (MERGE 성능 유지)
        # clean_database()로 데이터만 삭제되고 인덱스는 남음

        if all_objects:
            logger.info("Cleaning all database objects...")
            db.clean_database()
            logger.info("All database objects cleaned successfully")
        elif java_object:
            logger.info("Cleaning Java objects only...")
            db.clean_java_objects()
            logger.info("Java objects cleaned successfully")
        elif db_object:
            logger.info("Cleaning DB objects only...")
            db.clean_db_objects()
            logger.info("DB objects cleaned successfully")

    # 인덱스 확인 및 생성 (없으면 생성, 있으면 건너뜀)
    # 데이터 저장 전에 실행하여 MERGE 성능 보장
    logger.info("")
    db.ensure_indexes()
    logger.info("")

    return db


def _resolve_db_script_folder(db_script_folder: Optional[str], logger) -> Optional[str]:
    """Resolve DB script folder from arguments or environment."""
    if db_script_folder:
        return db_script_folder

    env_folder = os.getenv("DB_SCRIPT_FOLDER")
    if env_folder:
        logger.info("Using DB_SCRIPT_FOLDER from environment: %s", env_folder)
    return env_folder


def _resolve_project_path(java_source_folder: Optional[str]) -> str:
    """Return absolute project path when available."""
    if not java_source_folder:
        return ""

    try:
        normalized_path = os.path.abspath(java_source_folder)
    except (TypeError, OSError):
        return ""

    if not os.path.exists(normalized_path):
        return ""

    return normalized_path


def _count_project_files(project_path: str) -> int:
    """Count every file under the project path excluding hidden directories."""
    if not project_path or not os.path.isdir(project_path):
        return 0

    total_files = 0
    for _, dirnames, filenames in os.walk(project_path):
        dirnames[:] = [dirname for dirname in dirnames if not dirname.startswith(".")]
        total_files += len(filenames)
    return total_files


def analyze_project(
    java_source_folder: str,
    project_name: str,
    application_name: Optional[str],
    db_script_folder: Optional[str],
    neo4j_uri: str,
    neo4j_user: str,
    neo4j_password: Optional[str],
    neo4j_database: str,
    clean: bool,
    dry_run: bool,
    java_object: bool,
    db_object: bool,
    all_objects: bool,
    class_name: Optional[str],
    update: bool,
    logger,
    skip_ai: bool = False,  # backward compatibility
) -> Dict[str, object]:
    """Analyze project artifacts and optionally persist them into Neo4j."""
    overall_start_time = datetime.now()
    resolved_db_folder = _resolve_db_script_folder(db_script_folder, logger)
    java_stats: Optional[JavaAnalysisStats] = None
    db_stats: Optional[DatabaseAnalysisStats] = None
    db: Optional[GraphDB] = None
    project_path = _resolve_project_path(java_source_folder)
    fallback_project_name = ""
    fallback_source = project_path or java_source_folder or ""
    if not project_name and fallback_source:
        normalized_source = os.path.normpath(str(fallback_source))
        candidate = os.path.basename(normalized_source.rstrip("\\/"))
        if candidate not in ("", ".", "..", os.path.sep):
            fallback_project_name = candidate
    effective_project_name = project_name or fallback_project_name or ""
    timestamp = overall_start_time.strftime("%Y/%m/%d %H:%M:%S.%f")[:-3]
    project_entity = Project(
        name=effective_project_name,
        description="",
        ai_description="",
        application_name=application_name or "",
        number_of_files=_count_project_files(project_path),
        path=project_path,
        created_at=timestamp,
        updated_at=timestamp,
    )
    project_name = project_entity.name

    try:
        db = _prepare_database(
            dry_run,
            clean,
            all_objects,
            java_object,
            db_object,
            neo4j_uri,
            neo4j_user,
            neo4j_password,
            neo4j_database,
            logger,
        )

        # DB 분석을 먼저 수행하여 스키마 정보를 Neo4j에 저장
        if all_objects or db_object:
            if resolved_db_folder:
                if os.path.exists(resolved_db_folder):
                    db_stats = analyze_full_project_db(db, resolved_db_folder, project_name, dry_run, logger)
                else:
                    logger.warning("Database script folder does not exist: %s", resolved_db_folder)
                    logger.info("Please check the DB_SCRIPT_FOLDER path in your .env file or use --db-script-folder option")
            else:
                logger.warning("Database script folder not provided - skipping database analysis")
                logger.info("To analyze database objects, use --db-script-folder option to specify the path to SQL script files")

        # Java 분석을 나중에 수행하여 DB 스키마와의 관계를 정확하게 연결
        if all_objects or java_object:
            # 스트리밍 모드 확인
            use_streaming = os.getenv("USE_STREAMING_PARSE", "false").lower() == "true"

            if use_streaming and db:
                db.add_project(project_entity)

            artifacts, final_project_name = analyze_full_project_java(
                java_source_folder,
                project_name,
                logger,
                graph_db=db,  # 스트리밍 모드를 위해 graph_db 전달
            )

            if final_project_name:
                project_entity.name = final_project_name
                project_name = final_project_name

            if use_streaming:
                # 스트리밍 모드: Neo4j에서 직접 통계 조회
                from csa.services.analysis.summary import get_java_stats_from_neo4j
                # artifacts.metadata에 시간 정보가 있으면 전달
                start_time = artifacts.metadata.get('start_time') if hasattr(artifacts, 'metadata') and artifacts.metadata else None
                end_time = artifacts.metadata.get('end_time') if hasattr(artifacts, 'metadata') and artifacts.metadata else None
                java_stats = get_java_stats_from_neo4j(db, final_project_name, logger, start_time, end_time)
                if db:
                    db.add_project(project_entity)
            else:
                # 배치 모드: 기존 방식으로 Neo4j에 저장
                java_stats = save_java_objects_to_neo4j(
                    db,
                    artifacts,
                    project_entity,
                    clean,
                    logger,
                )

        # 인덱스는 이미 데이터 저장 전에 생성됨

        overall_end_time = datetime.now()
        print_analysis_summary(overall_start_time, overall_end_time, java_stats, db_stats, dry_run, db, project_name)

        result = AnalysisResult(
            success=True,
            java_stats=java_stats,
            db_stats=db_stats,
            message="Analysis completed successfully",
        )
        return {
            "success": True,
            "message": result.message,
            "stats": {
                "java_stats": result.java_stats.dict() if result.java_stats else None,
                "db_stats": result.db_stats.dict() if result.db_stats else None,
            },
        }

    except Exception as exc:  # pylint: disable=broad-except
        logger.error("Analysis error: %s", exc)
        return {"success": False, "error": str(exc)}
    finally:
        if db:
            db.close()


__all__ = ["analyze_project"]

