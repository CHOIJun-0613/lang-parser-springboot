from __future__ import annotations

from typing import Optional, Set


class DiagramMixin:
    """Render Mermaid diagrams for call chains and CRUD relations."""

    def generate_call_chain_diagram(
        self,
        project_name: Optional[str] = None,
        start_class: Optional[str] = None,
        start_method: Optional[str] = None,
    ) -> str:
        """
        Produce a Mermaid diagram describing the call chain.
        """
        try:
            analysis_result = self.analyze_call_chain(project_name, start_class, start_method)
            if "error" in analysis_result:
                return f"```mermaid\ngraph TD\n    A[Error: {analysis_result['error']}]\n```"

            call_chain = analysis_result.get("call_chain", [])
            missing_nodes = analysis_result.get("missing_nodes", {"missing_tables": [], "missing_columns": []})

            if not call_chain:
                return "```mermaid\ngraph TD\n    A[No call chain found]\n```"

            diagram_lines = ["```mermaid", "graph TD"]
            nodes: Set[str] = set()

            for call in call_chain:
                if call.get("source_class"):
                    nodes.add(call["source_class"])
                if call.get("target_class"):
                    nodes.add(call["target_class"])
                if call.get("table_name"):
                    nodes.add(f"Table_{call['table_name']}")
                if call.get("column_name"):
                    nodes.add(f"Column_{call['column_name']}")

            for missing_table in missing_nodes.get("missing_tables", []):
                nodes.add(f"MissingTable_{missing_table}")
            for missing_column in missing_nodes.get("missing_columns", []):
                nodes.add(f"MissingColumn_{missing_column}")

            for node in sorted(nodes):
                if node.startswith("MissingTable_"):
                    table_name = node.replace("MissingTable_", "")
                    diagram_lines.append(f'    {node}["⚠ Missing Table: {table_name}"]:::missingTable')
                elif node.startswith("MissingColumn_"):
                    column_name = node.replace("MissingColumn_", "")
                    diagram_lines.append(f'    {node}["⚠ Missing Column: {column_name}"]:::missingColumn')
                elif node.startswith("Table_"):
                    table_name = node.replace("Table_", "")
                    diagram_lines.append(f'    {node}["Table {table_name}"]:::table')
                elif node.startswith("Column_"):
                    column_name = node.replace("Column_", "")
                    diagram_lines.append(f'    {node}["Column {column_name}"]:::column')
                else:
                    diagram_lines.append(f'    {node}["Class {node}"]:::class')

            for call in call_chain:
                source_class = call.get("source_class")
                target_class = call.get("target_class")
                table_name = call.get("table_name")
                column_name = call.get("column_name")

                if source_class and target_class:
                    diagram_lines.append(f"    {source_class} --> {target_class}")
                if target_class and table_name:
                    table_node = f"Table_{table_name}"
                    diagram_lines.append(f"    {target_class} --> {table_node}")
                if table_name and column_name:
                    table_node = f"Table_{table_name}"
                    column_node = f"Column_{column_name}"
                    diagram_lines.append(f"    {table_node} --> {column_node}")

            for call in call_chain:
                table_name = call.get("table_name")
                column_name = call.get("column_name")
                target_class = call.get("target_class")

                if table_name and table_name in missing_nodes.get("missing_tables", []):
                    missing_table_node = f"MissingTable_{table_name}"
                    if target_class:
                        diagram_lines.append(f"    {target_class} -.-> {missing_table_node}")

                if column_name and column_name in missing_nodes.get("missing_columns", []):
                    missing_column_node = f"MissingColumn_{column_name}"
                    if table_name:
                        table_node = f"Table_{table_name}"
                        diagram_lines.append(f"    {table_node} -.-> {missing_column_node}")

            diagram_lines.extend(
                [
                    "",
                    "    classDef class fill:#e1f5fe,stroke:#01579b,stroke-width:2px",
                    "    classDef table fill:#f3e5f5,stroke:#4a148c,stroke-width:2px",
                    "    classDef column fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px",
                    "    classDef missingTable fill:#ffebee,stroke:#c62828,stroke-width:2px,stroke-dasharray: 5 5",
                    "    classDef missingColumn fill:#fff3e0,stroke:#ef6c00,stroke-width:2px,stroke-dasharray: 5 5",
                ]
            )
            diagram_lines.append("```")
            return "\n".join(diagram_lines)
        except Exception as exc:  # pylint: disable=broad-except
            self.logger.error(f"Call chain diagram generation error: {exc}")
            return f"```mermaid\ngraph TD\n    A[Error: {str(exc)}]\n```"

    def generate_crud_visualization_diagram(self, project_name: Optional[str] = None) -> str:
        """
        Produce a Mermaid diagram summarising CRUD access between classes and tables.
        """
        try:
            crud_data = self.generate_crud_matrix(project_name)
            class_matrix = crud_data.get("class_matrix", [])

            if not class_matrix:
                return "```mermaid\ngraph TD\n    A[No database calls found]\n```"

            diagram_lines = ["```mermaid", "graph TD"]
            nodes: Set[str] = set()
            class_table_relations = []

            for class_data in class_matrix:
                class_name = class_data["class_name"]
                nodes.add(f"Class_{class_name}")
                if class_data.get("tables"):
                    for table_info in class_data["tables"]:
                        if isinstance(table_info, dict) and "table_name" in table_info:
                            table_name = table_info["table_name"]
                            nodes.add(f"Table_{table_name}")
                            class_table_relations.append(
                                {
                                    "class_name": class_name,
                                    "table_name": table_name,
                                    "operations": table_info.get("operations", []),
                                    "database_name": table_info.get("database_name", "default"),
                                    "schema_name": table_info.get("schema_name", "public"),
                                }
                            )

            for node in sorted(nodes):
                if node.startswith("Class_"):
                    class_name = node.replace("Class_", "")
                    diagram_lines.append(f'    {node}["Class {class_name}"]')
                elif node.startswith("Table_"):
                    table_name = node.replace("Table_", "")
                    diagram_lines.append(f'    {node}["Table {table_name}"]')

            for relation in class_table_relations:
                class_node = f"Class_{relation['class_name']}"
                table_node = f"Table_{relation['table_name']}"
                operations_str = ", ".join(relation["operations"])
                diagram_lines.append(f"    {class_node} -->|{operations_str}| {table_node}")

            diagram_lines.append("```")
            return "\n".join(diagram_lines)
        except Exception as exc:  # pylint: disable=broad-except
            self.logger.error(f"CRUD visualization diagram generation error: {exc}")
            return f"```mermaid\ngraph TD\n    A[Error: {str(exc)}]\n```"
