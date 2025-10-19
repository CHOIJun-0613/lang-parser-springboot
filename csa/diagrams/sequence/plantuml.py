import logging
import copy
import os
import subprocess
import tempfile
from datetime import datetime
from typing import List, Dict, Set, Optional
from neo4j import Driver
from csa.utils.logger import get_logger
from csa.diagrams.sequence.repository import (
    build_activation_aware_flow,
    build_flows,
    fetch_call_chain,
    get_class_info,
    get_class_methods,
    get_method_return_type,
    get_table_schema,
    is_call_from_method,
    is_external_library_call,
    resolve_project_name,
    should_filter_call,
)

logger = get_logger(__name__)

class PlantUMLDiagramGenerator:
    """Generates PlantUML sequence diagrams from Java code analysis data."""

    def __init__(self, driver: Driver, database: Optional[str] = None, external_packages: Optional[Set[str]] = None):
        self.driver = driver
        self.database = database

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
            session_kwargs = {"database": self.database} if self.database else {}
            with self.driver.session(**session_kwargs) as session:
                class_info = get_class_info(session, class_name, project_name)
                if not class_info:
                    return f"Error: Class '{class_name}' not found in database."

                # 클래스 단위인 경우: 클래스의 메서드들을 리스트업하고 각 메서드마다 반복
                if method_name is None:
                    return self._generate_class_level_diagram(session, class_info, max_depth, include_external_calls, project_name, output_dir, image_format, image_width, image_height)
                
                # 메서드 단위인 경우: 기존 로직 사용
                call_chain = fetch_call_chain(session, class_name, method_name, max_depth, project_name)
                if not call_chain:
                    return {
                        "type": "method",
                        "class_name": class_name,
                        "method_name": method_name,
                        "diagram_path": None,
                        "image_path": None,
                        "error": f"No outbound calls found for {method_name}."
                    }

                flows = build_flows(call_chain, method_name)
                diagram = self._generate_plantuml_diagram(session, class_info, flows, include_external_calls, method_name, project_name)
                
                # 메서드 단위 파일 생성
                timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                package_name = class_info.get('package_name', '')
                # project_name 획득: class_info에서 가져오거나 파라미터 사용
                actual_project_name = resolve_project_name(class_info, project_name)
                
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
        actual_project_name = resolve_project_name(class_info, project_name)
        
        # 패키지명을 디렉토리 경로로 변환
        if package_name:
            package_path = package_name.replace('.', os.sep)
            final_output_dir = os.path.join(output_dir, actual_project_name, package_path)
        else:
            final_output_dir = os.path.join(output_dir, actual_project_name)
        
        # 1. 클래스의 메서드들을 리스트업
        methods = get_class_methods(session, class_name, project_name)
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
            call_chain = fetch_call_chain(session, class_name, method_name, max_depth, project_name)
            
            if call_chain:
                # 메서드 단위 플로우 빌딩 (메서드 단위와 동일한 로직 사용)
                method_flows = build_flows(call_chain, method_name)
                
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
        return get_class_methods(session, class_name, project_name)

    def _get_class_info(self, session, class_name: str, project_name: Optional[str]) -> Optional[Dict]:
        return get_class_info(session, class_name, project_name)

    def _get_method_return_type(self, session, class_name: str, method_name: str, project_name: Optional[str]) -> Optional[str]:
        return get_method_return_type(session, class_name, method_name, project_name)

    def _fetch_call_chain(self, session, class_name: str, method_name: Optional[str], max_depth: int, project_name: Optional[str]) -> List[Dict]:
        return fetch_call_chain(session, class_name, method_name, max_depth, project_name)

    def _build_flows(self, call_chain: List[Dict], start_method: Optional[str] = None) -> Dict[str, List[Dict]]:
        return build_flows(call_chain, start_method)

    def _is_call_from_method(self, call: Dict, top_method: str) -> bool:
        return is_call_from_method(call, top_method)

    def _generate_plantuml_diagram(self, session, class_info: Dict, flows: Dict[str, List[Dict]], include_external_calls: bool, start_method: Optional[str], project_name: Optional[str]) -> str:
        """Generate PlantUML sequence diagram with proper activation lifecycle management."""
        main_class_name = class_info['name']
        main_class_package = class_info.get('package_name', '')
        all_calls = [call for flow in flows.values() for call in flow]

        sql_calls = [call for call in all_calls if call.get('call_type') == 'sql']
        table_calls = [call for call in all_calls if call.get('call_type') == 'table']
        logger.info(f"_generate_plantuml_diagram: total={len(all_calls)}, sql_calls={len(sql_calls)}, table_calls={len(table_calls)}")

        participant_packages: Dict[str, str] = {}
        if main_class_package:
            participant_packages[main_class_name] = main_class_package

        sql_participant_required = False
        sql_display_label: Optional[str] = None
        table_participants: Dict[str, Dict[str, str]] = {}

        for call in all_calls:
            call_type = call.get('call_type', 'method')
            source_class = call.get('source_class', '')
            source_package = call.get('source_package', '')
            target_class = call.get('target_class', '')
            target_package = call.get('target_package', '')

            if source_class and source_class not in {'Client', 'SQL'} and call_type != 'table':
                if source_package:
                    participant_packages.setdefault(source_class, source_package)

            if call_type == 'sql':
                sql_participant_required = True
                # Mapper participant 표시: 'Mapper name' ({namespace})
                mapper_name = call.get('mapper_name') or 'SQL'
                mapper_namespace = call.get('mapper_namespace') or ''
                if mapper_namespace:
                    sql_display_label = f"{mapper_name}\\n({mapper_namespace})"
                else:
                    sql_display_label = mapper_name
            elif call_type == 'table':
                if target_class:
                    schema_value = call.get('table_schema') or target_package or ''
                    display_value = call.get('table_display') or (f"{schema_value}.{target_class}" if schema_value else target_class)
                    table_participants.setdefault(target_class, {'schema': schema_value, 'display': display_value})
            else:
                if target_class and target_class not in {'Client', 'SQL'}:
                    if target_package:
                        participant_packages.setdefault(target_class, target_package)

        ordered_participants = ['Client', main_class_name]
        seen_participants = set(ordered_participants)

        for participant, package_name in participant_packages.items():
            if participant and participant not in seen_participants:
                ordered_participants.append(participant)
                seen_participants.add(participant)

        if sql_participant_required and 'SQL' not in seen_participants:
            ordered_participants.append('SQL')
            seen_participants.add('SQL')

        for table_name in table_participants:
            if table_name and table_name not in seen_participants:
                ordered_participants.append(table_name)
                seen_participants.add(table_name)

        final_participants = [p for p in ordered_participants if p and p != 'Unknown']

        if start_method:
            title = f"{main_class_name}.{start_method}()"
        else:
            title = f"{main_class_name} Class Methods"

        diagram_lines = ["@startuml", f"title {title}", ""]

        for participant in final_participants:
            if participant == 'Client':
                diagram_lines.append(f'actor {participant} as "Client"')
            elif participant == 'SQL':
                label = sql_display_label or 'SQL statement'
                diagram_lines.append(f'participant {participant} as "{label}"')
            elif participant in table_participants:
                display_value = table_participants[participant]['display']
                diagram_lines.append(f'participant {participant} as "{display_value}"')
            else:
                package_info = participant_packages.get(participant, '')
                if package_info:
                    diagram_lines.append(f"participant {participant} << {package_info} >>")
                else:
                    diagram_lines.append(f"participant {participant}")

        diagram_lines.append("")

        is_single_method_flow = len(flows) == 1
        is_focused_method = start_method is not None

        for top_method, calls in flows.items():
            top_method_return_type = get_method_return_type(session, main_class_name, top_method, project_name)

            if not is_single_method_flow and not is_focused_method:
                diagram_lines.append(f"group flow for {top_method}")

            diagram_lines.append(f"Client -> {main_class_name} : {top_method}()")
            diagram_lines.append("activate Client")
            diagram_lines.append(f"activate {main_class_name}")

            activation_events = build_activation_aware_flow(calls, main_class_name, top_method)

            for event in activation_events:
                if event.get('type') == 'call':
                    call_details = event.get('call', {}) or {}
                    event.setdefault('source', call_details.get('source_class', main_class_name))
                    event.setdefault('target', call_details.get('target_class'))
                    event.setdefault('method', call_details.get('target_method'))
                    event.setdefault('return_type', call_details.get('return_type', 'void'))
                    event.setdefault('call_type', call_details.get('call_type', 'method'))
                    event.setdefault('table_display', call_details.get('table_display'))
                    event.setdefault('sql_type', call_details.get('sql_type'))
                    event.setdefault('sql_logical_name', call_details.get('sql_logical_name'))
                    event.setdefault('sql_display', call_details.get('sql_display'))

            activation_stack: List[Dict[str, str]] = []
            active_participants = {'Client', main_class_name}

            for event in activation_events:
                if event['type'] == 'call':
                    call_details = event['call']
                    source = event['source']
                    target = event['target']
                    method = event['method']
                    return_type = event.get('return_type', 'void')
                    call_type = event.get('call_type', 'method')

                    if not target or not method:
                        continue

                    if call_type == 'sql':
                        sql_type = (call_details.get('sql_type') or '').upper()
                        if sql_type == 'SELECT':
                            icon = '??'
                        elif sql_type in {'INSERT', 'UPDATE', 'DELETE'}:
                            icon = '??'
                        else:
                            icon = '???'
                        # SQL 호출 표시: sql_id<<logical_name>>
                        sql_id = method
                        sql_logical_name = call_details.get('sql_logical_name') or ''
                        if sql_logical_name:
                            label = f"{sql_id}<<{sql_logical_name}>>"
                        else:
                            label = sql_id
                        call_str = f"{source} -> {target} : {icon} {label}"
                        activate_target = True
                    elif call_type == 'table':
                        table_display = call_details.get('table_display') or target
                        call_str = f"{source} -> {target} : ?? {table_display}"
                        activate_target = True
                    else:
                        is_external_library = is_external_library_call(call_details)
                        # 메서드 호출 표시: method_name()<<logical_name>>
                        method_logical_name = call_details.get('target_method_logical_name') or ''
                        if method_logical_name:
                            method_display = f"{method}()<<{method_logical_name}>>"
                        else:
                            method_display = f"{method}()"

                        if is_external_library:
                            call_str = f"{source} -> {target} : {method_display}"
                        else:
                            call_str = f"{source} -> {target} : {method_display}"
                        activate_target = not (is_external_library and target in {'String', 'Logger', 'System'})

                    diagram_lines.append(call_str)

                    if activate_target:
                        diagram_lines.append(f"activate {target}")
                        activation_stack.append({'participant': target, 'method': method, 'source': source, 'return_type': return_type})
                        active_participants.add(target)

                elif event['type'] == 'return':
                    source = event['source']
                    target = event['target']
                    return_type = event.get('return_type', 'void')

                    # activation_stack에서 source를 찾아서 제거
                    activation_entry = None
                    for idx in range(len(activation_stack) - 1, -1, -1):
                        if activation_stack[idx]['participant'] == source:
                            activation_entry = activation_stack.pop(idx)
                            break

                    # return 명령과 deactivate 명령 생성
                    if source in active_participants:
                        diagram_lines.append(f"{source} --> {target} : return ({return_type})")
                        diagram_lines.append(f"deactivate {source}")
                        active_participants.discard(source)

            # 남은 활성 참여자들을 모두 반환 처리
            remaining_active = [p for p in active_participants if p not in {'Client', main_class_name}]
            remaining_active.sort(key=lambda x: final_participants.index(x) if x in final_participants else 999)

            for participant in remaining_active:
                diagram_lines.append(f"{participant} --> {main_class_name} : return (void)")
                diagram_lines.append(f"deactivate {participant}")
                active_participants.discard(participant)

            # 메인 클래스의 리턴은 항상 표시
            final_return_type = top_method_return_type or 'void'
            diagram_lines.append(f"{main_class_name} --> Client : return ({final_return_type})")
            diagram_lines.append(f"deactivate {main_class_name}")
            diagram_lines.append("deactivate Client")
            active_participants.discard(main_class_name)
            active_participants.discard('Client')

            if not is_single_method_flow and not is_focused_method:
                diagram_lines.append("end")

        diagram_lines.append("@enduml")
        return "\n".join(diagram_lines)
    def _build_activation_aware_flow(self, calls: List[Dict], main_class_name: str, top_method: str) -> List[Dict]:
        return build_activation_aware_flow(calls, main_class_name, top_method)

    def _is_external_library_call(self, call: Dict) -> bool:
        return is_external_library_call(call)

    def _get_table_schema(self, session, table_name: str, project_name: Optional[str]) -> Optional[str]:
        return get_table_schema(session, table_name, project_name)

    def _should_filter_call(self, call: Dict) -> bool:
        return should_filter_call(call)

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
