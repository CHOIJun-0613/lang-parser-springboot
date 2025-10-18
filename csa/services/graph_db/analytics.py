from __future__ import annotations

import json
from typing import Any, Dict, List, Optional


class AnalyticsMixin:
    """Provide aggregated analytics queries over the graph."""

    def get_crud_matrix(self, project_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return the class-to-table CRUD matrix."""
        query = """
        MATCH (c:Class)-[:HAS_METHOD]->(m:Method)
        MATCH (m)-[:CALLS]->(s:SqlStatement)
        WHERE s.tables IS NOT NULL AND s.tables <> '[]'
        WITH c, m, s, 
             CASE 
               WHEN s.sql_type = 'SELECT' THEN 'R'
               WHEN s.sql_type = 'INSERT' THEN 'C'
               WHEN s.sql_type = 'UPDATE' THEN 'U'
               WHEN s.sql_type = 'DELETE' THEN 'D'
               ELSE 'O'
             END as crud_operation
        RETURN c.name as class_name,
               c.package_name as package_name,
               m.name as method_name,
               s.tables as tables_json,
               crud_operation as operation,
               s.id as sql_id
        ORDER BY c.name, m.name
        """
        with self._driver.session(database=self._database) as session:
            result = session.run(query)
            raw_data = [record.data() for record in result]
            matrix_rows: List[Dict[str, Any]] = []
            for row in raw_data:
                class_name = row["class_name"]
                package_name = row["package_name"]
                method_name = row["method_name"]
                operation = row["operation"]
                try:
                    tables_json = row["tables_json"]
                    if tables_json and tables_json != "[]":
                        tables = json.loads(tables_json)
                        for table_info in tables:
                            if isinstance(table_info, dict) and "name" in table_info:
                                table_name = table_info["name"]
                                schema_query = """
                                MATCH (t:Table {name: $table_name})
                                RETURN t.schema AS schema
                                """
                                schema_result = session.run(schema_query, table_name=table_name)
                                schema_record = schema_result.single()
                                schema = schema_record["schema"] if schema_record else "unknown"
                                matrix_rows.append(
                                    {
                                        "class_name": class_name,
                                        "method_name": method_name,
                                        "package_name": package_name,
                                        "table_name": table_name,
                                        "schema": schema,
                                        "operation": operation,
                                        "sql_id": row["sql_id"],
                                    }
                                )
                except (json.JSONDecodeError, TypeError):
                    continue
            return matrix_rows

    def get_table_crud_summary(self, project_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return CRUD counts aggregated by table."""
        query = """
        MATCH (c:Class)-[:HAS_METHOD]->(m:Method)
        MATCH (m)-[:CALLS]->(s:SqlStatement)
        WHERE s.tables IS NOT NULL AND s.tables <> '[]'
        WITH c, m, s, 
             CASE 
               WHEN s.sql_type = 'SELECT' THEN 'READ'
               WHEN s.sql_type = 'INSERT' THEN 'CREATE'
               WHEN s.sql_type = 'UPDATE' THEN 'UPDATE'
               WHEN s.sql_type = 'DELETE' THEN 'DELETE'
               ELSE 'OTHER'
             END as operation
        RETURN s.tables as tables_json,
               operation
        """
        with self._driver.session(database=self._database) as session:
            result = session.run(query)
            raw_data = [record.data() for record in result]
            table_stats: Dict[str, Dict[str, int]] = {}
            for row in raw_data:
                try:
                    tables_json = row["tables_json"]
                    operation = row["operation"]
                    if tables_json and tables_json != "[]":
                        tables = json.loads(tables_json)
                        for table_info in tables:
                            if isinstance(table_info, dict) and "name" in table_info:
                                table_name = table_info["name"]
                                if table_name not in table_stats:
                                    table_stats[table_name] = {}
                                if operation not in table_stats[table_name]:
                                    table_stats[table_name][operation] = 0
                                table_stats[table_name][operation] += 1
                except (json.JSONDecodeError, TypeError):
                    continue
            return [
                {
                    "table_name": table_name,
                    "operations": [{"operation": op, "count": count} for op, count in operations.items()],
                }
                for table_name, operations in table_stats.items()
            ]

    def get_sql_statistics(self, project_name: Optional[str] = None) -> Dict[str, Any]:
        """Return statistics for SQL statements."""
        with self._driver.session(database=self._database) as session:
            if project_name:
                query = """
                MATCH (s:SqlStatement {project_name: $project_name})
                RETURN 
                    count(*) as total_sql_count,
                    count(DISTINCT s.mapper_name) as mapper_count,
                    count(DISTINCT s.sql_type) as sql_type_count,
                    collect(DISTINCT s.sql_type) as sql_types,
                    avg(s.complexity_score) as avg_complexity,
                    percentileCont(s.complexity_score, 0.5) as median_complexity,
                    max(s.complexity_score) as max_complexity,
                    min(s.complexity_score) as min_complexity
                """
                result = session.run(query, project_name=project_name)
            else:
                query = """
                MATCH (s:SqlStatement)
                RETURN 
                    count(*) as total_sql_count,
                    count(DISTINCT s.mapper_name) as mapper_count,
                    count(DISTINCT s.sql_type) as sql_type_count,
                    collect(DISTINCT s.sql_type) as sql_types,
                    avg(s.complexity_score) as avg_complexity,
                    percentileCont(s.complexity_score, 0.5) as median_complexity,
                    max(s.complexity_score) as max_complexity,
                    min(s.complexity_score) as min_complexity
                """
                result = session.run(query)
            return result.single()

    def get_table_usage_statistics(self, project_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Analyze table usage patterns."""
        with self._driver.session(database=self._database) as session:
            if project_name:
                query = """
                MATCH (s:SqlStatement)
                WHERE s.project_name = $project_name AND s.tables IS NOT NULL
                UNWIND s.tables as table_info
                WITH table_info.name as table_name, s.sql_type as operation
                RETURN 
                    table_name,
                    count(*) as access_count,
                    collect(DISTINCT operation) as operations
                ORDER BY access_count DESC
                """
                result = session.run(query, project_name=project_name)
            else:
                query = """
                MATCH (s:SqlStatement)
                WHERE s.tables IS NOT NULL
                UNWIND s.tables as table_info
                WITH table_info.name as table_name, s.sql_type as operation
                RETURN 
                    table_name,
                    count(*) as access_count,
                    collect(DISTINCT operation) as operations
                ORDER BY access_count DESC
                """
                result = session.run(query)
            return [record.data() for record in result]

    def get_sql_complexity_statistics(self, project_name: Optional[str] = None) -> Dict[str, int]:
        """Return SQL complexity distribution."""
        with self._driver.session(database=self._database) as session:
            if project_name:
                query = """
                MATCH (s:SqlStatement)
                WHERE s.project_name = $project_name AND s.complexity_score IS NOT NULL
                WITH s.complexity_score as score,
                     CASE 
                         WHEN s.complexity_score <= 3 THEN 'simple'
                         WHEN s.complexity_score <= 7 THEN 'medium'
                         WHEN s.complexity_score <= 12 THEN 'complex'
                         ELSE 'very_complex'
                     END as complexity_level
                RETURN 
                    complexity_level,
                    count(*) as count
                """
                result = session.run(query, project_name=project_name)
            else:
                query = """
                MATCH (s:SqlStatement)
                WHERE s.complexity_score IS NOT NULL
                WITH s.complexity_score as score,
                     CASE 
                         WHEN s.complexity_score <= 3 THEN 'simple'
                         WHEN s.complexity_score <= 7 THEN 'medium'
                         WHEN s.complexity_score <= 12 THEN 'complex'
                         ELSE 'very_complex'
                     END as complexity_level
                RETURN 
                    complexity_level,
                    count(*) as count
                """
                result = session.run(query)
            stats: Dict[str, int] = {}
            for record in result:
                stats[record["complexity_level"]] = record["count"]
            return stats

    def get_mapper_sql_distribution(self, project_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return SQL distribution grouped by mapper."""
        with self._driver.session(database=self._database) as session:
            if project_name:
                query = """
                MATCH (s:SqlStatement)
                WHERE s.project_name = $project_name
                RETURN
                    s.mapper_name as mapper_name,
                    count(*) as sql_count,
                    collect(DISTINCT s.sql_type) as sql_types
                ORDER BY sql_count DESC
                """
                result = session.run(query, project_name=project_name)
            else:
                query = """
                MATCH (s:SqlStatement)
                RETURN
                    s.mapper_name as mapper_name,
                    count(*) as sql_count,
                    collect(DISTINCT s.sql_type) as sql_types
                ORDER BY sql_count DESC
                """
                result = session.run(query)
            return [record.data() for record in result]

    def get_database_statistics(self, project_name: Optional[str] = None) -> Dict[str, Any]:
        """Neo4j 데이터베이스에 실제 저장된 노드와 관계 통계 조회"""
        with self._driver.session(database=self._database) as session:
            params = {"project_name": project_name} if project_name else {}

            # 전체 노드 수 조회
            if project_name:
                total_nodes_query = """
                MATCH (n)
                WHERE n.project_name = $project_name
                RETURN count(n) as count
                """
                total_nodes = session.run(total_nodes_query, params).single()["count"]
            else:
                total_nodes_query = "MATCH (n) RETURN count(n) as count"
                total_nodes = session.run(total_nodes_query).single()["count"]

            # 전체 관계 수 조회
            if project_name:
                total_rels_query = """
                MATCH (n)-[r]->(m)
                WHERE n.project_name = $project_name AND m.project_name = $project_name
                RETURN count(r) as count
                """
                total_rels = session.run(total_rels_query, params).single()["count"]
            else:
                total_rels_query = "MATCH ()-[r]->() RETURN count(r) as count"
                total_rels = session.run(total_rels_query).single()["count"]

            # 라벨별 노드 수 조회
            if project_name:
                node_labels_query = """
                MATCH (n)
                WHERE n.project_name = $project_name
                WITH labels(n) as node_labels
                UNWIND node_labels as label
                RETURN label, count(*) as count
                ORDER BY count DESC
                """
                node_counts_result = session.run(node_labels_query, params)
            else:
                node_labels_query = """
                CALL db.labels() YIELD label
                CALL (label) {
                    WITH label
                    MATCH (n) WHERE label IN labels(n)
                    RETURN count(n) as count
                }
                RETURN label, count
                ORDER BY count DESC
                """
                node_counts_result = session.run(node_labels_query)

            node_counts = {record["label"]: record["count"] for record in node_counts_result}

            # 타입별 관계 수 조회
            if project_name:
                rel_types_query = """
                MATCH (n)-[r]->(m)
                WHERE n.project_name = $project_name AND m.project_name = $project_name
                RETURN type(r) as relationshipType, count(r) as count
                ORDER BY count DESC
                """
                rel_counts_result = session.run(rel_types_query, params)
            else:
                rel_types_query = """
                CALL db.relationshipTypes() YIELD relationshipType
                CALL (relationshipType) {
                    WITH relationshipType
                    MATCH ()-[r]->() WHERE type(r) = relationshipType
                    RETURN count(r) as count
                }
                RETURN relationshipType, count
                ORDER BY count DESC
                """
                rel_counts_result = session.run(rel_types_query)

            rel_counts = {record["relationshipType"]: record["count"] for record in rel_counts_result}

            return {
                "total_nodes": total_nodes,
                "total_relationships": total_rels,
                "node_counts_by_label": node_counts,
                "relationship_counts_by_type": rel_counts,
            }
