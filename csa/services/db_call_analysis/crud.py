from __future__ import annotations

import json
from typing import Any, Dict, List


class CrudMatrixMixin:
    """Build CRUD matrices and supporting summaries."""

    def generate_crud_matrix(self, project_name: str = None) -> Dict[str, Any]:
        """
        Build CRUD matrices based on classes invoking SQL statements.
        """
        try:
            with self._open_session() as session:
                class_crud_query = """
                MATCH (c:Class)-[:HAS_METHOD]->(m:Method)
                MATCH (m)-[:CALLS]->(sql:SqlStatement)
                WHERE sql.tables IS NOT NULL AND sql.tables <> '[]'
                WITH c, m, sql,
                     CASE 
                       WHEN sql.sql_type = 'SELECT' THEN 'R'
                       WHEN sql.sql_type = 'INSERT' THEN 'C'
                       WHEN sql.sql_type = 'UPDATE' THEN 'U'
                       WHEN sql.sql_type = 'DELETE' THEN 'D'
                       ELSE 'O'
                     END as crud_operation
                RETURN c.name as class_name,
                       c.package_name as package_name,
                       sql.tables as tables_json,
                       crud_operation as operation,
                       sql.id as sql_id
                ORDER BY c.name
                """

                result = session.run(class_crud_query)
                raw_data = [record.data() for record in result]

                class_table_relations: List[Dict[str, Any]] = []
                processed_combinations = set()

                for row in raw_data:
                    class_name = row["class_name"]
                    package_name = row["package_name"]
                    operation = row["operation"]
                    sql_id = row["sql_id"]
                    database_name = "default"
                    schema_name = "public"

                    try:
                        tables_json = row["tables_json"]
                        if tables_json and tables_json != "[]":
                            tables = json.loads(tables_json)
                            for table_info in tables:
                                if isinstance(table_info, dict) and "name" in table_info:
                                    table_name = table_info["name"]
                                    combination_key = f"{class_name}_{table_name}"
                                    if combination_key not in processed_combinations:
                                        processed_combinations.add(combination_key)

                                        table_operations = set()
                                        table_sql_statements = set()

                                        for check_row in raw_data:
                                            if (
                                                check_row["class_name"] == class_name
                                                and check_row["tables_json"]
                                                and check_row["tables_json"] != "[]"
                                            ):
                                                try:
                                                    check_tables = json.loads(check_row["tables_json"])
                                                    for check_table in check_tables:
                                                        if (
                                                            isinstance(check_table, dict)
                                                            and "name" in check_table
                                                            and check_table["name"] == table_name
                                                        ):
                                                            table_operations.add(check_row["operation"])
                                                            table_sql_statements.add(check_row["sql_id"])
                                                except (json.JSONDecodeError, TypeError):
                                                    continue

                                        class_table_relations.append(
                                            {
                                                "class_name": class_name,
                                                "package_name": package_name,
                                                "table_name": table_name,
                                                "database_name": database_name,
                                                "schema_name": schema_name,
                                                "operations": list(table_operations),
                                                "sql_statements": list(table_sql_statements),
                                            }
                                        )
                    except (json.JSONDecodeError, TypeError) as exc:
                        self.logger.warning(f"Table JSON parse error: {exc}")
                        continue

                class_matrix: Dict[str, Dict[str, Any]] = {}
                for relation in class_table_relations:
                    class_name = relation["class_name"]
                    if class_name not in class_matrix:
                        class_matrix[class_name] = {
                            "class_name": class_name,
                            "package_name": relation["package_name"],
                            "tables": [],
                            "operations": set(),
                            "sql_statements": set(),
                        }

                    table_entry = {
                        "table_name": relation["table_name"],
                        "database_name": relation["database_name"],
                        "schema_name": relation["schema_name"],
                        "operations": relation["operations"],
                    }

                    if table_entry not in class_matrix[class_name]["tables"]:
                        class_matrix[class_name]["tables"].append(table_entry)

                    class_matrix[class_name]["operations"].update(relation["operations"])
                    if isinstance(relation["sql_statements"], dict):
                        class_matrix[class_name]["sql_statements"].update(relation["sql_statements"])
                    elif isinstance(relation["sql_statements"], (list, set)):
                        class_matrix[class_name]["sql_statements"].update(relation["sql_statements"])

                class_matrix_list = [
                    {
                        "class_name": data["class_name"],
                        "package_name": data["package_name"],
                        "tables": data["tables"],
                        "operations": list(data["operations"]),
                        "sql_statements": list(data["sql_statements"]),
                    }
                    for data in class_matrix.values()
                ]

                table_crud_query = """
                MATCH (sql:SqlStatement)
                WHERE sql.tables IS NOT NULL AND sql.tables <> '[]'
                RETURN sql.tables as tables_json, sql.sql_type as operation
                """

                result = session.run(table_crud_query)
                raw_table_data = [record.data() for record in result]

                table_stats: Dict[str, Dict[str, int]] = {}
                for row in raw_table_data:
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
                    except (json.JSONDecodeError, TypeError) as exc:
                        self.logger.warning(f"Table statistics JSON parse error: {exc}")
                        continue

                table_matrix = []
                for table_name, operations in table_stats.items():
                    operations_list = [{"operation": op, "count": count} for op, count in operations.items()]
                    table_matrix.append({"table_name": table_name, "operations": operations_list})

                return {
                    "project_name": project_name,
                    "class_matrix": class_matrix_list,
                    "table_matrix": table_matrix,
                    "summary": self._generate_crud_summary(class_matrix_list, table_matrix),
                }
        except Exception as exc:  # pylint: disable=broad-except
            self.logger.error(f"CRUD matrix generation error: {exc}")
            return {"error": str(exc)}

    def _generate_crud_summary(self, class_matrix: List[Dict[str, Any]], table_matrix: List[Dict[str, Any]]) -> Dict[str, Any]:
        total_classes = len(class_matrix)
        total_tables = len(table_matrix)
        crud_stats = {"C": 0, "R": 0, "U": 0, "D": 0, "O": 0}
        for class_data in class_matrix:
            for operation in class_data["operations"]:
                if operation in crud_stats:
                    crud_stats[operation] += 1

        return {
            "total_classes": total_classes,
            "total_tables": total_tables,
            "crud_stats": crud_stats,
            "most_active_class": max(class_matrix, key=lambda x: len(x["operations"]))["class_name"]
            if class_matrix
            else None,
            "most_used_table": max(
                table_matrix,
                key=lambda x: sum(op["count"] for op in x["operations"]),
            )["table_name"]
            if table_matrix
            else None,
        }

    def generate_crud_table_matrix(self, project_name: str = None) -> Dict[str, Any]:
        """
        Build a cross-tab view (classes vs tables) for CRUD operations.
        """
        try:
            crud_data = self.generate_crud_matrix(project_name)
            class_matrix = crud_data.get("class_matrix", [])

            if not class_matrix:
                return {
                    "table_matrix": [],
                    "class_names": [],
                    "table_names": [],
                    "summary": {"total_classes": 0, "total_tables": 0},
                }

            all_tables = set()
            for class_data in class_matrix:
                if class_data.get("tables"):
                    for table_info in class_data["tables"]:
                        if isinstance(table_info, dict) and "table_name" in table_info:
                            all_tables.add(table_info["table_name"])

            table_names = sorted(list(all_tables))
            class_names = [class_data["class_name"] for class_data in class_matrix]

            table_matrix = []
            for class_data in class_matrix:
                class_name = class_data["class_name"]
                package_name = class_data.get("package_name", "N/A")
                row: Dict[str, Any] = {"class_name": class_name, "package_name": package_name}

                class_tables: Dict[str, Dict[str, Any]] = {}
                if class_data.get("tables"):
                    for table_info in class_data["tables"]:
                        if isinstance(table_info, dict) and "table_name" in table_info:
                            table_name = table_info["table_name"]
                            class_tables[table_name] = {
                                "operations": table_info.get("operations", []),
                                "schema_name": table_info.get("schema_name", "public"),
                                "database_name": table_info.get("database_name", "default"),
                            }

                for table_name in table_names:
                    if table_name in class_tables:
                        operations = class_tables[table_name]["operations"]
                        operations_str = "/".join(sorted(operations)) if operations else "-"
                        row[table_name] = operations_str
                    else:
                        row[table_name] = "-"

                table_matrix.append(row)

            return {
                "table_matrix": table_matrix,
                "class_names": class_names,
                "table_names": table_names,
                "summary": crud_data.get("summary", {}),
            }
        except Exception as exc:  # pylint: disable=broad-except
            self.logger.error(f"CRUD table matrix generation error: {exc}")
            return {"error": str(exc)}
