"""
Analysis service package exposing high-level helpers for project analysis.
"""

from .handlers import analyze_project
from .options import (
    determine_project_name,
    get_or_determine_project_name,
    validate_analyze_options,
)
from .summary import (
    calculate_java_statistics,
    print_analysis_summary,
)

__all__ = [
    "analyze_project",
    "calculate_java_statistics",
    "determine_project_name",
    "get_or_determine_project_name",
    "print_analysis_summary",
    "validate_analyze_options",
]

