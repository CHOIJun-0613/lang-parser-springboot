"""
Sequence Diagram Generator for Java Code Analysis

This module provides functionality to generate sequence diagrams based on
method call relationships found in Java code analysis.
"""

import logging
from typing import List, Dict, Set, Optional
from neo4j import Driver
from src.utils.logger import get_logger

# Configure logger
logger = get_logger(__name__)

# Default list of external packages to be excluded from diagrams
DEFAULT_EXTERNAL_PACKAGES = {
    'java.lang', 'java.util', 'java.io', 'java.net', 'java.math',
    'java.time', 'java.text', 'java.security', 'java.sql',
    'javax.servlet', 'org.springframework', 'org.apache',
    'com.fasterxml.jackson', 'org.slf4j', 'org.apache.logging'
}


class SequenceDiagramGenerator:
    """Generates sequence diagrams from Java code analysis data."""

    def __init__(self, driver: Driver, external_packages: Optional[Set[str]] = None):
        """
        Initialize with Neo4j driver and optional external packages set.
        
        Args:
            driver: The Neo4j driver instance.
            external_packages: A set of package prefixes to consider external. 
                               If None, uses DEFAULT_EXTERNAL_PACKAGES.
        """
        self.driver = driver
        self.external_packages = external_packages or DEFAULT_EXTERNAL_PACKAGES

    def generate_sequence_diagram(self,
                                class_name: str,
                                method_name: Optional[str] = None,
                                max_depth: int = 10,
                                include_external_calls: bool = True,
                                project_name: Optional[str] = None) -> str:
        """
        Generate a Mermaid sequence diagram for a specific class and optionally a method.

        Args:
            class_name: Name of the class to analyze.
            method_name: Optional specific method to analyze. If None, analyzes all public methods.
            max_depth: Maximum depth of call chain to follow.
            include_external_calls: Whether to include calls to external libraries.
            project_name: Project name for database analysis (optional).

        Returns:
            Mermaid sequence diagram as a string.
        """
        try:
            with self.driver.session() as session:
                class_info = self._get_class_info(session, class_name, project_name)
                if not class_info:
                    return f"Error: Class '{class_name}' not found in database."

                call_chain = self._fetch_call_chain(session, class_name, method_name, max_depth, project_name)

                diagram = self._generate_mermaid_diagram(class_info, call_chain, include_external_calls)
                return diagram
        except Exception as e:
            logger.error(f"Error generating sequence diagram: {e}", exc_info=True)
            return f"Error connecting to database or generating diagram: {e}"

    def _get_class_info(self, session, class_name: str, project_name: Optional[str]) -> Optional[Dict]:
        """Get basic class information from the database."""
        query_params = {'class_name': class_name}
        
        where_clauses = ["c.name = $class_name"]
        if project_name:
            where_clauses.append("c.project_name = $project_name")
            query_params['project_name'] = project_name
        
        where_statement = " AND ".join(where_clauses)

        query = f"""
        MATCH (c:Class)
        WHERE {where_statement}
        OPTIONAL MATCH (pkg:Package)-[:CONTAINS]->(c)
        RETURN c.name as name,
               c.logical_name as logical_name,
               pkg.name as package_name,
               c.type as type
        LIMIT 1
        """
        result = session.run(query, query_params)
        record = result.single()
        return dict(record) if record else None

    def _fetch_call_chain(self, session, class_name: str, method_name: Optional[str], max_depth: int, project_name: Optional[str]) -> List[Dict]:
        """Fetch the entire call chain, including SQL and Table interactions, using a single efficient Cypher query."""
        query_params = {
            'class_name': class_name,
        }

        # Build WHERE clauses for filtering
        where_clauses = ["c.name = $class_name"]
        if method_name:
            where_clauses.append("m.name = $method_name")
            query_params['method_name'] = method_name
        if project_name:
            where_clauses.append("c.project_name = $project_name")
            query_params['project_name'] = project_name

        where_statement = " AND ".join(where_clauses)

        # This query combines three different types of relationships into one sequence.
        # 1. Method-to-Method calls
        # 2. Method-to-SqlStatement calls
        # 3. SqlStatement-to-Table interactions
        query = f"""
        // Part 1: Method-to-Method calls
        MATCH (c:Class)-[:HAS_METHOD]->(m:Method)
        WHERE {where_statement}
        MATCH path = (m)-[:CALLS*0..{max_depth}]->(callee:Method)
        UNWIND range(0, size(nodes(path))-1) as i
        WITH nodes(path)[i] AS source_method, nodes(path)[i+1] AS target_method, (i + 1) as depth
        OPTIONAL MATCH (source_class:Class)-[:HAS_METHOD]->(source_method)
        OPTIONAL MATCH (target_class:Class)-[:HAS_METHOD]->(target_method)
        RETURN
            coalesce(source_class.name, 'Unknown') AS source_class,
            source_method.name AS source_method,
            coalesce(target_class.name, 'Unknown') AS target_class,
            target_method.name AS target_method,
            coalesce(target_class.package_name, 'unknown.package') AS target_package,
            target_method.return_type AS return_type,
            depth

        UNION ALL

        // Part 2: Method (in Mapper Class) -> SqlStatement interactions
        MATCH (c:Class)-[:HAS_METHOD]->(m:Method)
        WHERE {where_statement}
        MATCH path = (m)-[:CALLS*0..{max_depth}]->(calling_method:Method)
        
        // Find the Class that contains this calling_method
        MATCH (calling_method_class:Class)-[:HAS_METHOD]->(calling_method)
        
        // Check if this Class is also a MyBatisMapper
        MATCH (mapper_node:MyBatisMapper {{name: calling_method_class.name, project_name: $project_name}})
        MATCH (mapper_node)-[:HAS_SQL_STATEMENT]->(sql:SqlStatement)
        
        WITH calling_method, sql, length(path) as path_depth, calling_method_class
        RETURN
            coalesce(calling_method_class.name, 'Unknown') AS source_class,
            calling_method.name AS source_method,
            'SQL' AS target_class,
            sql.type + ' (' + left(sql.id, 6) + '..)' AS target_method,
            'unknown.package' AS target_package, // SQL is not in a package
            'Result' AS return_type,
            path_depth + 1 AS depth

        UNION ALL

        // Part 3: SqlStatement-to-Table interactions (using embedded tables property)
        MATCH (c:Class)-[:HAS_METHOD]->(m:Method)
        WHERE {where_statement}
        MATCH path = (m)-[:CALLS*0..{max_depth}]->(calling_method:Method)
        
        // Find the Class that contains this calling_method
        MATCH (calling_method_class:Class)-[:HAS_METHOD]->(calling_method)
        
        // Check if this Class is also a MyBatisMapper
        MATCH (mapper_node:MyBatisMapper {{name: calling_method_class.name, project_name: $project_name}})
        MATCH (mapper_node)-[:HAS_SQL_STATEMENT]->(sql:SqlStatement)
        
        // Parse the JSON string in sql.tables before UNWINDing
        WITH sql, apoc.convert.fromJsonList(sql.tables) AS parsed_tables, length(path) as path_depth
        UNWIND parsed_tables AS table_info
        WITH sql, table_info, path_depth
        RETURN
            'SQL' AS source_class,
            sql.type + ' (' + left(sql.id, 6) + '..)' AS source_method,
            table_info.name AS target_class, // Now table_info is a map, so .name is valid
            'access table' AS target_method,
            'unknown.package' AS target_package, // Table is not in a package
            'Data' AS return_type,
            path_depth + 2 AS depth
        """

        result = session.run(query, query_params)
        
        # Sort results by depth to maintain call order
        calls = sorted([dict(record) for record in result], key=lambda x: x.get('depth', 0))
        logger.info(f"Found {len(calls)} total calls (including SQL/Table) during fetch.")
        return calls

    def _generate_mermaid_diagram(self, class_info: Dict, call_chain: List[Dict], include_external_calls: bool) -> str:
        """Generate a Mermaid sequence diagram from call chain data."""
        main_class_name = class_info['name']
        
        if not include_external_calls:
            call_chain = [call for call in call_chain if not self._is_external_call(call.get('target_package'))]

        if not call_chain:
            return f"```mermaid\nsequenceDiagram\n    participant {main_class_name}\n    note over {main_class_name}: No method calls found\n```"

        participants = {main_class_name}
        for call in call_chain:
            participants.add(call['source_class'])
            participants.add(call['target_class'])

        # Sort participants, ensuring the main class is first
        sorted_participants = sorted(list(participants))
        if main_class_name in sorted_participants:
            sorted_participants.remove(main_class_name)
            sorted_participants.insert(0, main_class_name)

        diagram_lines = ["```mermaid", "sequenceDiagram"]
        for p in sorted_participants:
            diagram_lines.append(f"    participant {p}")
        diagram_lines.append("")

        # Filter out duplicate calls and sort them for consistent diagram generation
        unique_calls_list = []
        seen_calls = set()
        for call in call_chain:
            # Create a tuple from relevant call details to identify unique calls
            call_tuple = (call['source_class'], call['source_method'], call['target_class'], call['target_method'], call.get('return_type', 'void'), call['depth'])
            if call_tuple not in seen_calls:
                seen_calls.add(call_tuple)
                unique_calls_list.append(call)
        
        # Re-sort after removing duplicates, maintaining depth order
        unique_calls_list.sort(key=lambda x: x.get('depth', 0))

        for call in unique_calls_list:
            source = call['source_class']
            target = call['target_class']
            method = call['target_method']
            return_type = call.get('return_type', 'void')

            if source and target and method:
                diagram_lines.append(f"    {source}->>{target}: {method}()")
                diagram_lines.append(f"    {target}-->>{source}: return ({return_type})")

        diagram_lines.append("```")
        return "\n".join(diagram_lines)

    def _is_external_call(self, package_name: Optional[str]) -> bool:
        """Check if a package is external based on the configured list."""
        if not package_name:
            return True
        return any(package_name.startswith(ext_pkg) for ext_pkg in self.external_packages)

    def get_available_classes(self, project_name: Optional[str] = None) -> List[Dict]:
        """Get a list of available classes in the database, optionally filtered by project."""
        try:
            with self.driver.session() as session:
                query_params = {}
                project_match = ""
                if project_name:
                    project_match = "WHERE c.project_name = $project_name"
                    query_params['project_name'] = project_name
                
                query = f"""
                MATCH (c:Class) {project_match}
                OPTIONAL MATCH (pkg:Package)-[:CONTAINS]->(c)
                RETURN c.name as name,
                       c.logical_name as logical_name,
                       pkg.name as package_name,
                       c.type as type
                ORDER BY c.name
                """
                result = session.run(query, query_params)
                return [dict(record) for record in result]
        except Exception as e:
            logger.error(f"Error getting available classes: {e}", exc_info=True)
            return []

    def get_class_methods(self, class_name: str, project_name: Optional[str] = None) -> List[Dict]:
        """Get a list of methods for a specific class, optionally filtered by project."""
        try:
            with self.driver.session() as session:
                query_params = {'class_name': class_name}
                
                where_clauses = ["c.name = $class_name"]
                if project_name:
                    where_clauses.append("c.project_name = $project_name")
                    query_params['project_name'] = project_name

                where_statement = " AND ".join(where_clauses)

                query = f"""
                MATCH (c:Class)-[:HAS_METHOD]->(m:Method)
                WHERE {where_statement}
                RETURN m.name as name,
                       m.return_type as return_type,
                       m.logical_name as logical_name
                ORDER BY m.name
                """
                result = session.run(query, query_params)
                return [dict(record) for record in result]
        except Exception as e:
            logger.error(f"Error getting class methods for '{class_name}': {e}", exc_info=True)
            return []