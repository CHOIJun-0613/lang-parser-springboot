from __future__ import annotations

from typing import Any, Dict, List, Optional


class ImpactMixin:
    """Provide impact and usage analytics."""

    def analyze_table_impact(self, project_name: Optional[str] = None, table_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyse which classes and methods touch the specified table.
        """
        try:
            with self._open_session() as session:
                impact_query = """
                MATCH (c:Class)-[:HAS_METHOD]->(m:Method)
                MATCH (m)-[:CALLS]->(sql:SqlStatement)
                WHERE sql.tables CONTAINS $table_name OR 
                      ANY(table_info IN sql.tables WHERE table_info.name = $table_name)
                RETURN c.name as class_name,
                       c.package_name as package_name,
                       m.name as method_name,
                       sql.id as sql_id,
                       sql.sql_type as sql_type,
                       sql.complexity_score as complexity_score
                ORDER BY c.name, m.name
                """

                result = session.run(impact_query, project_name=project_name, table_name=table_name)
                impacted_classes: List[Dict[str, Any]] = []
                for record in result:
                    impacted_classes.append(
                        {
                            "class_name": record["class_name"],
                            "package_name": record["package_name"],
                            "method_name": record["method_name"],
                            "sql_id": record["sql_id"],
                            "sql_type": record["sql_type"],
                            "complexity_score": record["complexity_score"],
                        }
                    )

                summary = {
                    "table_name": table_name,
                    "total_impacted_classes": len({entry["class_name"] for entry in impacted_classes}),
                    "total_impacted_methods": len({f"{entry['class_name']}.{entry['method_name']}" for entry in impacted_classes}),
                    "total_sql_statements": len({entry["sql_id"] for entry in impacted_classes if entry["sql_id"]}),
                    "crud_operations": list({entry["sql_type"] for entry in impacted_classes if entry["sql_type"]}),
                    "high_complexity_sql": [
                        entry for entry in impacted_classes if entry["complexity_score"] and entry["complexity_score"] > 7
                    ],
                }

                return {
                    "table_name": table_name,
                    "impacted_classes": impacted_classes,
                    "summary": summary,
                }
        except Exception as exc:  # pylint: disable=broad-except
            self.logger.error(f"Table impact analysis error: {exc}")
            return {"error": str(exc)}

    def get_database_usage_statistics(self, project_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Gather aggregate statistics about SQL usage, table access, and complexity.
        """
        try:
            with self._open_session() as session:
                sql_stats_query = """
                MATCH (sql:SqlStatement)
                RETURN 
                    count(sql) as total_sql,
                    sum(CASE WHEN sql.sql_type = 'SELECT' THEN 1 ELSE 0 END) as SELECT,
                    sum(CASE WHEN sql.sql_type = 'INSERT' THEN 1 ELSE 0 END) as INSERT,
                    sum(CASE WHEN sql.sql_type = 'UPDATE' THEN 1 ELSE 0 END) as UPDATE,
                    sum(CASE WHEN sql.sql_type = 'DELETE' THEN 1 ELSE 0 END) as DELETE
                """
                result = session.run(sql_stats_query, project_name=project_name)
                record = result.single()
                sql_stats = record.data() if record else {}

                table_usage_query = """
                MATCH (sql:SqlStatement {project_name: $project_name})
                WHERE sql.tables IS NOT NULL
                UNWIND sql.tables as table_info
                WITH table_info.name as table_name, sql.sql_type as operation
                RETURN 
                    table_name,
                    count(*) as access_count,
                    collect(DISTINCT operation) as operations
                ORDER BY access_count DESC
                """
                result = session.run(table_usage_query, project_name=project_name)
                table_usage = [row.data() for row in result]

                complexity_query = """
                MATCH (sql:SqlStatement {project_name: $project_name})
                WHERE sql.complexity_score IS NOT NULL
                WITH sql.complexity_score as score,
                     CASE 
                         WHEN sql.complexity_score <= 3 THEN 'simple'
                         WHEN sql.complexity_score <= 7 THEN 'medium'
                         WHEN sql.complexity_score <= 12 THEN 'complex'
                         ELSE 'very_complex'
                     END as complexity_level
                RETURN 
                    complexity_level,
                    count(*) as count
                """
                result = session.run(complexity_query, project_name=project_name)
                complexity_stats = {row["complexity_level"]: row["count"] for row in result}

                return {
                    "project_name": project_name,
                    "sql_statistics": sql_stats,
                    "table_usage": table_usage,
                    "complexity_statistics": complexity_stats,
                }
        except Exception as exc:  # pylint: disable=broad-except
            self.logger.error(f"Database usage statistics error: {exc}")
            return {"error": str(exc)}
