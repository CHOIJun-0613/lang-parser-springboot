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
    """Retrieve call chain from Neo4j."""
    depth_limit = max(0, int(max_depth))
    query = f"""
    MATCH (source_class:Class {{name: $class_name}})-[:HAS_METHOD]->(source_method:Method)
    WHERE ($method_name IS NULL OR source_method.name = $method_name)
      AND ($project_name IS NULL OR source_class.project_name = $project_name)
    OPTIONAL MATCH path = (source_method)-[:CALLS*0..{depth_limit}]->(target_method:Method)
    WITH source_class, source_method, target_method, path
    OPTIONAL MATCH (target_class:Class)-[:HAS_METHOD]->(target_method)
    OPTIONAL MATCH (target_method)-[:CALLS]->(sql:SqlStatement)
    RETURN
        source_method.name as source_method,
        source_class.name as source_class,
        source_class.package_name as source_package,
        target_method.name as target_method,
        target_class.name as target_class,
        target_class.package_name as target_package,
        sql.id as sql_id,
        sql.sql_type as sql_type,
        sql.tables as sql_tables,
        sql.columns as sql_columns,
        LENGTH(path) as depth
    ORDER BY depth, source_method
    """
    result = session.run(
        query,
        class_name=class_name,
        method_name=method_name,
        project_name=project_name,
    )
    return [dict(record) for record in result]


def build_flows(call_chain: List[Dict], start_method: Optional[str] = None) -> Dict[str, List[Dict]]:
    """Organize call chain data by top-level method."""
    flows: Dict[str, List[Dict]] = {}
    for call in call_chain:
        top_method = call.get("source_method")
        if not top_method:
            continue

        if start_method and top_method != start_method:
            continue

        if should_filter_call(call):
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
