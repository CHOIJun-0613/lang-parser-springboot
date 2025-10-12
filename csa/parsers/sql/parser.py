"""SQL parsing utilities for analysing statements and extracting metadata."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from csa.parsers.base import collapse_whitespace
from csa.utils.logger import get_logger

LOGGER = get_logger(__name__)


@dataclass
class SQLAnalysisResult:
    sql_type: str
    original_sql: str = ""
    cleaned_sql: str = ""
    tables: List[Dict[str, str]] = field(default_factory=list)
    columns: List[Dict[str, str]] = field(default_factory=list)
    joins: List[Dict[str, str]] = field(default_factory=list)
    where_conditions: List[str] = field(default_factory=list)
    order_by_columns: List[str] = field(default_factory=list)
    group_by_columns: List[str] = field(default_factory=list)
    having_conditions: List[str] = field(default_factory=list)
    subqueries: List[str] = field(default_factory=list)
    parameters: List[Dict[str, str]] = field(default_factory=list)
    complexity_score: int = 0


class SQLParser:
    """Analyse SQL statements and provide structured metadata."""

    def parse_sql_statement(self, sql_content: str, sql_type: str) -> SQLAnalysisResult:
        try:
            cleaned_sql = collapse_whitespace(self._strip_comments(sql_content))
            if not cleaned_sql:
                return SQLAnalysisResult(sql_type=sql_type)

            result = SQLAnalysisResult(
                sql_type=sql_type,
                original_sql=sql_content,
                cleaned_sql=cleaned_sql,
            )

            sql_type_upper = sql_type.upper()
            if sql_type_upper == "SELECT":
                self._analyse_select_sql(result)
            elif sql_type_upper == "INSERT":
                self._analyse_insert_sql(result)
            elif sql_type_upper == "UPDATE":
                self._analyse_update_sql(result)
            elif sql_type_upper == "DELETE":
                self._analyse_delete_sql(result)

            result.complexity_score = self._calculate_complexity_score(result)
            return result
        except Exception as exc:  # pylint: disable=broad-except
            LOGGER.error("Failed to parse SQL statement: %s", exc)
            return SQLAnalysisResult(sql_type=sql_type)

    def extract_table_column_mapping(self, sql_analysis: SQLAnalysisResult) -> Dict[str, List[str]]:
        mapping: Dict[str, List[str]] = {tbl["name"]: [] for tbl in sql_analysis.tables}
        for column in sql_analysis.columns:
            table = column.get("table")
            name = column.get("name")
            if not name:
                continue
            if table and table in mapping:
                mapping[table].append(name)
            elif not table:
                for tbl in mapping:
                    if name not in mapping[tbl]:
                        mapping[tbl].append(name)
        return mapping

    def analyse_sql_complexity(self, sql_analysis: SQLAnalysisResult) -> Dict[str, Any]:
        level = "simple"
        score = sql_analysis.complexity_score
        if score <= 3:
            level = "simple"
        elif score <= 7:
            level = "medium"
        elif score <= 12:
            level = "complex"
        else:
            level = "very_complex"

        characteristics: List[str] = []
        if len(sql_analysis.joins) > 3:
            characteristics.append("multiple_joins")
        if sql_analysis.subqueries:
            characteristics.append("subqueries")
        if len(sql_analysis.where_conditions) > 5:
            characteristics.append("complex_where")
        if sql_analysis.group_by_columns:
            characteristics.append("grouping")
        if len(sql_analysis.order_by_columns) > 3:
            characteristics.append("complex_ordering")

        recommendations: List[str] = []
        if "multiple_joins" in characteristics:
            recommendations.append("인덱스 최적화 검토")
        if "subqueries" in characteristics:
            recommendations.append("JOIN으로 변환 고려")
        if "complex_where" in characteristics:
            recommendations.append("WHERE 조건 단순화 검토")

        return {
            "score": score,
            "level": level,
            "characteristics": characteristics,
            "recommendations": recommendations,
        }

    # -- Internal helpers -------------------------------------------------

    def _strip_comments(self, sql_content: str) -> str:
        sql = re.sub(r"--.*$", "", sql_content, flags=re.MULTILINE)
        sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
        return sql

    def _analyse_select_sql(self, result: SQLAnalysisResult) -> None:
        sql = result.cleaned_sql
        result.tables = self._extract_tables(sql)
        result.columns = self._extract_select_columns(sql)
        result.joins = self._extract_joins(sql)
        result.where_conditions = self._extract_clause(sql, "WHERE")
        result.order_by_columns = self._extract_columns_in_clause(sql, "ORDER BY")
        result.group_by_columns = self._extract_columns_in_clause(sql, "GROUP BY")
        result.having_conditions = self._extract_clause(sql, "HAVING")
        result.subqueries = self._extract_subqueries(sql)
        result.parameters = self._extract_parameters(sql)

    def _analyse_insert_sql(self, result: SQLAnalysisResult) -> None:
        sql = result.cleaned_sql
        table_match = re.search(r"INSERT\s+INTO\s+([\w.]+)", sql, re.IGNORECASE)
        if table_match:
            table_name = table_match.group(1)
            result.tables = [{"name": table_name, "alias": None}]
            columns_match = re.search(r"\((.*?)\)\s*VALUES", sql, re.IGNORECASE)
            if columns_match:
                columns = [col.strip() for col in columns_match.group(1).split(",")]
                result.columns = [{"name": col, "table": table_name} for col in columns]
        result.parameters = self._extract_parameters(sql)

    def _analyse_update_sql(self, result: SQLAnalysisResult) -> None:
        sql = result.cleaned_sql
        table_match = re.search(r"UPDATE\s+([\w.]+)", sql, re.IGNORECASE)
        if table_match:
            table_name = table_match.group(1)
            result.tables = [{"name": table_name, "alias": None}]
            set_clause = re.search(r"SET\s+(.*?)\s+WHERE", sql, re.IGNORECASE)
            if set_clause:
                assignments = set_clause.group(1).split(",")
                columns = [assign.split("=")[0].strip() for assign in assignments if "=" in assign]
                result.columns = [{"name": col, "table": table_name} for col in columns]
        result.where_conditions = self._extract_clause(sql, "WHERE")
        result.parameters = self._extract_parameters(sql)

    def _analyse_delete_sql(self, result: SQLAnalysisResult) -> None:
        sql = result.cleaned_sql
        table_match = re.search(r"DELETE\s+FROM\s+([\w.]+)", sql, re.IGNORECASE)
        if table_match:
            table_name = table_match.group(1)
            result.tables = [{"name": table_name, "alias": None}]
        result.where_conditions = self._extract_clause(sql, "WHERE")
        result.parameters = self._extract_parameters(sql)

    def _extract_tables(self, sql: str) -> List[Dict[str, Optional[str]]]:
        tables: List[Dict[str, Optional[str]]] = []
        remaining = sql.upper()
        from_index = remaining.find(" FROM ")
        if from_index == -1:
            return tables
        after_from = sql[from_index + len(" FROM ") :]
        stop_keywords = [" WHERE ", " ORDER BY ", " GROUP BY ", " HAVING ", " LIMIT ", " OFFSET "]
        stop_positions = [after_from.upper().find(keyword) for keyword in stop_keywords if keyword in after_from.upper()]
        stop_position = min([pos for pos in stop_positions if pos >= 0], default=len(after_from))
        table_section = after_from[:stop_position]
        parts = [part.strip() for part in table_section.split(",")]
        for part in parts:
            if not part:
                continue
            match = re.match(r"([\w.]+)(?:\s+AS\s+|\s+)(\w+)?", part, re.IGNORECASE)
            if match:
                tables.append({"name": match.group(1), "alias": match.group(2)})
        return tables

    def _extract_select_columns(self, sql: str) -> List[Dict[str, Optional[str]]]:
        columns: List[Dict[str, Optional[str]]] = []
        select_match = re.search(r"SELECT\s+(.*?)\s+FROM", sql, re.IGNORECASE | re.DOTALL)
        if not select_match:
            return columns
        column_section = select_match.group(1)
        column_parts = [part.strip() for part in column_section.split(",")]
        for part in column_parts:
            if not part:
                continue
            alias_match = re.match(r"(.*?)(?:\s+AS\s+|\s+)(\w+)$", part, re.IGNORECASE)
            column_alias = alias_match.group(2) if alias_match else None
            expression = alias_match.group(1) if alias_match else part
            table_name = None
            column_name = expression
            if "." in expression:
                table_name, column_name = expression.split(".", 1)
            columns.append({"name": column_name.strip(), "table": table_name})
        return columns

    def _extract_joins(self, sql: str) -> List[Dict[str, str]]:
        join_pattern = r"(LEFT|RIGHT|INNER|OUTER|FULL)?\s*JOIN\s+([\w.]+)(?:\s+AS\s+|\s+)(\w+)?\s+ON\s+([^=]+=[^=]+)"
        matches = re.finditer(join_pattern, sql, re.IGNORECASE)
        joins: List[Dict[str, str]] = []
        for match in matches:
            join_type = match.group(1) or "JOIN"
            table_name = match.group(2)
            alias = match.group(3)
            condition = match.group(4)
            joins.append({"type": join_type.strip().upper(), "table": table_name, "alias": alias, "condition": condition.strip()})
        return joins

    def _extract_clause(self, sql: str, keyword: str) -> List[str]:
        pattern = rf"{keyword}\s+(.*?)(?:\s+GROUP BY|\s+ORDER BY|\s+HAVING|\s+LIMIT|\s+OFFSET|$)"
        match = re.search(pattern, sql, re.IGNORECASE | re.DOTALL)
        if not match:
            return []
        clause = match.group(1).strip()
        return [clause] if clause else []

    def _extract_columns_in_clause(self, sql: str, keyword: str) -> List[str]:
        parts = self._extract_clause(sql, keyword)
        if not parts:
            return []
        section = parts[0]
        return [item.strip() for item in section.split(",") if item.strip()]

    def _extract_subqueries(self, sql: str) -> List[str]:
        subquery_pattern = r"\((\s*SELECT .*?)\)"
        return [match.group(1).strip() for match in re.finditer(subquery_pattern, sql, re.IGNORECASE | re.DOTALL)]

    def _extract_parameters(self, sql: str) -> List[Dict[str, str]]:
        parameters: List[Dict[str, str]] = []
        if "?" in sql:
            parameters.append({"type": "positional", "count": sql.count("?")})
        for param in re.findall(r"#\{([^}]+)\}", sql):
            parameters.append({"type": "mybatis", "name": param})
        for param in re.findall(r":(\w+)", sql):
            parameters.append({"type": "named", "name": param})
        return parameters

    def _calculate_complexity_score(self, result: SQLAnalysisResult) -> int:
        score = 1
        score += len(result.tables)
        score += len(result.joins)
        score += len(result.subqueries)
        score += len(result.where_conditions)
        score += len(result.group_by_columns)
        score += len(result.order_by_columns)
        score += len(result.having_conditions)
        return score


__all__ = ["SQLParser", "SQLAnalysisResult"]
