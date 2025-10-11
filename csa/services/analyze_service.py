"""
Compatibility layer that preserves the original public interface for analysis services.
"""
from __future__ import annotations

from csa.services.analysis.handlers import analyze_project
from csa.services.analysis.options import (
    determine_project_name,
    get_or_determine_project_name,
    validate_analyze_options,
)
from csa.services.analysis.summary import print_analysis_summary

__all__ = [
    "analyze_project",
    "determine_project_name",
    "get_or_determine_project_name",
    "print_analysis_summary",
    "validate_analyze_options",
]

