"""Convenience exports for the parser package."""

from csa.parsers.db.ddl_parser import DDLParser, DDLParseResult
from csa.parsers.sql.parser import SQLParser, SQLAnalysisResult

__all__ = [
    "DDLParser",
    "DDLParseResult",
    "SQLParser",
    "SQLAnalysisResult",
]
