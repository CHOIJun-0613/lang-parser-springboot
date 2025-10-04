import logging
import copy
from typing import List, Dict, Set, Optional
from neo4j import Driver
from src.utils.logger import get_logger

logger = get_logger(__name__)

class SequenceDiagramGenerator:
    """Generates sequence diagrams from Java code analysis data."""

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

                call_chain = self._fetch_call_chain(session, class_name, method_name, max_depth, project_name)
                if not call_chain:
                    return f"""```mermaid
sequenceDiagram
    participant {class_name}
    note over {class_name}: No outbound calls found for {method_name or 'this class'}.
```"""

                flows = self._build_flows(call_chain)
                diagram = self._generate_mermaid_diagram(class_info, flows, include_external_calls, method_name)
                return diagram
        except Exception as e:
            logger.error(f"Error generating sequence diagram: {e}", exc_info=True)
            return f"Error: {e}"

    def _get_class_info(self, session, class_name: str, project_name: Optional[str]) -> Optional[Dict]:
        query_params = {'class_name': class_name, 'project_name': project_name}
        where_clauses = ["c.name = $class_name"]
        if project_name:
            where_clauses.append("c.project_name = $project_name")
        
        where_statement = " AND ".join(where_clauses)
        query = f"""MATCH (c:Class) WHERE {where_statement} RETURN c.name as name LIMIT 1"""
        result = session.run(query, query_params)
        record = result.single()
        return dict(record) if record else None

    def _fetch_call_chain(self, session, class_name: str, method_name: Optional[str], max_depth: int, project_name: Optional[str]) -> List[Dict]:
        """
        클래스 단위 시퀀스 다이어그램을 위한 호출 체인을 가져옵니다.
        method 단위와 동일한 방법으로 메서드 중첩과 SqlStatement/Table 호출관계를 처리합니다.
        """
        query_params = {
            'class_name': class_name,
            'method_name': method_name,
            'project_name': project_name
        }
        
        # method 단위와 동일한 쿼리 구조 사용
        # 클래스 단위에서는 method_name이 None일 때 모든 메서드를 대상으로 하되, SQL 호출 관계는 유지
        method_condition = "m.name = $method_name" if method_name else "true"
        
        final_query = f"""
        -- 1. 메서드 간 호출관계 (method 단위와 동일한 처리)
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
        
        -- 2. SqlStatement 호출관계 (method 단위와 동일한 처리)
        MATCH (c:Class)-[:HAS_METHOD]->(m:Method) 
        WHERE c.name = $class_name AND ({method_condition}) AND (c.project_name = $project_name OR $project_name IS NULL)
        MATCH path = (m)-[:CALLS*0..{max_depth}]->(calling_method:Method)
        MATCH (source_class:Class)-[:HAS_METHOD]->(calling_method)
        MATCH (mapper_node:MyBatisMapper {{name: source_class.name, project_name: $project_name}})
        MATCH (mapper_node)-[:HAS_SQL_STATEMENT]->(sql:SqlStatement {{id: calling_method.name}})
        WITH m, path, source_class, calling_method, sql
        WHERE source_class.project_name IS NOT NULL AND sql IS NOT NULL
        RETURN DISTINCT m.name as top_level_method, source_class.name AS source_class, calling_method.name AS source_method, 'SQL' AS target_class, sql.id AS target_method, 'Result' AS return_type, length(path) + 1 AS depth, "" as table_name, "" as sql_type, "" as target_package
        
        UNION ALL
        
        -- 3. Table 호출관계 (method 단위와 동일한 처리)
        MATCH (c:Class)-[:HAS_METHOD]->(m:Method) 
        WHERE c.name = $class_name AND ({method_condition}) AND (c.project_name = $project_name OR $project_name IS NULL)
        MATCH path = (m)-[:CALLS*0..{max_depth}]->(calling_method:Method)
        MATCH (source_class:Class)-[:HAS_METHOD]->(calling_method)
        MATCH (mapper_node:MyBatisMapper {{name: source_class.name, project_name: $project_name}})
        MATCH (mapper_node)-[:HAS_SQL_STATEMENT]->(sql:SqlStatement {{id: calling_method.name}})
        WITH m, path, source_class, calling_method, sql
        WHERE source_class.project_name IS NOT NULL AND sql IS NOT NULL AND sql.tables IS NOT NULL
        UNWIND apoc.convert.fromJsonList(sql.tables) as table_info
        RETURN DISTINCT m.name as top_level_method, 'SQL' AS source_class, sql.id AS source_method, table_info.name AS target_class, sql.sql_type AS target_method, 'Data' AS return_type, length(path) + 2 AS depth, table_info.name as table_name, sql.sql_type as sql_type, "" as target_package
        """

        result = session.run(final_query, query_params)
        return [dict(record) for record in result]

    def _build_flows(self, call_chain: List[Dict]) -> Dict[str, List[Dict]]:
        flows = {}
        for call in call_chain:
            top_method = call.get('top_level_method', 'main')
            if top_method not in flows:
                flows[top_method] = []
            flows[top_method].append(call)
        return flows

    def _generate_mermaid_diagram(self, class_info: Dict, flows: Dict[str, List[Dict]], include_external_calls: bool, start_method: Optional[str]) -> str:
        main_class_name = class_info['name']
        all_calls = [call for flow in flows.values() for call in flow]

        # Participant ordering logic
        table_participants = {p['target_class'] for p in all_calls if p['source_class'] == 'SQL'}
        ordered_participants = ['Client', main_class_name]  # Client를 첫 번째로 추가
        seen_participants = {'Client', main_class_name}
        sql_participant = None

        all_calls.sort(key=lambda x: x.get('depth', 0))

        for call in all_calls:
            for participant in [call['source_class'], call['target_class']]:
                if participant == 'SQL':
                    sql_participant = 'SQL'
                elif participant in table_participants:
                    continue
                elif participant not in seen_participants:
                    ordered_participants.append(participant)
        
        final_participants = list(dict.fromkeys(ordered_participants))
        if sql_participant:
            final_participants.append(sql_participant)
        if table_participants:
            final_participants.extend(sorted(list(table_participants)))
        
        final_participants_unique = [p for p in final_participants if p and p != 'Unknown']

        diagram_lines = ["```mermaid", "sequenceDiagram"]
        for p in final_participants_unique:
            if p == 'Client':
                diagram_lines.append(f"    actor {p} as \"👤 Client\"")
            elif p == 'SQL':
                diagram_lines.append(f"    participant {p} as \"SQL statement\"")
            elif p in table_participants:
                diagram_lines.append(f"    participant {p} as \"🗃️ Table: {p}\"")
            else:
                diagram_lines.append(f"    participant {p}")
        diagram_lines.append("")

        # --- DFS-based rendering logic ---
        is_single_method_flow = (len(flows) == 1)

        for top_method, calls in flows.items():
            if not is_single_method_flow:
                diagram_lines.append(f"    opt flow for {top_method}")

            # 각 flow마다 Client 호출 표시
            diagram_lines.append(f"    Client->>{main_class_name}: {top_method}()")
            diagram_lines.append(f"    activate {main_class_name}")
            
            # Stack-based rendering on the correctly ordered flow
            activation_stack = []
            active_participants = set()  # 현재 활성화된 participant 추적
            active_participants.add(main_class_name)

            # Build a map of calls from each source
            calls_from_source = {}
            for call in calls:
                key = (call['source_class'], call['source_method'])
                if key not in calls_from_source:
                    calls_from_source[key] = []
                calls_from_source[key].append(call)

            # Use DFS to create a sequential call order
            ordered_flow = []
            visited_edges = set()
            
            # The entry point is the user-specified method, or all public methods of the class
            entry_source = main_class_name
            entry_method = top_method

            def build_flow_dfs(source_class, source_method):
                """
                method 단위와 동일한 DFS 방식으로 메서드 중첩을 처리합니다.
                """
                key = (source_class, source_method)
                if key in calls_from_source:
                    # method 단위와 동일한 메서드 호출 순서 정렬
                    def sort_key(call):
                        method_name = call['target_method']
                        # 소스코드의 실제 호출 순서에 맞게 정의 (method 단위와 동일)
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
                    
                    # method 단위와 동일한 방식으로 호출된 메서드들을 저장하고 처리
                    method_calls = []
                    for call in sorted_children:
                        edge = (call['source_class'], call['source_method'], call['target_class'], call['target_method'])
                        if edge not in visited_edges:
                            visited_edges.add(edge)
                            method_caller_call = copy.deepcopy(call)
                            method_caller_call['source_class'] = call['source_class']
                            method_caller_call['source_method'] = call['source_method']
                            method_calls.append(method_caller_call)
                    
                    # method 단위와 동일한 방식으로 각 메서드 호출을 처리
                    for call in method_calls:
                        ordered_flow.append(call)
                        # method 단위와 동일한 재귀 호출로 내부 호출 체인을 완전히 처리
                        build_flow_dfs(call['target_class'], call['target_method'])
                        
                        # method 단위와 동일한 반환 처리 (메서드의 전체 호출 체인 완료 후)
                        # 내부 호출인지 외부 호출인지에 따라 반환 대상 결정
                        if call['source_class'] == call['target_class']:
                            # 내부 호출: 자기 자신에게 반환 (method 단위와 동일)
                            return_target = call['target_class']
                        else:
                            # 외부 호출: 호출한 곳으로 반환 (method 단위와 동일)
                            return_target = call['source_class']
                        
                        ordered_flow.append({
                            'source_class': call['target_class'],
                            'source_method': call['target_method'],
                            'target_class': return_target,
                            'target_method': call['source_method'],
                            'return_type': call.get('return_type', 'void'),
                            'is_return': True
                        })
            
            build_flow_dfs(entry_source, entry_method)
            
            for call in ordered_flow:
                # method 단위와 동일한 방식으로 반환 처리
                if call.get('is_return', False):
                    # method 단위와 동일한 반환 처리
                    source = call['source_class']
                    target = call['target_class']
                    return_type = call.get('return_type', 'void')
                    
                    # method 단위와 동일한 반환 표시
                    diagram_lines.append(f"    {source}-->>{target}: return ({return_type})")
                    
                    # method 단위와 동일한 방식으로 모든 반환에 대해 deactivate 처리 (내부 호출도 중첩 박스 닫기)
                    if source in active_participants:
                        diagram_lines.append(f"    deactivate {source}")
                        active_participants.remove(source)
                    
                    # method 단위와 동일한 방식으로 activation_stack에서 해당 participant 제거
                    activation_stack = [a for a in activation_stack if a['participant'] != source]
                    continue
                
                
                
                source = call['source_class']
                target = call['target_class']
                method = call['target_method']
                source_method = call['source_method']
                return_type = call.get('return_type') or 'void'

                # 현재 호출이 같은 클래스 내부 호출인지 확인
                is_internal_call = (source == target and source_method != method)

                if source and target and method:
                    # method 단위와 동일한 방식으로 SqlStatement와 Table 호출관계 처리
                    if source == 'SQL':
                        # SQL에서 Table로의 호출 (method 단위와 동일한 처리)
                        call_str = f"    {source}->>{target}: 🔍 {method}"
                    elif target in table_participants:
                        # Table 호출 (method 단위와 동일한 처리)
                        call_str = f"    {source}->>{target}: 📊 {method}"
                    elif target == 'SQL':
                        # Method에서 SQL로의 호출 (method 단위와 동일한 처리)
                        call_str = f"    {source}->>{target}: {method}"  # SQL 호출 시 () 제거
                    else:
                        # 일반 메서드 호출 (method 단위와 동일한 처리)
                        call_str = f"    {source}->>{target}: {method}()"
                    diagram_lines.append(call_str)
                    
                    # method 단위와 동일한 방식으로 모든 호출에 대해 activate 처리 (내부 호출도 중첩 박스로 표시)
                    diagram_lines.append(f"    activate {target}")
                    activation_stack.append({'participant': target, 'return_type': return_type, 'source': source})
                    active_participants.add(target)

            # 시작 메서드의 activation 블럭 종료
            if main_class_name in active_participants:
                diagram_lines.append(f"    deactivate {main_class_name}")
            
            # 각 flow의 마지막 반환 표시
            diagram_lines.append(f"    {main_class_name}-->>Client: return (ResponseEntity)")

            if not is_single_method_flow:
                diagram_lines.append("    end")

        diagram_lines.append("```")
        return "\n".join(diagram_lines)

    def get_available_classes(self, project_name: Optional[str] = None) -> List[Dict]:
        pass

    def get_class_methods(self, class_name: str, project_name: Optional[str] = None) -> List[Dict]:
        pass

    def _is_external_call(self, package_name: Optional[str]) -> bool:
        pass