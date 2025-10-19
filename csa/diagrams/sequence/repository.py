"""Shared database access helpers for sequence diagram generation."""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

from csa.utils.logger import get_logger

LOGGER = get_logger(__name__)


def get_class_info(session, class_name: str, project_name: Optional[str]) -> Optional[Dict]:
    """Fetch basic class information."""
    query = """
    MATCH (c:Class {name: $class_name})
    WHERE ($project_name IS NULL OR c.project_name = $project_name)
    RETURN c.name as name, c.package_name as package_name, c.project_name as project_name
    """
    result = session.run(query, class_name=class_name, project_name=project_name)
    record = result.single()
    return dict(record) if record else None


def get_class_methods(session, class_name: str, project_name: Optional[str]) -> List[Dict]:
    """Return method metadata for the given class."""
    query = """
    MATCH (c:Class {name: $class_name})-[:HAS_METHOD]->(m:Method)
    WHERE ($project_name IS NULL OR c.project_name = $project_name)
    RETURN m.name as name,
           m.return_type as return_type,
           m.description as description,
           m.ai_description as ai_description,
           m.logical_name as logical_name
    ORDER BY m.name
    """
    result = session.run(query, class_name=class_name, project_name=project_name)
    return [dict(record) for record in result]


def get_method_return_type(
    session,
    class_name: str,
    method_name: str,
    project_name: Optional[str],
) -> Optional[str]:
    """Return the declared return type for the given method."""
    query = """
    MATCH (c:Class {name: $class_name})-[:HAS_METHOD]->(m:Method {name: $method_name})
    WHERE ($project_name IS NULL OR c.project_name = $project_name)
    RETURN m.return_type as return_type
    """
    result = session.run(
        query,
        class_name=class_name,
        method_name=method_name,
        project_name=project_name,
    )
    record = result.single()
    return record["return_type"] if record and record["return_type"] else None


