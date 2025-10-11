"""
Option validation and project name helpers for the analysis service.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Tuple

from csa.utils.logger import get_logger


def _validate_analyze_options(
    db_object: bool,
    java_object: bool,
    class_name: Optional[str],
    update: bool,
    java_source_folder: Optional[str],
) -> Tuple[bool, bool, bool]:
    """Validate analyze command options and infer defaults when needed."""
    default_to_full = False
    effective_db_object = db_object
    effective_java_object = java_object

    if not db_object and not java_object and not class_name and not update:
        effective_java_object = True
        effective_db_object = True
        default_to_full = True

    if effective_java_object or class_name or update or (not effective_db_object):
        if not java_source_folder:
            raise ValueError(
                "JAVA_SOURCE_FOLDER environment variable or --java-source-folder option is required for Java object analysis.",
            )

    return effective_db_object, effective_java_object, default_to_full


def validate_analyze_options(
    db_object: bool,
    java_object: bool,
    class_name: Optional[str],
    update: bool,
    java_source_folder: Optional[str],
) -> Tuple[bool, bool, bool]:
    """Public wrapper for option validation."""
    return _validate_analyze_options(db_object, java_object, class_name, update, java_source_folder)


def _determine_project_name(
    project_name: Optional[str],
    detected_name: Optional[str],
    logger=None,
) -> str:
    """Determine project name. Priority: CLI argument > detected name."""
    if logger is None:
        logger = get_logger(__name__, command="analyze")
    if project_name:
        logger.info("Using provided project name: %s", project_name)
        return project_name

    if detected_name:
        logger.info("Using detected project name: %s", detected_name)
        return detected_name

    logger.warning("Project name not provided and detection failed. Falling back to default value.")
    return "default_project"


def determine_project_name(project_name: Optional[str], detected_name: Optional[str], logger):
    """Public wrapper kept for backward compatibility."""
    final_name = _determine_project_name(project_name, detected_name, logger)
    logger.debug("Final project name determined as %s", final_name)
    return final_name


def _get_or_determine_project_name(
    project_name: Optional[str],
    detected_project_name: Optional[str],
    java_source_folder: Optional[str],
    logger=None,
) -> str:
    """Resolve the project name using provided, detected, or fallback values."""
    if logger is None:
        logger = get_logger(__name__, command="analyze")
    if project_name:
        logger.info("Using provided project name: %s", project_name)
        return project_name

    if detected_project_name:
        logger.info("Using detected project name: %s", detected_project_name)
        return detected_project_name

    if java_source_folder:
        fallback_name = Path(java_source_folder).resolve().name
    else:
        fallback_name = os.getenv("PROJECT_NAME", "default_project")

    logger.info("Using fallback project name: %s", fallback_name)
    return fallback_name


def get_or_determine_project_name(
    project_name: Optional[str],
    detected_project_name: Optional[str],
    java_source_folder: Optional[str],
    logger,
) -> str:
    """Public wrapper for project name determination."""
    final_name = _get_or_determine_project_name(project_name, detected_project_name, java_source_folder, logger)
    logger.debug("Resolved project name: %s", final_name)
    return final_name


__all__ = [
    "determine_project_name",
    "get_or_determine_project_name",
    "validate_analyze_options",
]
