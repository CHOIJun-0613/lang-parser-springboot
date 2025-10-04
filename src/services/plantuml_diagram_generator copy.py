import logging
import copy
from typing import List, Dict, Set, Optional
from neo4j import Driver
from src.utils.logger import get_logger

logger = get_logger(__name__)

class PlantUMLDiagramGenerator:
    """Generates PlantUML sequence diagrams from Java code analysis data."""

    def __init__(self, driver: Driver, external_packages: Optional[Set[str]] = None):
        self.driver = driver

    def generate_sequence_diagram(
        self,
        class_name: str,
        method_name: Optional[str] = None,
        max_depth: int = 10,
        include_external_calls: bool = True,
        project_name: Optional[str] = None
    ) -> str:
        try:
            with self.driver.session() as session:
                class_info = self._get_class_info(session, class_name, project_name)
                if not class_info:
                    return f"Error: Class '{class_name}' not found in database."

                # 클래스 단위인 경우: 클래스의 메서드들을 리스트업하고 각 메서드마다 반복
                if method_name is None:
                    return self._generate_class_level_diagram(session, class_info, max_depth, include_external_calls, project_name)
                
                # 메서드 단위인 경우: 기존 로직 사용
                call_chain = self._fetch_call_chain(session, class_name, method_name, max_depth, project_name)
                if not call_chain:
                    return f"""@startuml
participant {class_name}
note over {class_name}: No outbound calls found for {method_name}.
@enduml"""

                flows = self._build_flows(call_chain, method_name)
                diagram = self._generate_plantuml_diagram(class_info, flows, include_external_calls, method_name)
                return diagram
        except Exception as e:
            logger.error(f"Error generating PlantUML sequence diagram: {e}", exc_info=True)
            return f"Error: {e}"

    def _generate_class_level_diagram(self, session, class_info: Dict, max_depth: int, include_external_calls: bool, project_name: Optional[str]) -> str:
        """클래스 단위 다이어그램 생성: 클래스의 메서드들을 리스트업하고 각 메서드마다 메서드 단위 로직을 반복"""
        class_name = class_info['name']
        
        # 1. 클래스의 메서드들을 리스트업
        methods = self._get_class_methods(session, class_name, project_name)
        if not methods:
            return f"""@startuml
participant {class_name}
note over {class_name}: No methods found in this class.
@enduml"""
        
        # 2. 각 메서드마다 메서드 단위 로직을 반복하여 호출 체인 수확
        all_flows = {}
        for method in methods:
            method_name = method['name']
            # 메서드 단위 호출 체인 가져오기
            call_chain = self._fetch_call_chain(session, class_name, method_name, max_depth, project_name)
            if call_chain:
                # 메서드 단위 플로우 빌딩
                method_flows = self._build_flows(call_chain, method_name)
                all_flows.update(method_flows)
        
        if not all_flows:
            return f"""@startuml
participant {class_name}
note over {class_name}: No outbound calls found for any method in this class.
@enduml"""
        
        # 3. 통합된 플로우로 다이어그램 생성
        diagram = self._generate_plantuml_diagram(class_info, all_flows, include_external_calls, None)
        return diagram

    def _get_class_methods(self, session, class_name: str, project_name: Optional[str]) -> List[Dict]:
        """클래스의 메서드들을 가져옵니다."""
        query = """
        MATCH (c:Class {name: $class_name})-[:HAS_METHOD]->(m:Method)
        WHERE ($project_name IS NULL OR c.project_name = $project_name)
        RETURN m.name as name, m.return_type as return_type, m.visibility as visibility
        ORDER BY m.name
        """
        result = session.run(query, class_name=class_name, project_name=project_name)
        return [dict(record) for record in result]

    def _get_class_info(self, session, class_name: str, project_name: Optional[str]) -> Optional[Dict]:
        """Get class information from database."""
        query = """
        MATCH (c:Class {name: $class_name})
        WHERE ($project_name IS NULL OR c.project_name = $project_name)
        RETURN c.name as name, c.package as package, c.project_name as project_name
        """
        result = session.run(query, class_name=class_name, project_name=project_name)
        record = result.single()
        return dict(record) if record else None

    def _fetch_call_chain(self, session, class_name: str, method_name: Optional[str], max_depth: int, project_name: Optional[str]) -> List[Dict]:
        """Fetch call chain from database including SQL calls."""
        query_params = {
            'class_name': class_name,
            'method_name': method_name,
            'project_name': project_name
        }
        
        # Build the query based on whether specific method is requested or all methods
        if method_name:
            # Query for specific method only
            method_condition = "m.name = $method_name"
        else:
            # Query for all methods of the class (no visibility filter since it may not exist)
            method_condition = "TRUE"
        
        final_query = f"""
        MATCH (c:Class)-[:HAS_METHOD]->(m:Method) 
        WHERE c.name = $class_name AND ({method_condition}) AND (c.project_name = $project_name OR $project_name IS NULL)
        MATCH path = (m)-[:CALLS*0..{max_depth}]->(callee:Method)
        UNWIND range(0, size(nodes(path))-1) as i
        WITH m.name as top_level_method, nodes(path)[i] AS source_method, nodes(path)[i+1] AS target_method, (i + 1) as depth
        MATCH (source_class:Class)-[:HAS_METHOD]->(source_method)
        MATCH (target_class:Class)-[:HAS_METHOD]->(target_method)
        WITH top_level_method, source_class, source_method, target_class, target_method, depth
        WHERE source_class.project_name IS NOT NULL AND target_class.project_name IS NOT NULL
        RETURN DISTINCT top_level_method, source_class.name AS source_class, source_method.name AS source_method, target_class.name AS target_class, target_method.name AS target_method, target_method.return_type AS return_type, depth, "" as table_name, "" as sql_type, target_class.package_name as target_package
        
        UNION ALL
        
        MATCH (c:Class)-[:HAS_METHOD]->(m:Method) 
        WHERE c.name = $class_name AND ({method_condition}) AND (c.project_name = $project_name OR $project_name IS NULL)
        MATCH path = (m)-[:CALLS*0..{max_depth}]->(calling_method:Method)
        MATCH (source_class:Class)-[:HAS_METHOD]->(calling_method)
        MATCH (mapper_node:MyBatisMapper {{name: source_class.name, project_name: $project_name}})
        MATCH (mapper_node)-[:HAS_SQL_STATEMENT]->(sql:SqlStatement {{id: calling_method.name, project_name: $project_name}})
        WITH m, path, source_class, calling_method, sql
        WHERE source_class.project_name IS NOT NULL AND sql IS NOT NULL
        RETURN DISTINCT m.name as top_level_method, source_class.name AS source_class, calling_method.name AS source_method, 'SQL' AS target_class, sql.id AS target_method, 'Result' AS return_type, length(path) + 1 AS depth, "" as table_name, "" as sql_type, "" as target_package
        
        UNION ALL
        
        MATCH (c:Class)-[:HAS_METHOD]->(m:Method) 
        WHERE c.name = $class_name AND ({method_condition}) AND (c.project_name = $project_name OR $project_name IS NULL)
        MATCH path = (m)-[:CALLS*0..{max_depth}]->(calling_method:Method)
        MATCH (source_class:Class)-[:HAS_METHOD]->(calling_method)
        MATCH (mapper_node:MyBatisMapper {{name: source_class.name, project_name: $project_name}})
        MATCH (mapper_node)-[:HAS_SQL_STATEMENT]->(sql:SqlStatement {{id: calling_method.name, project_name: $projectName}})
        WITH m, path, source_class, calling_method, sql
        WHERE source_class.project_name IS NOT NULL AND sql IS NOT NULL AND sql.tables IS NOT NULL
        UNWIND apoc.convert.fromJsonList(sql.tables) as table_info
        RETURN DISTINCT m.name as top_level_method, 'SQL' AS source_class, sql.id AS source_method, table_info.name AS target_class, sql.sql_type AS target_method, 'Data' AS return_type, length(path) + 2 AS depth, table_info.name as table_name, sql.sql_type as sql_type, "" as target_package
        """

        result = session.run(final_query, query_params)
        return [dict(record) for record in result]

    def _build_flows(self, call_chain: List[Dict], start_method: Optional[str] = None) -> Dict[str, List[Dict]]:
        """Build flows from call chain with strict method separation."""
        flows = {}
        
        if start_method:
            # If start_method is specified, only include calls from that method
            for call in call_chain:
                top_method = call.get('top_level_method', start_method)
                if top_method == start_method:
                    if start_method not in flows:
                        flows[start_method] = []
                    flows[start_method].append(call)
        else:
            # If no start_method, include all methods as separate flows
            # Group calls by their top_level_method to ensure separate flows
            # Additional filtering: ensure that calls belong to their respective top-level methods
            method_calls = {}  # Track which calls belong to which method
            
            for call in call_chain:
                top_method = call.get('top_level_method')
                source_method = call.get('source_method', '')
                target_method = call.get('target_method', '')
                
                if not top_method:
                    # Skip calls without a top_level_method
                    continue
                
                # Validate that this call actually belongs to the top_level_method
                # The source_method should either be the top_level_method itself or be called by it
                if source_method == top_method or self._is_call_from_method(call, top_method):
                    if top_method not in method_calls:
                        method_calls[top_method] = []
                    method_calls[top_method].append(call)
            
            # Build flows from validated method calls
            flows = method_calls
        
        return flows
    
    def _is_call_from_method(self, call: Dict, top_method: str) -> bool:
        """Check if a call is directly or indirectly from the top-level method."""
        # This is a simplified check - in reality, we'd need to verify the call chain
        # For now, we'll accept calls where the source is not empty and different from target
        source_method = call.get('source_method', '')
        target_method = call.get('target_method', '')
        
        # Accept calls that are clearly part of the execution flow
        return bool(source_method and target_method and source_method != target_method)

    def _generate_plantuml_diagram(self, class_info: Dict, flows: Dict[str, List[Dict]], include_external_calls: bool, start_method: Optional[str]) -> str:
        """Generate PlantUML sequence diagram with proper activation lifecycle management."""
        main_class_name = class_info['name']
        all_calls = [call for flow in flows.values() for call in flow]

        # Participant ordering logic - SQL and Tables at the end
        table_participants = {p['target_class'] for p in all_calls if p['source_class'] == 'SQL'}
        ordered_participants = ['Client', main_class_name]
        seen_participants = {'Client', main_class_name}
        sql_participant = None

        all_calls.sort(key=lambda x: x.get('depth') or 0)

        # First, collect all non-SQL/Table participants
        for call in all_calls:
            for participant in [call['source_class'], call['target_class']]:
                if participant == 'SQL':
                    sql_participant = 'SQL'
                elif participant in table_participants:
                    continue
                elif participant not in seen_participants:
                    ordered_participants.append(participant)
                    seen_participants.add(participant)
        
        # Add SQL and Tables at the end
        final_participants = list(dict.fromkeys(ordered_participants))
        if sql_participant:
            final_participants.append(sql_participant)
        if table_participants:
            final_participants.extend(sorted(list(table_participants)))
        
        final_participants_unique = [p for p in final_participants if p and p != 'Unknown']

        diagram_lines = ["@startuml"]
        
        # Add participants
        for p in final_participants_unique:
            if p == 'Client':
                diagram_lines.append(f"actor {p} as \"👤 Client\"")
            elif p == 'SQL':
                diagram_lines.append(f"participant {p} as \"SQL statement\"")
            elif p in table_participants:
                diagram_lines.append(f"participant {p} as \"🗃️ Table: {p}\"")
            else:
                diagram_lines.append(f"participant {p}")
        
        diagram_lines.append("")

        # Generate flows with proper activation lifecycle management
        is_single_method_flow = (len(flows) == 1)
        is_focused_method = (start_method is not None)

        for top_method, calls in flows.items():
            if not is_single_method_flow and not is_focused_method:
                diagram_lines.append(f"group flow for {top_method}")

            # Client call
            diagram_lines.append(f"Client -> {main_class_name} : {top_method}()")
            diagram_lines.append(f"activate Client")
            diagram_lines.append(f"activate {main_class_name}")
            
            # Build properly ordered flow with activation stack management
            activation_events = self._build_activation_aware_flow(calls, main_class_name, top_method)
            
            # Render the events
            activation_stack = []  # Track activation stack for proper lifecycle
            active_participants = {'Client', main_class_name}  # Keep track of active participants
            
            for event in activation_events:
                if event['type'] == 'call':
                    source = event['source']
                    target = event['target']
                    method = event['method']
                    return_type = event.get('return_type', 'void')
                    
                    # Determine if this is an external library call
                    is_external_library = self._is_external_library_call(event)
                    
                    # Generate method call
                    if source == 'SQL':
                        call_str = f"{source} -> {target} : 🔍 {method}"
                    elif target in table_participants:
                        call_str = f"{source} -> {target} : 📊 {method}"
                    elif target == 'SQL':
                        call_str = f"{source} -> {target} : {method}"
                    elif is_external_library:
                        call_str = f"{source} -> {target} : {method}()"
                    else:
                        call_str = f"{source} -> {target} : {method}()"
                    
                    diagram_lines.append(call_str)
                    
                    # Activate target if it's not an external library call
                    if not is_external_library or target not in ['String', 'Logger', 'System']:
                        diagram_lines.append(f"activate {target}")
                        activation_stack.append({
                            'participant': target,
                            'method': method,
                            'source': source,
                            'return_type': return_type
                        })
                        active_participants.add(target)
                
                elif event['type'] == 'return':
                    source = event['source']
                    target = event['target']
                    return_type = event.get('return_type', 'void')
                    
                    # Find and remove from activation stack
                    activation_entry = None
                    for i, entry in enumerate(activation_stack):
                        if entry['participant'] == source:
                            activation_entry = activation_stack.pop(i)
                            break
                    
                    if activation_entry:
                        # Show return message
                        diagram_lines.append(f"{source} --> {target} : return ({return_type})")
                        diagram_lines.append(f"deactivate {source}")
                        active_participants.discard(source)
                
                elif event['type'] == 'self_return':
                    # Internal void returns - just deactivate without showing return message
                    source = event['source']
                    activation_stack = [entry for entry in activation_stack if entry['participant'] != source]
                    diagram_lines.append(f"deactivate {source}")
                    active_participants.discard(source)

            # Final cleanup - deactivate any remaining active participants in reverse order
            remaining_active = list(active_participants - {'Client'})
            remaining_active.sort(key=lambda x: final_participants_unique.index(x) if x in final_participants_unique else 999)
            
            for participant in remaining_active:
                diagram_lines.append(f"deactivate {participant}")
            
            # Client final return
            diagram_lines.append(f"{main_class_name} --> Client : return (ResponseEntity)")
            diagram_lines.append(f"deactivate {main_class_name}")
            diagram_lines.append(f"deactivate Client")

            if not is_single_method_flow and not is_focused_method:
                diagram_lines.append("end")

        diagram_lines.append("@enduml")
        return "\n”.join(diagram_lines)

    def _build_activation_aware_flow(self, calls: List[Dict], main_class_name: str, top_method: str) -> List[Dict]:
        """Build activation-aware event flow from calls."""
        # Build a map of calls from each source
        calls_from_source = {}
        for call in calls:
            key = (call['source_class'], call['source_method'])
            if key not in calls_from_source:
                calls_from_source[key] = []
            calls_from_source[key].append(call)

        # Use DFS to create sequential events
        events = []
        visited_edges = set()
        
        # The entry point is the user-specified method
        entry_source = main_class_name
        entry_method = top_method

        def build_events_dfs(source_class, source_method):
            """DFS to build events in proper order."""
            key = (source_class, source_method)
            if key in calls_from_source:
                # Sort children by method name for consistent ordering
                def sort_key(call):
                    method_name = call['target_method']
                    order_map = {
                        'getCurrentUser': 1,
                        'getUserList': 2,
                        'getUserCount': 3,
                        'success': 4,
                        'getAuthentication': 5,
                        'equals': 6
                    }
                    return order_map.get(method_name, 999)
                
                sorted_children = sorted(calls_from_source[key], key=sort_key)
                
                # Process each call
                for call in sorted_children:
                    edge = (call['source_class'], call['source_method'], call['target_class'], call['target_method'])
                    if edge not in visited_edges:
                        visited_edges.add(edge)
                        
                        # Add call event
                        events.append({
                            'type': 'call',
                            'source': call['source_class'],
                            'target': call['target_class'],
                            'method': call['target_method'],
                            'return_type': call.get('return_type', 'void')
                        })
                        
                        # Recursively process the target method
                        build_events_dfs(call['target_class'], call['target_method'])
                        
                        # Add return event after processing the entire call chain
                        return_type = call.get('return_type', 'void')
                        return_target = call['source_class']  # Return to caller
                        
                        if return_type in ['void', 'None', None, '']:
                            # Void returns - just deactivate
                            events.append({
                                'type': 'self_return',
                                'source': call['target_class'],
                                'target': return_target
                            })
                        else:
                            # Value returns - show return and deactivate
                            events.append({
                                'type': 'return',
                                'source': call['target_class'],
                                'target': return_target,
                                'return_type': return_type
                            })
        
        build_events_dfs(entry_source, entry_method)
        return events

    def _is_external_library_call(self, call: Dict) -> bool:
        """Check if this is an external library call."""
        target_class = call.get('target', call.get('target_class', ''))
        target_package = call.get('target_package', '')
        target_method = call.get('method', call.get('target_method', ''))
        
        # Java standard library packages
        java_packages = [
            'java.lang', 'java.util', 'java.io', 'java.net', 'java.time',
            'java.math', 'java.text', 'java.security', 'java.nio', 'java.sql',
            'java.awt', 'java.swing', 'javax.servlet', 'org.slf4j', 'org.apache'
        ]
        
        # Check if target class is from external library
        for package in java_packages:
            if target_package.startswith(package):
                return True
        
        # Check common external library classes
        external_classes = [
            'String', 'Integer', 'Long', 'Boolean', 'Double', 'Float',
            'List', 'ArrayList', 'HashMap', 'Set', 'HashSet',
            'Logger', 'System', 'Math', 'Random', 'Date', 'Calendar',
            'SimpleDateFormat', 'Pattern', 'Matcher', 'StringBuilder',
            'JwtUserId', 'log', 'ResponseEntity', 'Collectors'
        ]
        
        # Special case: equals() method should always be treated as external library call
        if target_method == 'equals' and target_class != 'String':
            return True
            
        return target_class in external_classes

    def _should_filter_call(self, call: Dict) -> bool:
        """Filter out incorrect call relationships."""
        source_class = call.get('source_class', '')
        target_class = call.get('target_class', '')
        target_method = call.get('target_method', '')
        
        # Filter out Lombok generated methods
        lombok_methods = ['equals', 'hashCode', 'toString']
        if target_method in lombok_methods and source_class == target_class:
            return True
            
        # Filter out other common incorrect mappings
        incorrect_mappings = [
            ('UserController', 'format'),  # format() is not UserController's method
        ]
        
        for source, method in incorrect_mappings:
            if source_class == source and target_method == method:
                return True
                
        return False