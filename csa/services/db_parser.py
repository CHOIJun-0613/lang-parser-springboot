"""Backward-compatible wrapper for DDL parsing utilities."""

from __future__ import annotations

from typing import Any, Dict, List

from csa.parsers.db.ddl_parser import DDLParser, DDLParseResult


class DBParser:
    """Legacy facade that returns dictionaries for compatibility."""

    def __init__(self) -> None:
        self._parser = DDLParser()

    def parse_ddl_file(self, file_path: str, project_name: str) -> Dict[str, Any]:
        result = self._parser.parse_file(file_path, project_name)
        return self._to_dict(result)

    def parse_ddl_directory(self, directory_path: str, project_name: str) -> List[Dict[str, Any]]:
        results = self._parser.parse_directory(directory_path, project_name)
        return [self._to_dict(res) for res in results]

    def _to_dict(self, result: DDLParseResult) -> Dict[str, Any]:
        return {
            "database": result.database,
            "tables": result.tables,
            "columns": result.columns,
            "indexes": [(index, index.table_name) for index in result.indexes],
            "constraints": [(constraint, constraint.table_name) for constraint in result.constraints],
        }


__all__ = ["DBParser", "DDLParser", "DDLParseResult"]
