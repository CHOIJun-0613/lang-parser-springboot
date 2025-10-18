"""Parse database DDL scripts into graph entity payloads."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from csa.models.graph_entities import Column, Constraint, Database, Index, Table
from csa.parsers.base import file_exists, list_files, read_text, timestamp
from csa.utils.logger import get_logger

_LOGGER = None

def _get_logger():
    """지연 초기화된 로거"""
    global _LOGGER
    if _LOGGER is None:
        _LOGGER = get_logger(__name__)
    return _LOGGER

# 하위 호환성을 위해 LOGGER 별칭 제공
class _LoggerProxy:
    def __getattr__(self, name):
        return getattr(_get_logger(), name)

LOGGER = _LoggerProxy()


@dataclass
class DDLParseResult:
    database: Database
    tables: List[Table]
    columns: List[Column]
    indexes: List[Index]
    constraints: List[Constraint]


class DDLParser:
    """Utility for parsing SQL DDL files and producing graph-entity payloads."""

    def parse_file(self, file_path: str, project_name: str) -> DDLParseResult:
        if not file_exists(file_path):
            raise FileNotFoundError(file_path)

        content = read_text(file_path)

        database = self._build_database(content, file_path, project_name)
        tables_data = self._parse_tables(content)
        indexes_data = self._parse_indexes(content)
        constraints_data = self._parse_constraints(content)

        tables: List[Table] = []
        columns: List[Column] = []
        indexes: List[Index] = []
        constraints: List[Constraint] = []

        stamp = timestamp()

        for table_name, info in tables_data.items():
            table = Table(
                name=table_name,
                schema_name=info.get("schema", "public"),
                comment=info.get("description", ""),
                ai_description="",
                updated_at=stamp,
            )
            tables.append(table)

            for column_info in info.get("columns", []):
                column = Column(
                    name=column_info["name"],
                    data_type=column_info["data_type"],
                    nullable=column_info.get("nullable", True),
                    unique=column_info.get("unique", False),
                    primary_key=column_info.get("primary_key", False),
                    default_value=column_info.get("default_value", ""),
                    constraints=column_info.get("constraints", []),
                    comment=column_info.get("description", ""),
                    ai_description="",
                    updated_at=stamp,
                )
                column.table_name = table_name
                columns.append(column)

        for table_name, table_indexes in indexes_data.items():
            for index_info in table_indexes:
                index = Index(
                    name=index_info["name"],
                    type=index_info.get("type", "B-tree"),
                    columns=index_info.get("columns", []),
                    table_name=table_name,
                    description=index_info.get("description", ""),
                    ai_description="",
                    updated_at=stamp,
                )
                indexes.append(index)

        for table_name, table_constraints in constraints_data.items():
            for constraint_info in table_constraints:
                constraint = Constraint(
                    name=constraint_info["name"],
                    type=constraint_info["type"],
                    definition=constraint_info.get("definition", ""),
                    table_name=table_name,
                    columns=constraint_info.get("columns", []),
                    reference_table=constraint_info.get("reference_table", ""),
                    reference_columns=constraint_info.get("reference_columns", []),
                    description=constraint_info.get("description", ""),
                    ai_description="",
                    updated_at=stamp,
                )
                constraints.append(constraint)

        return DDLParseResult(
            database=database,
            tables=tables,
            columns=columns,
            indexes=indexes,
            constraints=constraints,
        )

    def parse_directory(self, directory_path: str, project_name: str) -> List[DDLParseResult]:
        if not file_exists(directory_path):
            LOGGER.error("Directory %s does not exist", directory_path)
            return []

        results: List[DDLParseResult] = []
        for path in list_files(directory_path, ".sql"):
            filename = path.split("\\")[-1] if "\\" in path else path.split("/")[-1]
            try:
                LOGGER.info("Parsing DDL file: %s", filename)
                results.append(self.parse_file(path, project_name))
            except Exception as exc:  # pylint: disable=broad-except
                LOGGER.error("Failed to parse %s: %s", filename, exc)
        return results

    # -- helpers ---------------------------------------------------------

    def _build_database(self, content: str, file_path: str, project_name: str) -> Database:
        name = self._extract_database_name(content, file_path)
        environment = self._extract_environment(content, file_path)
        return Database(
            name=name,
            version="1.0",
            environment=environment,
            description=f"Database schema for {project_name}",
            ai_description="",
            updated_at=timestamp(),
        )

    def _extract_database_name(self, content: str, file_path: str) -> str:
        match = re.search(r"--\s*Database[:=]\s*(\w+)", content, re.IGNORECASE)
        if match:
            return match.group(1)
        return Path(file_path).stem

    def _extract_environment(self, content: str, file_path: str) -> str:
        match = re.search(r"--\s*Environment[:=]\s*(\w+)", content, re.IGNORECASE)
        if match:
            return match.group(1)
        filename = Path(file_path).name
        if "prod" in filename.lower():
            return "production"
        if "dev" in filename.lower():
            return "development"
        if "test" in filename.lower():
            return "test"
        return "unknown"

    def _parse_tables(self, content: str) -> Dict[str, Dict[str, Any]]:
        tables: Dict[str, Dict[str, Any]] = {}
        table_pattern = r"CREATE\s+TABLE\s+(\w+)\s*\((.*?)\);"
        for match in re.finditer(table_pattern, content, re.DOTALL | re.IGNORECASE):
            table_name = match.group(1)
            table_body = match.group(2)
            tables[table_name] = {
                "schema": "public",
                "columns": self._parse_columns(table_body),
                "constraints": self._parse_inline_constraints(table_body, table_name),
            }
        return tables

    def _parse_columns(self, table_body: str) -> List[Dict[str, Any]]:
        columns = []
        column_pattern = r"(\w+)\s+([\w\(\), ]+)(?:\s+CONSTRAINT\s+\w+\s+([\w\s]+))?"
        for match in re.finditer(column_pattern, table_body, re.IGNORECASE):
            column_name = match.group(1)
            data_type = match.group(2).strip()
            constraint_def = match.group(3)
            column_info: Dict[str, Any] = {
                "name": column_name,
                "data_type": data_type,
                "nullable": "NOT NULL" not in data_type.upper(),
                "unique": "UNIQUE" in data_type.upper(),
                "primary_key": "PRIMARY KEY" in data_type.upper(),
                "constraints": [],
            }
            if constraint_def:
                column_info["constraints"].append(constraint_def.strip())
            columns.append(column_info)
        return columns

    def _parse_inline_constraints(self, table_body: str, table_name: str) -> List[Dict[str, Any]]:
        constraints = []
        constraint_pattern = r"CONSTRAINT\s+(\w+)\s+([^,]+)"
        for match in re.finditer(constraint_pattern, table_body, re.IGNORECASE):
            constraint_name = match.group(1)
            definition = match.group(2).strip()
            constraint_type = self._determine_constraint_type(definition)
            columns, reference_table, reference_columns = self._extract_constraint_details(definition, constraint_type)
            constraints.append(
                {
                    "name": constraint_name,
                    "type": constraint_type,
                    "definition": definition,
                    "columns": columns,
                    "reference_table": reference_table,
                    "reference_columns": reference_columns,
                    "description": f"Constraint {constraint_name} on {table_name}",
                }
            )
        return constraints

    def _parse_indexes(self, content: str) -> Dict[str, List[Dict[str, Any]]]:
        indexes: Dict[str, List[Dict[str, Any]]] = {}
        index_pattern = r"CREATE\s+(UNIQUE\s+)?INDEX\s+(\w+)\s+ON\s+(\w+)\s*\(([^)]+)\)"
        for match in re.finditer(index_pattern, content, re.IGNORECASE):
            unique_keyword, index_name, table_name, columns = match.groups()
            indexes.setdefault(table_name, []).append(
                {
                    "name": index_name,
                    "type": "UNIQUE" if unique_keyword else "B-tree",
                    "columns": [col.strip() for col in columns.split(",")],
                    "description": f"Index {index_name} on {table_name}",
                }
            )
        return indexes

    def _parse_constraints(self, content: str) -> Dict[str, List[Dict[str, Any]]]:
        constraints: Dict[str, List[Dict[str, Any]]] = {}
        alter_pattern = r"ALTER\s+TABLE\s+(\w+)\s+ADD\s+CONSTRAINT\s+(\w+)\s+([^;]+)"
        for match in re.finditer(alter_pattern, content, re.IGNORECASE):
            table_name, name, definition = match.groups()
            constraint_type = self._determine_constraint_type(definition.strip())
            columns, reference_table, reference_columns = self._extract_constraint_details(definition.strip(), constraint_type)
            constraints.setdefault(table_name, []).append(
                {
                    "name": name,
                    "type": constraint_type,
                    "definition": definition.strip(),
                    "columns": columns,
                    "reference_table": reference_table,
                    "reference_columns": reference_columns,
                    "description": f"Constraint {name} on {table_name}",
                }
            )

        table_pattern = r"CREATE\s+TABLE\s+(\w+)\s*\((.*?)\);"
        for match in re.finditer(table_pattern, content, re.DOTALL | re.IGNORECASE):
            table_name = match.group(1)
            table_body = match.group(2)
            inline_constraints = self._parse_inline_constraints(table_body, table_name)
            if inline_constraints:
                constraints.setdefault(table_name, []).extend(inline_constraints)
        return constraints

    def _determine_constraint_type(self, definition: str) -> str:
        definition_upper = definition.upper()
        if "PRIMARY KEY" in definition_upper:
            return "PRIMARY KEY"
        if "FOREIGN KEY" in definition_upper:
            return "FOREIGN KEY"
        if "UNIQUE" in definition_upper:
            return "UNIQUE"
        if "CHECK" in definition_upper:
            return "CHECK"
        if "DEFAULT" in definition_upper:
            return "DEFAULT"
        return "CONSTRAINT"

    def _extract_constraint_details(self, definition: str, constraint_type: str) -> tuple[list[str], str, list[str]]:
        columns: list[str] = []
        reference_table = ""
        reference_columns: list[str] = []

        foreign_key_match = re.search(
            r"FOREIGN\s+KEY\s*\(([^)]+)\)\s*REFERENCES\s+([^\s(]+)\s*\(([^)]+)\)",
            definition,
            re.IGNORECASE,
        )
        if foreign_key_match:
            columns = [col.strip() for col in foreign_key_match.group(1).split(",") if col.strip()]
            reference_table = foreign_key_match.group(2).strip()
            reference_columns = [col.strip() for col in foreign_key_match.group(3).split(",") if col.strip()]
            return columns, reference_table, reference_columns

        if constraint_type in {"PRIMARY KEY", "UNIQUE"}:
            column_match = re.search(r"\(([^)]+)\)", definition)
            if column_match:
                columns = [col.strip() for col in column_match.group(1).split(",") if col.strip()]

        return columns, reference_table, reference_columns


__all__ = ["DDLParser", "DDLParseResult"]
