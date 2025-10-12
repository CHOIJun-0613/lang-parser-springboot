"""Backward-compatible wrapper for SQLParser (moved to csa.parsers.sql)."""

from __future__ import annotations

from csa.parsers.sql.parser import SQLParser, SQLAnalysisResult

__all__ = ["SQLParser", "SQLAnalysisResult"]
