import logging
import copy
import os
import subprocess
import tempfile
from datetime import datetime
from typing import List, Dict, Set, Optional
from neo4j import Driver
from csa.utils.logger import get_logger

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
        project_name: Optional[str] = None,
        output_dir: str = "output",
        image_format: str = "png",
        image_width: int = 1200,
        image_height: int = 800
    ) -> Dict:
        try:
            with self.driver.session() as session:
                class_info = self._get_class_info(session, class_name, project_name)
                if not class_info:
                    return f"Error: Class '{class_name}' not found in database."

                # 클래스 단위인 경우: 클래스의 메서드들을 리스트업하고 각 메서드마다 반복
                if method_name is None:
                    return self._generate_class_level_diagram(session, class_info, max_depth, include_external_calls, project_name, output_dir, image_format, image_width, image_height)
                
                # 메서드 단위인 경우: 기존 로직 사용
                call_chain = self._fetch_call_chain(session, class_name, method_name, max_depth, project_name)
                if not call_chain:
                    return {
                        "type": "method",
                        "class_name": class_name,
                        "method_name": method_name,
                        "diagram_path": None,
                        "image_path": None,
                        "error": f"No outbound calls found for {method_name}."
                    }

                flows = self._build_flows(call_chain, method_name)
                diagram = self._generate_plantuml_diagram(session, class_info, flows, include_external_calls, method_name, project_name)
                
                # 메서드 단위 파일 생성
                timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                package_name = class_info.get('package_name', '')
                # project_name 획득: class_info에서 가져오거나 파라미터 사용
                actual_project_name = class_info.get('project_name', project_name or 'default_project')
                
                # 패키지명을 디렉토리 경로로 변환
                if package_name:
                    package_path = package_name.replace('.', os.sep)
                    final_output_dir = os.path.join(output_dir, actual_project_name, package_path)
                else:
                    final_output_dir = os.path.join(output_dir, actual_project_name)
                
                # 파일명 생성: SEQ_클래스명_메서드명_YYYYMMDD-HH24MiSS.puml
                filename = f"SEQ_{class_name}_{method_name}_{timestamp}.puml"
                os.makedirs(final_output_dir, exist_ok=True)
                diagram_path = os.path.join(final_output_dir, filename)
                
                with open(diagram_path, 'w', encoding='utf-8') as f:
                    f.write(diagram)
                
                logger.info(f"Generated sequence diagram: {diagram_path}")
                
                result = {
                    "type": "method",
                    "class_name": class_name,
                    "method_name": method_name,
                    "diagram_path": diagram_path,
                    "image_path": None
                }
                
                # 이미지 변환
                if image_format and image_format != "none":
                    image_filename = f"SEQ_{class_name}_{method_name}_{timestamp}-P.{image_format}"
                    image_path = os.path.join(final_output_dir, image_filename)
                    
                    if self._convert_to_image(diagram, image_path, image_format, image_width, image_height):
                        result["image_path"] = image_path
                        logger.info(f"Generated image: {image_path}")
                
                return result
        except Exception as e:
            logger.error(f"Error generating PlantUML sequence diagram: {e}", exc_info=True)
            return f"Error: {e}"

    def _generate_class_level_diagram(self, session, class_info: Dict, max_depth: int, include_external_calls: bool, project_name: Optional[str], output_dir: str, image_format: str = "png", image_width: int = 1200, image_height: int = 800) -> Dict:
        """클래스 단위 다이어그램 생성: 각 메서드별로 별도 파일 생성"""
        class_name = class_info['name']
        package_name = class_info.get('package_name', '')
        # project_name 획득: class_info에서 가져오거나 파라미터 사용
        actual_project_name = class_info.get('project_name', project_name or 'default_project')
        
        # 패키지명을 디렉토리 경로로 변환
        if package_name:
            package_path = package_name.replace('.', os.sep)
            final_output_dir = os.path.join(output_dir, actual_project_name, package_path)
        else:
            final_output_dir = os.path.join(output_dir, actual_project_name)
        
        # 1. 클래스의 메서드들을 리스트업
        methods = self._get_class_methods(session, class_name, project_name)
        if not methods:
            return {
                "type": "class",
                "class_name": class_name,
                "files": [],
                "output_dir": final_output_dir,
                "error": "No methods found in this class."
            }
        
        # 2. 각 메서드별로 개별 다이어그램 파일 생성
        generated_files = []
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        
        for method in methods:
            method_name = method['name']
            # 메서드 단위 호출 체인 가져오기 (메서드 단위와 동일한 로직 사용)
            call_chain = self._fetch_call_chain(session, class_name, method_name, max_depth, project_name)
            
            if call_chain:
                # 메서드 단위 플로우 빌딩 (메서드 단위와 동일한 로직 사용)
                method_flows = self._build_flows(call_chain, method_name)
                
                if method_flows:
                    # 개별 메서드 다이어그램 생성
                    diagram = self._generate_plantuml_diagram(session, class_info, method_flows, include_external_calls, method_name, project_name)
                    
                    # 파일명 생성: SEQ_클래스명_메서드명_YYYYMMDD-HH24MiSS.puml
                    filename = f"SEQ_{class_name}_{method_name}_{timestamp}.puml"
                    
                    # 지정된 디렉토리에 파일 저장 (패키지 구조 반영)
                    os.makedirs(final_output_dir, exist_ok=True)
                    diagram_path = os.path.join(final_output_dir, filename)
                    
                    with open(diagram_path, 'w', encoding='utf-8') as f:
                        f.write(diagram)
                    
                    logger.info(f"Generated sequence diagram: {diagram_path}")
                    
                    file_info = {
                        "diagram_path": diagram_path,
                        "image_path": None
                    }
                    
                    # 이미지 변환
                    if image_format and image_format != "none":
                        image_filename = f"SEQ_{class_name}_{method_name}_{timestamp}-P.{image_format}"
                        image_path = os.path.join(final_output_dir, image_filename)
                        
                        if self._convert_to_image(diagram, image_path, image_format, image_width, image_height):
                            file_info["image_path"] = image_path
                            logger.info(f"Generated image: {image_path}")
                    
                    generated_files.append(file_info)
        
        return {
            "type": "class",
            "class_name": class_name,
            "files": generated_files,
            "output_dir": final_output_dir
        }

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
        RETURN c.name as name, c.package_name as package_name, c.project_name as project_name
        """
        result = session.run(query, class_name=class_name, project_name=project_name)
        record = result.single()
        return dict(record) if record else None

    def _get_method_return_type(self, session, class_name: str, method_name: str, project_name: Optional[str]) -> Optional[str]:
        """Get method's return type from database."""
        query = """
        MATCH (c:Class {name: $class_name})-[:HAS_METHOD]->(m:Method {name: $method_name})
        WHERE ($project_name IS NULL OR c.project_name = $project_name)
        RETURN m.return_type as return_type
        """
        result = session.run(query, class_name=class_name, method_name=method_name, project_name=project_name)
        record = result.single()
        return record['return_type'] if record and record['return_type'] else None

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
        WITH m.name as top_level_method, nodes(path)[i] AS source_method, nodes(path)[i+1] AS target_method, (i + 1) as depth, relationships(path)[i] as rel
        MATCH (source_class:Class)-[:HAS_METHOD]->(source_method)
        MATCH (target_class:Class)-[:HAS_METHOD]->(target_method)
        WITH top_level_method, source_class, source_method, target_class, target_method, depth, rel
        WHERE source_class.project_name IS NOT NULL AND target_class.project_name IS NOT NULL
        RETURN DISTINCT top_level_method, source_class.name AS source_class, source_method.name AS source_method, target_class.name AS target_class, target_method.name AS target_method, target_method.return_type AS return_type, depth, "" as table_name, "" as sql_type, source_class.package_name as source_package, target_class.package_name as target_package, "" as mapper_name, "" as mapper_namespace, "" as mapper_file_path, COALESCE(rel.call_order, 999) as call_order
        ORDER BY top_level_method, call_order, depth
        
        UNION ALL
        
        MATCH (c:Class)-[:HAS_METHOD]->(m:Method) 
        WHERE c.name = $class_name AND ({method_condition}) AND (c.project_name = $project_name OR $project_name IS NULL)
        MATCH path = (m)-[:CALLS*0..{max_depth}]->(calling_method:Method)
        MATCH (source_class:Class)-[:HAS_METHOD]->(calling_method)
        MATCH (mapper_node:MyBatisMapper {{name: source_class.name}})
        WHERE mapper_node.project_name = $project_name OR $project_name IS NULL
        MATCH (mapper_node)-[:HAS_SQL_STATEMENT]->(sql:SqlStatement {{id: calling_method.name}})
        WITH m, path, source_class, calling_method, sql, mapper_node
        WHERE source_class.project_name IS NOT NULL AND sql IS NOT NULL
        RETURN DISTINCT m.name as top_level_method, source_class.name AS source_class, calling_method.name AS source_method, 'SQL' AS target_class, sql.id AS target_method, 'Result' AS return_type, length(path) + 1 AS depth, "" as table_name, "" as sql_type, source_class.package_name as source_package, "" as target_package, sql.mapper_name as mapper_name, mapper_node.namespace as mapper_namespace, mapper_node.file_path as mapper_file_path, 999 as call_order
        
        UNION ALL
        
        MATCH (c:Class)-[:HAS_METHOD]->(m:Method) 
        WHERE c.name = $class_name AND ({method_condition}) AND (c.project_name = $project_name OR $project_name IS NULL)
        MATCH (mapper_node:MyBatisMapper {{name: $class_name}})
        WHERE mapper_node.project_name = $project_name OR $project_name IS NULL
        MATCH (mapper_node)-[:HAS_SQL_STATEMENT]->(sql:SqlStatement {{id: m.name}})
        WHERE sql IS NOT NULL
        RETURN DISTINCT m.name as top_level_method, $class_name AS source_class, m.name AS source_method, 'SQL' AS target_class, sql.id AS target_method, 'Result' AS return_type, 1 AS depth, "" as table_name, "" as sql_type, c.package_name as source_package, "" as target_package, sql.mapper_name as mapper_name, mapper_node.namespace as mapper_namespace, mapper_node.file_path as mapper_file_path, 999 as call_order
        
        UNION ALL
        
        MATCH (c:Class)-[:HAS_METHOD]->(m:Method) 
        WHERE c.name = $class_name AND ({method_condition}) AND (c.project_name = $project_name OR $project_name IS NULL)
        MATCH path = (m)-[:CALLS*0..{max_depth}]->(calling_method:Method)
        MATCH (source_class:Class)-[:HAS_METHOD]->(calling_method)
        MATCH (mapper_node:MyBatisMapper {{name: source_class.name}})
        WHERE mapper_node.project_name = $project_name OR $project_name IS NULL
        MATCH (mapper_node)-[:HAS_SQL_STATEMENT]->(sql:SqlStatement {{id: calling_method.name}})
        WITH m, path, source_class, calling_method, sql, mapper_node
        WHERE source_class.project_name IS NOT NULL AND sql IS NOT NULL AND sql.tables IS NOT NULL
        UNWIND apoc.convert.fromJsonList(sql.tables) as table_info
        RETURN DISTINCT m.name as top_level_method, 'SQL' AS source_class, sql.id AS source_method, table_info.name AS target_class, sql.sql_type AS target_method, 'Data' AS return_type, length(path) + 2 AS depth, table_info.name as table_name, sql.sql_type as sql_type, "" as source_package, "" as target_package, sql.mapper_name as mapper_name, mapper_node.namespace as mapper_namespace, mapper_node.file_path as mapper_file_path, 999 as call_order
        
        UNION ALL
        
        MATCH (c:Class)-[:HAS_METHOD]->(m:Method) 
        WHERE c.name = $class_name AND ({method_condition}) AND (c.project_name = $project_name OR $project_name IS NULL)
        MATCH (mapper_node:MyBatisMapper {{name: $class_name}})
        WHERE mapper_node.project_name = $project_name OR $project_name IS NULL
        MATCH (mapper_node)-[:HAS_SQL_STATEMENT]->(sql:SqlStatement {{id: m.name}})
        WHERE sql IS NOT NULL AND sql.tables IS NOT NULL
        UNWIND apoc.convert.fromJsonList(sql.tables) as table_info
        RETURN DISTINCT m.name as top_level_method, 'SQL' AS source_class, sql.id AS source_method, table_info.name AS target_class, sql.sql_type AS target_method, 'Data' AS return_type, 2 AS depth, table_info.name as table_name, sql.sql_type as sql_type, "" as source_package, "" as target_package, sql.mapper_name as mapper_name, mapper_node.namespace as mapper_namespace, mapper_node.file_path as mapper_file_path, 999 as call_order
        """

        result = session.run(final_query, query_params)
        call_chain = [dict(record) for record in result]
        
        # 디버깅 로그 추가
        sql_calls = [call for call in call_chain if call.get('target_class') == 'SQL']
        table_calls = [call for call in call_chain if call.get('source_class') == 'SQL']
        logger.info(f"_fetch_call_chain: 총 {len(call_chain)}개 호출, SQL 호출: {len(sql_calls)}개, Table 호출: {len(table_calls)}개")
        
        return call_chain

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
        
        # 각 메서드별로 호출 순서 정렬
        for method_name, calls in flows.items():
            # 간단하고 명확한 정렬: depth 우선, 그 다음 call_order
            sorted_calls = sorted(calls, key=lambda c: (
                c.get('depth', 0),      # depth 우선
                c.get('call_order', 999)  # 같은 depth 내에서는 call_order로 정렬
            ))
            flows[method_name] = sorted_calls
        
        # 디버깅 로그 추가
        all_flow_calls = [call for flow in flows.values() for call in flow]
        sql_calls_in_flows = [call for call in all_flow_calls if call.get('target_class') == 'SQL']
        table_calls_in_flows = [call for call in all_flow_calls if call.get('source_class') == 'SQL']
        logger.info(f"_build_flows: 총 {len(all_flow_calls)}개 호출, SQL 호출: {len(sql_calls_in_flows)}개, Table 호출: {len(table_calls_in_flows)}개")
        
        return flows
    
    def _is_call_from_method(self, call: Dict, top_method: str) -> bool:
        """Check if a call is directly or indirectly from the top-level method."""
        # This is a simplified check - in reality, we'd need to verify the call chain
        # For now, we'll accept calls where the source is not empty and different from target
        source_method = call.get('source_method', '')
        target_method = call.get('target_method', '')
        
        # Accept calls that are clearly part of the execution flow
        return bool(source_method and target_method and source_method != target_method)

    def _generate_plantuml_diagram(self, session, class_info: Dict, flows: Dict[str, List[Dict]], include_external_calls: bool, start_method: Optional[str], project_name: Optional[str]) -> str:
        """Generate PlantUML sequence diagram with proper activation lifecycle management."""
        main_class_name = class_info['name']
        main_class_package = class_info.get('package_name', '')
        all_calls = [call for flow in flows.values() for call in flow]

        # 디버깅 로그 추가
        sql_calls = [call for call in all_calls if call.get('target_class') == 'SQL']
        table_calls = [call for call in all_calls if call.get('source_class') == 'SQL']
        logger.info(f"_generate_plantuml_diagram: 총 {len(all_calls)}개 호출, SQL 호출: {len(sql_calls)}개, Table 호출: {len(table_calls)}개")

        # Participant별 package 정보 수집
        participant_packages = {}
        
        # 메인 클래스의 패키지 정보 추가
        if main_class_package:
            participant_packages[main_class_name] = main_class_package
        
        # SQL participant의 mapper 정보 수집
        sql_mapper_info = {}
        
        # 모든 호출에서 participant의 package 정보 및 mapper 정보 수집
        for call in all_calls:
            source_class = call.get('source_class', '')
            target_class = call.get('target_class', '')
            source_package = call.get('source_package', '')
            target_package = call.get('target_package', '')
            mapper_name = call.get('mapper_name', '')
            mapper_namespace = call.get('mapper_namespace', '')
            mapper_file_path = call.get('mapper_file_path', '')
            
            if source_class and source_package and source_class not in ['Client', 'SQL']:
                participant_packages[source_class] = source_package
            if target_class and target_package and target_class not in ['Client', 'SQL']:
                participant_packages[target_class] = target_package
            
            # SQL과 관련된 호출에서 mapper 정보 수집
            if (target_class == 'SQL' or source_class == 'SQL') and mapper_file_path:
                # 파일명 추출: 마지막 / 또는 \ 뒤의 문자열
                file_name = os.path.basename(mapper_file_path)
                
                sql_mapper_info['SQL'] = {
                    'file_name': file_name,
                    'namespace': mapper_namespace
                }

        # Participant ordering logic - SQL and Tables at the end
        table_participants = {p['target_class'] for p in all_calls if p['source_class'] == 'SQL'}
        ordered_participants = ['Client', main_class_name]
        seen_participants = {'Client', main_class_name}
        sql_participant = None

        # all_calls는 이미 _build_flows에서 정렬되었으므로 다시 정렬하지 않음
        # all_calls.sort(key=lambda x: x.get('depth') or 0)  # 제거

        # Collect table schema information
        table_schemas = {}
        for table_name in table_participants:
            schema = self._get_table_schema(session, table_name, project_name)
            if schema:
                table_schemas[table_name] = schema

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
        
        # Add title based on method name
        if start_method:
            # Method-level diagram: show specific method
            title = f"{main_class_name}.{start_method}()"
        else:
            # Class-level diagram: show class name
            title = f"{main_class_name} Class Methods"
        
        diagram_lines.append(f"title {title}")
        diagram_lines.append("")
        
        # Add participants with package information
        for p in final_participants_unique:
            if p == 'Client':
                diagram_lines.append(f"actor {p} as \"Client\"")
            elif p == 'SQL':
                # Add mapper file name and namespace to SQL participant if available
                mapper_info = sql_mapper_info.get('SQL', {})
                file_name = mapper_info.get('file_name', '')
                namespace = mapper_info.get('namespace', '')
                
                if file_name and namespace:
                    diagram_lines.append(f"participant SQL as \"{file_name}\" << {namespace} >>")
                elif file_name:
                    diagram_lines.append(f"participant SQL as \"{file_name}\"")
                else:
                    diagram_lines.append(f"participant SQL as \"SQL statement\"")
            elif p in table_participants:
                schema = table_schemas.get(p, None)
                if schema:
                    diagram_lines.append(f'participant {p} as "Table : {p}" << Schema : {schema} >>')
                else:
                    diagram_lines.append(f'participant {p} as "Table : {p}"')
            else:
                # Add package information as stereotype if available
                package_info = participant_packages.get(p, '')
                if package_info and package_info.strip():
                    diagram_lines.append(f"participant {p} << {package_info} >>")
                else:
                    diagram_lines.append(f"participant {p}")
        
        diagram_lines.append("")

        # Generate flows with proper activation lifecycle management
        is_single_method_flow = (len(flows) == 1)
        is_focused_method = (start_method is not None)

        for top_method, calls in flows.items():
            # Top-level 메서드의 실제 return type 조회
            top_method_return_type = self._get_method_return_type(session, main_class_name, top_method, project_name)
            
            if not is_single_method_flow and not is_focused_method:
                diagram_lines.append(f"group flow for {top_method}")

            # Client call
            diagram_lines.append(f"Client -> {main_class_name} : {top_method}()")
            diagram_lines.append(f"activate Client")
            diagram_lines.append(f"activate {main_class_name}")
            
            # Build properly ordered flow with activation stack management
            activation_events = self._build_activation_aware_flow(calls, main_class_name, top_method)
            
            # Render the events with proper activation lifecycle
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
                    
                    # Find and remove from activation stack (LIFO - Last In First Out)
                    activation_entry = None
                    for i in range(len(activation_stack) - 1, -1, -1):
                        if activation_stack[i]['participant'] == source:
                            activation_entry = activation_stack.pop(i)
                            break
                    
                    if activation_entry:
                        # Show return message
                        diagram_lines.append(f"{source} --> {target} : return ({return_type})")
                        diagram_lines.append(f"deactivate {source}")
                        active_participants.discard(source)
                
                elif event['type'] == 'self_return':
                    # Internal void returns - show return message before deactivate
                    source = event['source']
                    target = event['target']
                    
                    # Find and remove from activation stack (LIFO - Last In First Out)
                    activation_entry = None
                    for i in range(len(activation_stack) - 1, -1, -1):
                        if activation_stack[i]['participant'] == source:
                            activation_entry = activation_stack.pop(i)
                            break
                    
                    if activation_entry:
                        diagram_lines.append(f"{source} --> {target} : return (void)")
                        diagram_lines.append(f"deactivate {source}")
                        active_participants.discard(source)

            # Final cleanup - return and deactivate any remaining active participants in reverse order
            # Exclude Client and main_class_name from cleanup (they will be handled separately)
            remaining_active = list(active_participants - {'Client', main_class_name})
            remaining_active.sort(key=lambda x: final_participants_unique.index(x) if x in final_participants_unique else 999)
            
            for participant in remaining_active:
                # Return to caller before deactivating
                diagram_lines.append(f"{participant} --> {main_class_name} : return (void)")
                diagram_lines.append(f"deactivate {participant}")
            
            # Client final return with actual return type
            final_return_type = top_method_return_type if top_method_return_type else "void"
            diagram_lines.append(f"{main_class_name} --> Client : return ({final_return_type})")
            diagram_lines.append(f"deactivate {main_class_name}")
            diagram_lines.append(f"deactivate Client")

            if not is_single_method_flow and not is_focused_method:
                diagram_lines.append("end")

        diagram_lines.append("@enduml")
        return "\n".join(diagram_lines)

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
                # Sort children by call_order for proper sequence
                sorted_children = sorted(calls_from_source[key], key=lambda call: call.get('call_order', 999))
                
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
                        
                        # Recursively process the target method (this will add its own return events)
                        build_events_dfs(call['target_class'], call['target_method'])
                        
                        # Add return event immediately after the target method completes
                        # This ensures proper nested activation/deactivation
                        return_type = call.get('return_type', 'void')
                        return_target = call['source_class']  # Return to caller
                        
                        if return_type in ['void', 'None', None, '']:
                            # Void returns - show return and deactivate
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
            'JwtUserPrincipal', 'log', 'ResponseEntity', 'Collectors'
        ]
        
        # Special case: equals() method should always be treated as external library call
        if target_method == 'equals' and target_class != 'String':
            return True
            
        return target_class in external_classes

    def _get_table_schema(self, session, table_name: str, project_name: Optional[str]) -> Optional[str]:
        """Get table schema information from database."""
        query = """
        MATCH (t:Table {name: $table_name})
        WHERE (t.project_name IS NULL OR t.project_name = $project_name)
        RETURN t.schema as schema
        """
        result = session.run(query, table_name=table_name, project_name=project_name)
        record = result.single()
        return record['schema'] if record and record['schema'] else None

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

    def _convert_to_image(self, diagram_content: str, output_file: str, image_format: str, width: int, height: int) -> bool:
        """Convert PlantUML diagram to image using plantuml.jar"""
        try:
            # Try different possible locations for plantuml.jar
            plantuml_paths = [
                'plantuml.jar',
                os.path.join(os.getcwd(), 'plantuml.jar'),
                os.path.join(os.path.dirname(__file__), '..', '..', 'plantuml.jar'),
                os.path.join(os.path.dirname(__file__), '..', '..', 'libs', 'plantuml.jar'),
                r'C:\plantuml\plantuml.jar'
            ]
            
            plantuml_jar = None
            for path in plantuml_paths:
                if os.path.exists(path):
                    plantuml_jar = path
                    break
            
            if not plantuml_jar:
                logger.error("plantuml.jar not found. Please install PlantUML.")
                return False
            
            # Determine format from output file extension
            file_extension = output_file.split('.')[-1].lower()
            actual_format = file_extension if file_extension in ['png', 'svg', 'pdf'] else image_format
            
            # Create temporary file in the output directory (not system temp)
            output_dir = os.path.dirname(output_file) or '.'
            os.makedirs(output_dir, exist_ok=True)
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.puml', delete=False, encoding='utf-8', newline='', dir=output_dir) as temp_file:
                temp_file.write(diagram_content)
                temp_file_path = temp_file.name
            
            # Convert to image using plantuml.jar
            cmd = [
                'java', '-jar', plantuml_jar,
                f'-t{actual_format}',
                temp_file_path
            ]
            
            logger.info(f"Running command: {' '.join(cmd)}")
            
            # Set environment variables for UTF-8 encoding
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            env['LANG'] = 'en_US.UTF-8'
            env['LC_ALL'] = 'en_US.UTF-8'
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, encoding='utf-8', errors='ignore', env=env)
            
            # Log PlantUML output for debugging
            if result.stdout:
                logger.info(f"PlantUML stdout: {result.stdout}")
            if result.stderr:
                logger.info(f"PlantUML stderr: {result.stderr}")
            
            # Check if the expected output file was created (in the same directory as temp file)
            expected_filename = os.path.splitext(os.path.basename(temp_file_path))[0] + '.' + actual_format
            expected_path = os.path.join(os.path.dirname(temp_file_path), expected_filename)
            
            # Clean up temporary .puml file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
            
            if os.path.exists(expected_path):
                # Rename to the desired output filename
                if expected_path != output_file:
                    os.rename(expected_path, output_file)
                logger.info(f"Image saved to: {output_file}")
                return True
            else:
                logger.error(f"Expected file {expected_path} not found")
                logger.error(f"Temp file was: {temp_file_path}")
                logger.error(f"Output file should be: {output_file}")
                return False
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Error converting to image: {e}")
            logger.error(f"Error output: {e.stderr}")
            if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
            return False
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
            return False