def fetch_call_chain(
    session,
    class_name: str,
    method_name: Optional[str],
    max_depth: int,
    project_name: Optional[str],
) -> List[Dict]:
    """Retrieve call chain from Neo4j with ordered method/SQL/table calls."""
    depth_limit = max(0, int(max_depth))
    if depth_limit <= 0:
        return []

    top_method_query = """
    MATCH (c:Class {name: $class_name})
    WHERE ($project_name IS NULL OR c.project_name = $project_name)
    MATCH (c)-[:HAS_METHOD]->(m:Method)
    WHERE ($method_name IS NULL OR m.name = $method_name)
    RETURN m.name AS method_name,
           c.name AS class_name,
           c.package_name AS package_name,
           c.project_name AS project_name
    ORDER BY method_name
    """

    method_call_query = """
    MATCH (source:Method {name: $method_name, class_name: $class_name})-[rel:CALLS]->(target:Method)
    OPTIONAL MATCH (target_class_node:Class)-[:HAS_METHOD]->(target)
    RETURN
        COALESCE(rel.call_order, rel.line_number, 0) AS call_order,
        rel.line_number AS line_number,
        target.name AS target_method,
        COALESCE(target_class_node.name, rel.target_class) AS target_class,
        COALESCE(target_class_node.package_name, rel.target_package) AS target_package,
        target_class_node.project_name AS target_project
    ORDER BY call_order, line_number, target_method
    """

    sql_call_query = """
    MATCH (source:Method {name: $method_name, class_name: $class_name})-[rel:CALLS]->(sql:SqlStatement)
    RETURN
        COALESCE(rel.call_order, rel.line_number, 0) AS call_order,
        rel.line_number AS line_number,
        sql.id AS sql_id,
        sql.logical_name AS sql_logical_name,
        sql.sql_type AS sql_type,
        sql.tables AS sql_tables,
        sql.columns AS sql_columns,
        sql.mapper_name AS mapper_name,
        sql.project_name AS sql_project
    ORDER BY call_order, line_number, sql_id
    """

    fallback_sql_query = """
    MATCH (sql:SqlStatement)
    WHERE sql.id = $sql_id AND sql.mapper_name IN $mapper_names
    RETURN
        0 AS call_order,
        0 AS line_number,
        sql.id AS sql_id,
        sql.logical_name AS sql_logical_name,
        sql.sql_type AS sql_type,
        sql.tables AS sql_tables,
        sql.columns AS sql_columns,
        sql.mapper_name AS mapper_name,
        sql.project_name AS sql_project
    ORDER BY sql.mapper_name
    """

    def _safe_project(value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        lowered = value.strip()
        if not lowered or lowered.lower() == "null":
            return None
        return lowered

    def _should_include_method(target_project: Optional[str]) -> bool:
        project = _safe_project(target_project)
        if project is None:
            return False
        if project_name is None:
            return True
        return project == project_name

    def _sql_tables_or_empty(raw_tables):
        if not raw_tables:
            return []
        if isinstance(raw_tables, list):
            return raw_tables
        return []

    def _extract_tables_from_columns(raw_columns):
        if not raw_columns:
            return []
        tables: List[Dict[str, str]] = []
        seen: set[str] = set()
        if isinstance(raw_columns, list):
            for column in raw_columns:
                if not isinstance(column, dict):
                    continue
                table_name = column.get("table") or column.get("table_name")
                if not table_name or table_name in seen:
                    continue
                seen.add(table_name)
                schema_value = column.get("schema") or column.get("schema_name") or ""
                tables.append({"name": table_name, "schema": schema_value})
        return tables
    table_schema_cache: Dict[str, str] = {}
    events: List[Dict] = []

    top_methods = session.run(
        top_method_query,
        class_name=class_name,
        method_name=method_name,
        project_name=project_name,
    )

    visited_methods: Dict[Tuple[str, str, str], int] = {}
    visited_sql: Dict[Tuple[str, str, str], bool] = {}

    def traverse_method(method_info: Dict[str, str], depth: int, top_method_name: str) -> None:
        if depth >= depth_limit:
            return

        method_params = {
            "method_name": method_info["method_name"],
            "class_name": method_info["class_name"],
        }

        method_records = list(session.run(method_call_query, **method_params))
        for record in method_records:
            target_class = record["target_class"]
            target_method = record["target_method"]
            target_project = _safe_project(record["target_project"])
            if not target_class or not target_method:
                continue
            if not _should_include_method(target_project):
                continue

            call_event = {
                "call_type": "method",
                "top_method": top_method_name,
                "source_class": method_info["class_name"],
                "source_package": method_info["package_name"],
                "source_method": method_info["method_name"],
                "source_project": method_info["project_name"],
                "target_class": target_class,
                "target_package": record["target_package"] or "",
                "target_method": target_method,
                "target_project": target_project,
                "call_order": record["call_order"],
                "line_number": record["line_number"],
                "depth": depth + 1,
            }
            events.append(call_event)

            if depth + 1 < depth_limit:
                visit_key = (top_method_name, target_class, target_method)
                previous_depth = visited_methods.get(visit_key)
                if previous_depth is not None and previous_depth <= depth + 1:
                    continue
                visited_methods[visit_key] = depth + 1
                traverse_method(
                    {
                        "method_name": target_method,
                        "class_name": target_class,
                        "package_name": record["target_package"] or "",
                        "project_name": target_project,
                    },
                    depth + 1,
                    top_method_name,
                )

        sql_records = list(session.run(sql_call_query, **method_params))
        if not sql_records:
            mapper_names: List[str] = []
            class_name_value = method_info.get("class_name") or ""
            if class_name_value:
                mapper_names.append(class_name_value)
                simple_name = class_name_value.split(".")[-1]
                if simple_name not in mapper_names:
                    mapper_names.append(simple_name)
            if mapper_names:
                sql_records = list(
                    session.run(
                        fallback_sql_query,
                        sql_id=method_info["method_name"],
                        mapper_names=mapper_names,
                    )
                )
        if sql_records:
            LOGGER.debug(
                "SQL calls for %s.%s (top: %s): %s",
                method_info["class_name"],
                method_info["method_name"],
                top_method_name,
                [record["sql_id"] for record in sql_records],
            )
        for record in sql_records:
            sql_id = record["sql_id"]
            if not sql_id:
                continue

            sql_event = {
                "call_type": "sql",
                "top_method": top_method_name,
                "source_class": method_info["class_name"],
                "source_package": method_info["package_name"],
                "source_method": method_info["method_name"],
                "source_project": method_info["project_name"],
                "target_class": "SQL",
                "target_method": sql_id,
                "target_package": record["mapper_name"] or "",
                "target_project": _safe_project(record["sql_project"]),
                "sql_type": record["sql_type"],
                "sql_tables": record["sql_tables"],
                "sql_columns": record["sql_columns"],
                "mapper_name": record["mapper_name"],
                "sql_logical_name": record["sql_logical_name"],
                "sql_display": record["mapper_name"] or sql_id,
                "call_order": record["call_order"],
                "line_number": record["line_number"],
                "depth": depth + 1,
            }
            sql_visit_key = (top_method_name, method_info["method_name"], sql_id)
            if not visited_sql.get(sql_visit_key):
                events.append(sql_event)
                visited_sql[sql_visit_key] = True

            tables = _sql_tables_or_empty(record["sql_tables"])
            if not tables:
                tables = _extract_tables_from_columns(record["sql_columns"])
            if tables:
                LOGGER.debug("Tables referenced by SQL %s: %s", sql_id, tables)
            for table_data in tables:
                table_name = table_data.get("name") or table_data.get("table") or table_data.get("table_name")
                if not table_name:
                    continue

                cache_key = f"{table_name.lower()}"
                cached_schema = table_schema_cache.get(cache_key)
                if cached_schema is None:
                    schema_value = table_data.get("schema") or table_data.get("schema_name") or ""
                    graph_schema = get_table_schema(session, table_name, None)
                    cached_schema = graph_schema or schema_value or ""
                    table_schema_cache[cache_key] = cached_schema

                table_event = {
                    "call_type": "table",
                    "top_method": top_method_name,
                    "source_class": "SQL",
                    "source_package": record["mapper_name"] or "",
                    "source_method": sql_id,
                    "source_project": _safe_project(record["sql_project"]),
                    "target_class": table_name,
                    "target_method": table_name,
                    "target_package": cached_schema,
                    "target_project": None,
                    "table_schema": cached_schema,
                    "table_display": f"{cached_schema}.{table_name}" if cached_schema else table_name,
                    "sql_type": record["sql_type"],
                    "call_order": record["call_order"],
                    "line_number": record["line_number"],
                    "depth": depth + 2,
                }
                LOGGER.debug(
                    "Table event registered for SQL %s -> %s (schema=%s)",
                    sql_id,
                    table_name,
                    cached_schema,
                )
                events.append(table_event)

    for top_method in top_methods:
        method_info = {
            "method_name": top_method["method_name"],
            "class_name": top_method["class_name"],
            "package_name": top_method["package_name"] or "",
            "project_name": _safe_project(top_method["project_name"]),
        }
        traverse_method(method_info, depth=0, top_method_name=top_method["method_name"])

    return events


def build_flows(call_chain: List[Dict], start_method: Optional[str] = None) -> Dict[str, List[Dict]]:
    """Organize call chain data by top-level method."""
    flows: Dict[str, List[Dict]] = {}
    for call in call_chain:
        top_method = call.get("top_method") or call.get("source_method")
        if not top_method:
            continue

        if start_method and top_method != start_method:
            continue

        call_type = call.get("call_type", "method")
        if call_type == "method" and should_filter_call(call):
            continue

        flows.setdefault(top_method, []).append(call)
    return flows


def is_call_from_method(call: Dict, top_method: str) -> bool:
    """Check if the call originated from the given method."""
    return call.get("source_method") == top_method


def build_activation_aware_flow(
    calls: Sequence[Dict],
    main_class_name: str,
    top_method: str,
) -> List[Dict]:
    """Transform raw call list into activation-aware flow."""
    activation_stack: List[Tuple[str, str]] = [(main_class_name, top_method)]
    activation_flow: List[Dict] = []

    for call in calls:
        target_class = call.get("target_class")
        target_method = call.get("target_method")
        if not target_class or not target_method:
            continue

        while activation_stack and not is_call_from_method(call, activation_stack[-1][1]):
            ended = activation_stack.pop()
            activation_flow.append(
                {
                    "type": "deactivate",
                    "class": ended[0],
                    "method": ended[1],
                }
            )

        activation_flow.append({"type": "call", "call": call})
        activation_stack.append((target_class, target_method))

    while activation_stack:
        ended = activation_stack.pop()
        activation_flow.append(
            {
                "type": "deactivate",
                "class": ended[0],
                "method": ended[1],
            }
        )

    return activation_flow


def is_external_library_call(call: Dict) -> bool:
    """Determine whether the given call targets an external component."""
    target_package = call.get("target_package") or ""
    return (
        target_package.startswith("java.")
        or target_package.startswith("javax.")
        or target_package.startswith("jakarta.")
        or target_package.startswith("org.springframework")
        or target_package.startswith("org.apache")
    )


def get_table_schema(session, table_name: str, project_name: Optional[str]) -> str:
    """Resolve table schema information.

    Returns:
        Schema string in format "database.schema" if Table node exists.
        Empty string ("") if Table node does not exist.
    """
    query = """
    MATCH (t:Table {name: $table_name})
    WHERE ($project_name IS NULL OR t.project_name = $project_name)
    RETURN t.schema as schema, t.database_name as database_name
    """
    result = session.run(query, table_name=table_name, project_name=project_name)
    record = result.single()
    if not record:
        return ""

    schema = record["schema"] or "public"
    database = record["database_name"] or "default"
    return f"{database}.{schema}"


def should_filter_call(call: Dict) -> bool:
    """Filter out incorrect or noisy call relationships."""
    source_class = call.get("source_class", "")
    target_class = call.get("target_class", "")
    target_method = call.get("target_method", "")

    lombok_methods = {"equals", "hashCode", "toString"}
    if target_method in lombok_methods and source_class == target_class:
        return True

    incorrect_mappings = {
        ("UserController", "format"),
    }
    return (source_class, target_method) in incorrect_mappings


def resolve_project_name(class_info: Dict, fallback: Optional[str]) -> str:
    """Return the most appropriate project name."""
    return class_info.get("project_name") or fallback or "default_project"
