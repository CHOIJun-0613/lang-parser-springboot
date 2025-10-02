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
                                max_depth: int = 10,
                                include_external_calls: bool = True,
                                method_focused: bool = False,
                                project_name: Optional[str] = None,
                                output_path: Optional[str] = None) -> str:
        """
        Generate a Mermaid sequence diagram for a specific class and optionally a method.
        
        Args:
            class_name: Name of the class to analyze
            method_name: Optional specific method to analyze. If None, analyzes all methods
            max_depth: Maximum depth of call chain to follow
            include_external_calls: Whether to include calls to external libraries
            method_focused: If True, shows only direct calls from the specified method
            project_name: Project name for database analysis (optional)
            output_path: Output path for saving the diagram (optional)
            
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
                diagram = self._generate_mermaid_diagram(class_info, call_chain, include_external_calls)
                
                # Save to file if output_path is provided
                if output_path:
                    try:
                        with open(output_path, 'w', encoding='utf-8') as f:
                            f.write(diagram)
                        print(f"Sequence diagram saved to: {output_path}")
                    except Exception as e:
                        print(f"Error saving diagram to file: {e}")
                
                return diagram
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
        """Get call chain for a specific method - includes proper call chain analysis."""
        # First, get direct calls from the method
        direct_calls_query = """
        MATCH (c:Class {name: $class_name})-[:HAS_METHOD]->(m:Method {name: $method_name})
        MATCH (m)-[:CALLS]->(target_method:Method)
        MATCH (target_method)<-[:HAS_METHOD]-(target_class:Class)
        RETURN m.name as source_method,
               c.name as source_class,
               c.package_name as source_package,
               target_method.name as target_method,
               target_class.name as target_class,
               target_class.package_name as target_package,
               target_method.return_type as return_type
        ORDER BY target_class.name, target_method.name
        """
        
        result = session.run(direct_calls_query, 
                           class_name=class_name, 
                           method_name=method_name)
        
        calls = []
        for record in result:
            call = {
                'source_method': record['source_method'],
                'source_class': record['source_class'],
                'source_package': record['source_package'] or 'default',
                'target_method': record['target_method'],
                'target_class': record['target_class'],
                'target_package': record['target_package'] or 'default',
                'return_type': record.get('return_type', 'void'),
                'depth': 1
            }
            calls.append(call)
            
            # For each target method, get its calls (recursive)
            if max_depth > 1:
                recursive_calls = self._get_recursive_calls(session, record['target_class'], record['target_method'], max_depth - 1, 2)
                calls.extend(recursive_calls)
        
        return calls
    
    def _get_recursive_calls(self, session, class_name: str, method_name: str, remaining_depth: int, current_depth: int) -> List[Dict]:
        """Get recursive calls from a method."""
        if remaining_depth <= 0:
            return []
            
        query = """
        MATCH (c:Class {name: $class_name})-[:HAS_METHOD]->(m:Method {name: $method_name})
        MATCH (m)-[:CALLS]->(target_method:Method)
        MATCH (target_method)<-[:HAS_METHOD]-(target_class:Class)
        RETURN m.name as source_method,
               c.name as source_class,
               c.package_name as source_package,
               target_method.name as target_method,
               target_class.name as target_class,
               target_class.package_name as target_package,
               target_method.return_type as return_type
        ORDER BY target_class.name, target_method.name
        """
        
        result = session.run(query, 
                           class_name=class_name, 
                           method_name=method_name)
        
        calls = []
        for record in result:
            call = {
                'source_method': record['source_method'],
                'source_class': record['source_class'],
                'source_package': record['source_package'] or 'default',
                'target_method': record['target_method'],
                'target_class': record['target_class'],
                'target_package': record['target_package'] or 'default',
                'return_type': record.get('return_type', 'void'),
                'depth': current_depth
            }
            calls.append(call)
            
            # Continue recursion if depth allows
            if remaining_depth > 1:
                recursive_calls = self._get_recursive_calls(session, record['target_class'], record['target_method'], remaining_depth - 1, current_depth + 1)
                calls.extend(recursive_calls)
        
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
        """Generate Mermaid sequence diagram from call chain data with proper call order."""
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
            diagram_lines.append(f"    participant {participant}")
        
        diagram_lines.append("")  # Empty line before interactions
        
        # Add interactions with proper call order
        current_method = None
        activated_participants = set()  # Track which participants are currently activated
        
        # Group calls by depth to show proper call hierarchy
        calls_by_depth = {}
        for call in call_chain:
            if not call['target_class'] or not call['target_method']:
                continue
            depth = call.get('depth', 1)
            if depth not in calls_by_depth:
                calls_by_depth[depth] = []
            calls_by_depth[depth].append(call)
        
        # Process calls by depth
        for depth in sorted(calls_by_depth.keys()):
            for call in calls_by_depth[depth]:
                # Add note for method start if it's a new source method
                if call['source_method'] != current_method:
                    if current_method is not None:
                        diagram_lines.append(f"    note over {call['source_class']}: End of {current_method}")
                        # Only deactivate if it was activated
                        if call['source_class'] in activated_participants:
                            diagram_lines.append(f"    deactivate {call['source_class']}")
                            activated_participants.remove(call['source_class'])
                    diagram_lines.append(f"    note over {call['source_class']}: Start of {call['source_method']}")
                    diagram_lines.append(f"    activate {call['source_class']}")
                    activated_participants.add(call['source_class'])
                    current_method = call['source_method']
                
                # Add method call
                diagram_lines.append(f"    {call['source_class']}->>{call['target_class']}: {call['target_method']}()")
                diagram_lines.append(f"    activate {call['target_class']}")
                activated_participants.add(call['target_class'])
                
                # Add return message
                return_type = call.get('return_type', 'void')
                diagram_lines.append(f"    {call['target_class']}-->>{call['source_class']}: return ({return_type})")
                diagram_lines.append(f"    deactivate {call['target_class']}")
                activated_participants.discard(call['target_class'])
        
        # Deactivate remaining active participants
        for participant in activated_participants:
            diagram_lines.append(f"    deactivate {participant}")
        
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
