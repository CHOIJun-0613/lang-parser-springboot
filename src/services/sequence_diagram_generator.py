"""
Sequence Diagram Generator for Java Code Analysis

This module provides functionality to generate sequence diagrams based on
method call relationships found in Java code analysis.
"""

from typing import List, Dict, Set, Tuple, Optional
from neo4j import Driver, GraphDatabase
from src.models.graph_entities import Class, Method, MethodCall


class SequenceDiagramGenerator:
    """Generates sequence diagrams from Java code analysis data."""
    
    def __init__(self, driver: Driver):
        """Initialize with Neo4j driver."""
        self.driver = driver
    
    def generate_sequence_diagram(self, 
                                class_name: str, 
                                method_name: Optional[str] = None,
                                max_depth: int = 3,
                                include_external_calls: bool = True,
                                method_focused: bool = False) -> str:
        """
        Generate a Mermaid sequence diagram for a specific class and optionally a method.
        
        Args:
            class_name: Name of the class to analyze
            method_name: Optional specific method to analyze. If None, analyzes all methods
            max_depth: Maximum depth of call chain to follow
            include_external_calls: Whether to include calls to external libraries
            method_focused: If True, shows only direct calls from the specified method
            
        Returns:
            Mermaid sequence diagram as string
        """
        try:
            with self.driver.session() as session:
                # Get class information
                class_info = self._get_class_info(session, class_name)
                if not class_info:
                    return f"Error: Class '{class_name}' not found in database."
                
                # Get method call relationships
                if method_focused and method_name:
                    # Method-focused mode: only direct calls from the specified method
                    call_chain = self._get_method_call_chain(session, class_name, method_name, 1)
                elif method_name:
                    call_chain = self._get_method_call_chain(session, class_name, method_name, max_depth)
                else:
                    call_chain = self._get_class_call_chain(session, class_name, max_depth)
                
                # Generate Mermaid diagram
                return self._generate_mermaid_diagram(class_info, call_chain, include_external_calls)
        except Exception as e:
            return f"Error connecting to database: {str(e)}\n\nPlease ensure Neo4j is running and accessible."
    
    def _get_class_info(self, session, class_name: str) -> Optional[Dict]:
        """Get basic class information from database."""
        query = """
        MATCH (c:Class {name: $class_name})
        OPTIONAL MATCH (pkg:Package)-[:CONTAINS]->(c)
        RETURN c.name as name, 
               c.logical_name as logical_name,
               pkg.name as package_name,
               c.type as type
        """
        
        result = session.run(query, class_name=class_name)
        record = result.single()
        
        if record:
            return {
                'name': record['name'],
                'logical_name': record['logical_name'],
                'package_name': record['package_name'] or 'default',
                'type': record['type']
            }
        return None
    
    def _get_method_call_chain(self, session, class_name: str, method_name: str, max_depth: int) -> List[Dict]:
        """Get call chain for a specific method - only outgoing calls from the class."""
        # Build the relationship pattern based on max_depth
        if max_depth == 1:
            rel_pattern = "CALLS"
        else:
            rel_pattern = f"CALLS*1..{max_depth}"
        
        if max_depth == 1:
            # Single relationship - can access properties directly
            query = f"""
            MATCH (c:Class {{name: $class_name}})-[:HAS_METHOD]->(m:Method {{name: $method_name}})
            MATCH (m)-[r:CALLS]->(target_method:Method)
            MATCH (target_method)<-[:HAS_METHOD]-(target_class:Class)
            WHERE target_class.name <> $class_name
            RETURN m.name as source_method,
                   c.name as source_class,
                   c.package_name as source_package,
                   target_method.name as target_method,
                   target_class.name as target_class,
                   target_class.package_name as target_package,
                   target_method.return_type as return_type,
                   r.call_order as call_order,
                   r.line_number as line_number,
                   1 as depth
            ORDER BY call_order, line_number, target_class.name, target_method.name
            """
        else:
            # Multiple relationships - cannot access properties directly
            query = f"""
            MATCH (c:Class {{name: $class_name}})-[:HAS_METHOD]->(m:Method {{name: $method_name}})
            MATCH (m)-[r:CALLS*1..{max_depth}]->(target_method:Method)
            MATCH (target_method)<-[:HAS_METHOD]-(target_class:Class)
            WHERE target_class.name <> $class_name
            RETURN m.name as source_method,
                   c.name as source_class,
                   c.package_name as source_package,
                   target_method.name as target_method,
                   target_class.name as target_class,
                   target_class.package_name as target_package,
                   0 as call_order,
                   0 as line_number,
                   size(r) as depth
            ORDER BY depth, target_class.name, target_method.name
            """
        
        result = session.run(query, 
                           class_name=class_name, 
                           method_name=method_name)
        
        calls = []
        for record in result:
            calls.append({
                'source_method': record['source_method'],
                'source_class': record['source_class'],
                'source_package': record['source_package'] or 'default',
                'target_method': record['target_method'],
                'target_class': record['target_class'],
                'target_package': record['target_package'] or 'default',
                'call_order': record['call_order'] or 0,
                'line_number': record['line_number'] or 0,
                'return_type': record.get('return_type', 'void'),
                'depth': record['depth']
            })
        
        return calls
    
    def _get_class_call_chain(self, session, class_name: str, max_depth: int) -> List[Dict]:
        """Get call chain for all methods in a class - only outgoing calls from the class."""
        # Build the relationship pattern based on max_depth
        if max_depth == 1:
            rel_pattern = "CALLS"
        else:
            rel_pattern = f"CALLS*1..{max_depth}"
        
        if max_depth == 1:
            # Single relationship - can access properties directly
            query = f"""
            MATCH (c:Class {{name: $class_name}})-[:HAS_METHOD]->(m:Method)
            MATCH (m)-[r:CALLS]->(target_method:Method)
            MATCH (target_method)<-[:HAS_METHOD]-(target_class:Class)
            WHERE target_class.name <> $class_name
            RETURN m.name as source_method,
                   c.name as source_class,
                   c.package_name as source_package,
                   target_method.name as target_method,
                   target_class.name as target_class,
                   target_class.package_name as target_package,
                   target_method.return_type as return_type,
                   r.call_order as call_order,
                   r.line_number as line_number,
                   1 as depth
            ORDER BY source_method, call_order, line_number, target_class.name, target_method.name
            """
        else:
            # Multiple relationships - cannot access properties directly
            query = f"""
            MATCH (c:Class {{name: $class_name}})-[:HAS_METHOD]->(m:Method)
            MATCH (m)-[r:CALLS*1..{max_depth}]->(target_method:Method)
            MATCH (target_method)<-[:HAS_METHOD]-(target_class:Class)
            WHERE target_class.name <> $class_name
            RETURN m.name as source_method,
                   c.name as source_class,
                   c.package_name as source_package,
                   target_method.name as target_method,
                   target_class.name as target_class,
                   target_class.package_name as target_package,
                   0 as call_order,
                   0 as line_number,
                   size(r) as depth
            ORDER BY source_method, depth, target_class.name, target_method.name
            """
        
        result = session.run(query, 
                           class_name=class_name)
        
        calls = []
        for record in result:
            calls.append({
                'source_method': record['source_method'],
                'source_class': record['source_class'],
                'source_package': record['source_package'] or 'default',
                'target_method': record['target_method'],
                'target_class': record['target_class'],
                'target_package': record['target_package'] or 'default',
                'call_order': record['call_order'] or 0,
                'line_number': record['line_number'] or 0,
                'return_type': record.get('return_type', 'void'),
                'depth': record['depth']
            })
        
        return calls
    
    def _generate_mermaid_diagram(self, class_info: Dict, call_chain: List[Dict], include_external_calls: bool) -> str:
        """Generate Mermaid sequence diagram from call chain data."""
        if not call_chain:
            return f"```mermaid\nsequenceDiagram\n    participant {class_info['name']}\n    note over {class_info['name']}: No method calls found\n```"
        
        # Collect all participants
        participants = set()
        participants.add(class_info['name'])
        
        for call in call_chain:
            if call['target_class']:
                participants.add(call['target_class'])
        
        # Filter external calls if needed
        if not include_external_calls:
            call_chain = [call for call in call_chain 
                         if not self._is_external_call(call['target_package'])]
        
        # Generate diagram
        diagram_lines = ["```mermaid", "sequenceDiagram"]
        
        # Add participants with better formatting
        sorted_participants = sorted(participants)
        # Put main class first
        if class_info['name'] in sorted_participants:
            sorted_participants.remove(class_info['name'])
            sorted_participants.insert(0, class_info['name'])
        
        for participant in sorted_participants:
            # Use participant notation for all classes (UML standard)
            diagram_lines.append(f"    participant {participant}")
        
        diagram_lines.append("")  # Empty line before interactions
        
        # Add interactions with UML standard formatting
        current_method = None
        active_methods = {}  # Track active methods for each class
        
        for call in call_chain:
            if not call['target_class'] or not call['target_method']:
                continue
                
            # Add note for method start if it's a new source method
            if call['source_method'] != current_method:
                if current_method is not None:
                    diagram_lines.append(f"    note over {call['source_class']}: End of {current_method}")
                    diagram_lines.append(f"    deactivate {call['source_class']}")
                diagram_lines.append(f"    note over {call['source_class']}: Start of {call['source_method']}")
                diagram_lines.append(f"    activate {call['source_class']}")
                current_method = call['source_method']
                active_methods = {call['source_class']: call['source_method']}
            
            # Add method call with proper arrow types
            if call['depth'] > 1:
                # Asynchronous call (dashed arrow with filled arrowhead)
                diagram_lines.append(f"    {call['source_class']}-->>{call['target_class']}: {call['target_method']}()")
            else:
                # Synchronous call (solid arrow with filled arrowhead)
                diagram_lines.append(f"    {call['source_class']}->>{call['target_class']}: {call['target_method']}()")
            
            # Activate target method (UML standard) - always activate for each call
            diagram_lines.append(f"    activate {call['target_class']}")
            
            # Add return message with dotted arrow and return type (UML standard)
            return_type = call.get('return_type', 'void')
            if call['depth'] > 1:
                diagram_lines.append(f"    {call['target_class']}-->>{call['source_class']}: return ({return_type})")
            else:
                diagram_lines.append(f"    {call['target_class']}-->>{call['source_class']}: return ({return_type})")
            
            # Deactivate target method after return (UML standard)
            diagram_lines.append(f"    deactivate {call['target_class']}")
        
        # Deactivate all active methods
        for class_name in active_methods:
            diagram_lines.append(f"    deactivate {class_name}")
        
        # Add final note
        if current_method:
            diagram_lines.append(f"    note over {class_info['name']}: End of {current_method}")
        
        diagram_lines.append("```")
        
        return "\n".join(diagram_lines)
    
    def _is_external_call(self, package_name: str) -> bool:
        """Check if a package is external (not part of the analyzed project)."""
        external_packages = {
            'java.lang', 'java.util', 'java.io', 'java.net', 'java.math',
            'java.time', 'java.text', 'java.security', 'java.sql',
            'javax.servlet', 'org.springframework', 'org.apache',
            'com.fasterxml.jackson', 'org.slf4j', 'org.apache.logging'
        }
        
        return any(package_name.startswith(ext_pkg) for ext_pkg in external_packages)
    
    def get_available_classes(self) -> List[Dict]:
        """Get list of available classes in the database."""
        try:
            with self.driver.session() as session:
                query = """
                MATCH (c:Class)
                OPTIONAL MATCH (pkg:Package)-[:CONTAINS]->(c)
                RETURN c.name as name, 
                       c.logical_name as logical_name,
                       pkg.name as package_name,
                       c.type as type
                ORDER BY c.name
                """
                
                result = session.run(query)
                classes = []
                
                for record in result:
                    classes.append({
                        'name': record['name'],
                        'logical_name': record['logical_name'],
                        'package_name': record['package_name'] or 'default',
                        'type': record['type']
                    })
                
                return classes
        except Exception as e:
            print(f"Error connecting to database: {str(e)}")
            return []
    
    def get_class_methods(self, class_name: str) -> List[Dict]:
        """Get list of methods for a specific class."""
        try:
            with self.driver.session() as session:
                query = """
                MATCH (c:Class {name: $class_name})-[:HAS_METHOD]->(m:Method)
                RETURN m.name as name,
                       m.return_type as return_type,
                       m.logical_name as logical_name
                ORDER BY m.name
                """
                
                result = session.run(query, class_name=class_name)
                methods = []
                
                for record in result:
                    methods.append({
                        'name': record['name'],
                        'return_type': record['return_type'],
                        'logical_name': record['logical_name']
                    })
                
                return methods
        except Exception as e:
            print(f"Error connecting to database: {str(e)}")
            return []
