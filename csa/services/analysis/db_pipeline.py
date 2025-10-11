"""
Database parsing pipeline helpers.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from csa.models.analysis import DatabaseAnalysisStats
from csa.services.db_parser import DBParser
from csa.services.graph_db import GraphDB


def analyze_full_project_db(
    db: Optional[GraphDB],
    db_script_folder: Optional[str],
    project_name: str,
    dry_run: bool,
    logger,
) -> Optional[DatabaseAnalysisStats]:
    """Parse database scripts and optionally persist them into Neo4j."""
    if not db_script_folder:
        logger.info("No DB_SCRIPT_FOLDER specified. Skipping database object analysis.")
        return None

    logger.info("Analyzing database objects from: %s", db_script_folder)
    db_parser = DBParser()
    db_start_time = datetime.now()
    all_db_objects = db_parser.parse_ddl_directory(db_script_folder, project_name)

    if not all_db_objects:
        logger.info("No database objects found.")
        return None

    logger.info("Found %s DDL files to process.", len(all_db_objects))

    grouped_objects = {}
    for obj in all_db_objects:
        db_name = obj["database"].name or "default"
        grouped_objects.setdefault(db_name, []).append(obj)

    logger.info("Found %s databases: %s", len(grouped_objects), list(grouped_objects.keys()))

    if dry_run:
        logger.info("Dry run mode - not saving to database.")
        for db_name, objects in grouped_objects.items():
            logger.info("Database '%s': %s objects", db_name, len(objects))
        logger.info("Database object analysis complete (dry run).")
        return None

    stats = DatabaseAnalysisStats(
        ddl_files=len(all_db_objects),
        databases=len(grouped_objects),
    )

    for db_name, objects in grouped_objects.items():
        logger.info("Processing database: %s", db_name)

        for obj in objects:
            db.add_database(obj["database"], project_name)

            for table in obj["tables"]:
                db.add_table(table, db_name, project_name)
                stats.tables += 1

            for column in obj["columns"]:
                db.add_column(column, column.table_name, project_name)
                stats.columns += 1

            for index, table_name in obj["indexes"]:
                db.add_index(index, table_name, project_name)
                stats.indexes += 1

            for constraint, table_name in obj["constraints"]:
                db.add_constraint(constraint, table_name, project_name)
                stats.constraints += 1

    stats.start_time = db_start_time
    stats.end_time = datetime.now()
    logger.info("Database object analysis completed.")
    return stats


__all__ = ["analyze_full_project_db"]

