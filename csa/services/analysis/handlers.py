"""
High-level orchestration for project analysis.
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Dict, Optional

from csa.models.analysis import AnalysisResult, DatabaseAnalysisStats, JavaAnalysisStats
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

    return db


def _resolve_db_script_folder(db_script_folder: Optional[str], logger) -> Optional[str]:
    """Resolve DB script folder from arguments or environment."""
    if db_script_folder:
        return db_script_folder

    env_folder = os.getenv("DB_SCRIPT_FOLDER")
    if env_folder:
        logger.info("Using DB_SCRIPT_FOLDER from environment: %s", env_folder)
    return env_folder


def analyze_project(
    java_source_folder: str,
    project_name: str,
    db_script_folder: Optional[str],
    neo4j_uri: str,
    neo4j_user: str,
    neo4j_password: Optional[str],
    neo4j_database: str,
    clean: bool,
    dry_run: bool,
    concurrent: bool,
    workers: Optional[int],
    java_object: bool,
    db_object: bool,
    all_objects: bool,
    class_name: Optional[str],
    update: bool,
    logger,
) -> Dict[str, object]:
    """Analyze project artifacts and optionally persist them into Neo4j."""
    overall_start_time = datetime.now()
    resolved_db_folder = _resolve_db_script_folder(db_script_folder, logger)
    java_stats: Optional[JavaAnalysisStats] = None
    db_stats: Optional[DatabaseAnalysisStats] = None
    db: Optional[GraphDB] = None

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

        if all_objects or java_object:
            artifacts, final_project_name = analyze_full_project_java(java_source_folder, project_name, logger)
            java_stats = save_java_objects_to_neo4j(
                db,
                artifacts,
                final_project_name,
                clean,
                concurrent,
                workers,
                logger,
            )

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

        overall_end_time = datetime.now()
        print_analysis_summary(overall_start_time, overall_end_time, java_stats, db_stats, dry_run)

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

