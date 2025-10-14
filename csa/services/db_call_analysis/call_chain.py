from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Set


class CallChainMixin:
    """Provide call-chain level queries and summaries."""

    def analyze_call_chain(
        self,
        project_name: Optional[str] = None,
        start_class: Optional[str] = None,
        start_method: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Analyze controller → service → repository → SQL call chain."""
        try:
            with self._open_session() as session:
                if start_class and start_method:
                    call_chain = self._get_method_call_chain(session, start_class, start_method)
                elif start_class:
                    call_chain = self._get_class_call_chain(session, start_class)
                else:
                    call_chain = self._get_project_call_chain(session)

                missing_nodes = self._identify_missing_nodes(session, call_chain)

                return {
                    "project_name": project_name,
                    "call_chain": call_chain,
                    "missing_nodes": missing_nodes,
                    "analysis_summary": self._generate_analysis_summary(call_chain, missing_nodes),
                }
        except Exception as exc:  # pylint: disable=broad-except
            self.logger.error(f"Call chain analysis error: {exc}")
            return {"error": str(exc)}

    def _get_method_call_chain(self, session, class_name: str, method_name: str) -> List[Dict[str, Any]]:
        query = """
        MATCH (c:Class {name: $class_name})-[:HAS_METHOD]->(m:Method {name: $method_name})
        OPTIONAL MATCH (m)-[:CALLS*0..5]->(target_method:Method)
        OPTIONAL MATCH (target_method)<-[:HAS_METHOD]-(target_class:Class)
        OPTIONAL MATCH (target_method)-[:CALLS]->(sql:SqlStatement)
        RETURN m.name as source_method,
               c.name as source_class,
               c.package_name as source_package,
               target_method.name as target_method,
               target_class.name as target_class,
               target_class.package_name as target_package,
               sql.id as sql_id,
               sql.sql_type as sql_type,
               sql.tables as sql_tables,
               sql.columns as sql_columns
        ORDER BY source_method, target_class.name, target_method.name
        """

        result = session.run(query, class_name=class_name, method_name=method_name)
        call_chain: List[Dict[str, Any]] = []
        for record in result:
            call_chain.append(
                {
                    "source_method": record["source_method"],
                    "source_class": record["source_class"],
                    "source_package": record["source_package"] or "default",
                    "target_method": record["target_method"],
                    "target_class": record["target_class"],
                    "target_package": record["target_package"] or "default",
                    "sql_id": record["sql_id"],
                    "sql_type": record["sql_type"],
                    "sql_tables": json.loads(record["sql_tables"]) if record["sql_tables"] else [],
                    "sql_columns": json.loads(record["sql_columns"]) if record["sql_columns"] else [],
                }
            )
        return call_chain

    def _get_class_call_chain(self, session, class_name: str) -> List[Dict[str, Any]]:
        query = """
        MATCH (c:Class {name: $class_name})-[:HAS_METHOD]->(m:Method)
        OPTIONAL MATCH (m)-[:CALLS*0..5]->(target_method:Method)
        OPTIONAL MATCH (target_method)<-[:HAS_METHOD]-(target_class:Class)
        OPTIONAL MATCH (target_method)-[:CALLS]->(sql:SqlStatement)
        RETURN m.name as source_method,
               c.name as source_class,
               c.package_name as source_package,
               target_method.name as target_method,
               target_class.name as target_class,
               target_class.package_name as target_package,
               sql.id as sql_id,
               sql.sql_type as sql_type,
               sql.tables as sql_tables,
               sql.columns as sql_columns
        ORDER BY source_method, target_class.name, target_method.name
        """

        result = session.run(query, class_name=class_name)
        call_chain: List[Dict[str, Any]] = []
        for record in result:
            call_chain.append(
                {
                    "source_method": record["source_method"],
                    "source_class": record["source_class"],
                    "source_package": record["source_package"] or "default",
                    "target_method": record["target_method"],
                    "target_class": record["target_class"],
                    "target_package": record["target_package"] or "default",
                    "sql_id": record["sql_id"],
                    "sql_type": record["sql_type"],
                    "sql_tables": json.loads(record["sql_tables"]) if record["sql_tables"] else [],
                    "sql_columns": json.loads(record["sql_columns"]) if record["sql_columns"] else [],
                }
            )
        return call_chain

    def _get_project_call_chain(self, session) -> List[Dict[str, Any]]:
        query = """
        MATCH (c:Class)-[:HAS_METHOD]->(m:Method)
        OPTIONAL MATCH (m)-[:CALLS*0..5]->(target_method:Method)
        OPTIONAL MATCH (target_method)<-[:HAS_METHOD]-(target_class:Class)
        OPTIONAL MATCH (target_method)-[:CALLS]->(sql:SqlStatement)
        RETURN m.name as source_method,
               c.name as source_class,
               c.package_name as source_package,
               target_method.name as target_method,
               target_class.name as target_class,
               target_class.package_name as target_package,
               sql.id as sql_id,
               sql.sql_type as sql_type,
               sql.tables as sql_tables,
               sql.columns as sql_columns
        ORDER BY source_class, source_method, target_class.name, target_method.name
        """

        result = session.run(query)
        call_chain: List[Dict[str, Any]] = []
        for record in result:
            call_chain.append(
                {
                    "source_method": record["source_method"],
                    "source_class": record["source_class"],
                    "source_package": record["source_package"] or "default",
                    "target_method": record["target_method"],
                    "target_class": record["target_class"],
                    "target_package": record["target_package"] or "default",
                    "sql_id": record["sql_id"],
                    "sql_type": record["sql_type"],
                    "sql_tables": json.loads(record["sql_tables"]) if record["sql_tables"] else [],
                    "sql_columns": json.loads(record["sql_columns"]) if record["sql_columns"] else [],
                }
            )
        return call_chain

    def _identify_missing_nodes(self, session, call_chain: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        missing_tables: Set[str] = set()
        missing_columns: Set[str] = set()
        referenced_tables: Set[str] = set()
        referenced_columns: Set[str] = set()

        for call in call_chain:
            if call.get("sql_tables"):
                for table_info in call["sql_tables"]:
                    if isinstance(table_info, dict) and "name" in table_info:
                        referenced_tables.add(table_info["name"])

            if call.get("sql_columns"):
                for column_info in call["sql_columns"]:
                    if isinstance(column_info, dict) and "name" in column_info:
                        referenced_columns.add(column_info["name"])
                        if column_info.get("table"):
                            referenced_tables.add(column_info["table"])

        existing_tables = self._get_existing_tables(session)
        existing_columns = self._get_existing_columns(session)

        for table_name in referenced_tables:
            if table_name not in existing_tables:
                missing_tables.add(table_name)

        for column_name in referenced_columns:
            if column_name not in existing_columns:
                missing_columns.add(column_name)

        return {
            "missing_tables": list(missing_tables),
            "missing_columns": list(missing_columns),
        }

    def _get_existing_tables(self, session) -> Set[str]:
        query = """
        MATCH (t:Table)
        RETURN t.name as table_name
        """
        result = session.run(query)
        return {record["table_name"] for record in result}

    def _get_existing_columns(self, session) -> Set[str]:
        query = """
        MATCH (c:Column)
        RETURN c.name as column_name
        """
        result = session.run(query)
        return {record["column_name"] for record in result}

    def _generate_analysis_summary(
        self,
        call_chain: List[Dict[str, Any]],
        missing_nodes: Dict[str, List[str]],
    ) -> Dict[str, Any]:
        class_stats: Dict[str, Dict[str, int]] = {}
        all_tables: Set[str] = set()
        all_columns: Set[str] = set()

        for call in call_chain:
            source_class = call["source_class"]
            if source_class not in class_stats:
                class_stats[source_class] = {
                    "method_count": 0,
                    "sql_count": 0,
                    "table_count": 0,
                    "column_count": 0,
                }
            if call["source_method"]:
                class_stats[source_class]["method_count"] += 1
            if call["sql_id"]:
                class_stats[source_class]["sql_count"] += 1

            # sql_tables JSON에서 테이블 추출
            if call.get("sql_tables"):
                for table_info in call["sql_tables"]:
                    if isinstance(table_info, dict) and "name" in table_info:
                        all_tables.add(table_info["name"])
                        class_stats[source_class]["table_count"] += 1

            # sql_columns JSON에서 컬럼 추출
            if call.get("sql_columns"):
                for column_info in call["sql_columns"]:
                    if isinstance(column_info, dict) and "name" in column_info:
                        all_columns.add(column_info["name"])
                        class_stats[source_class]["column_count"] += 1

        return {
            "total_calls": len(call_chain),
            "unique_classes": len(class_stats),
            "unique_methods": len({call["source_method"] for call in call_chain if call["source_method"]}),
            "unique_sql_statements": len({call["sql_id"] for call in call_chain if call["sql_id"]}),
            "unique_tables": len(all_tables),
            "unique_columns": len(all_columns),
            "missing_tables_count": len(missing_nodes["missing_tables"]),
            "missing_columns_count": len(missing_nodes["missing_columns"]),
            "class_stats": class_stats,
        }
