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

class MermaidDiagramGenerator:
    """Generates Mermaid sequence diagrams from Java code analysis data."""

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
                diagram = self._generate_mermaid_diagram(session, class_info, flows, include_external_calls, method_name, project_name)
                
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
                
                # 파일명 생성: SEQ_클래스명_메서드명_YYYYMMDD-HH24MiSS.md
                filename = f"SEQ_{class_name}_{method_name}_{timestamp}.md"
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
                    image_filename = f"SEQ_{class_name}_{method_name}_{timestamp}-M.{image_format}"
                    image_path = os.path.join(final_output_dir, image_filename)
                    
                    if self._convert_to_image(diagram, image_path, image_format, image_width, image_height):
                        result["image_path"] = image_path
                        logger.info(f"Generated image: {image_path}")
                
                return result
        except Exception as e:
            logger.error(f"Error generating sequence diagram: {e}", exc_info=True)
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
                    diagram = self._generate_mermaid_diagram(session, class_info, method_flows, include_external_calls, method_name, project_name)
                    
                    # 파일명 생성: SEQ_클래스명_메서드명_YYYYMMDD-HH24MiSS.md
                    filename = f"SEQ_{class_name}_{method_name}_{timestamp}.md"
                    
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
                        image_filename = f"SEQ_{class_name}_{method_name}_{timestamp}-M.{image_format}"
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

    def _fetch_call_chain(self, session, class_name: str, method_name: Optional[str], max_depth: int, project_name: Optional[str]) -> List[Dict]:
        return fetch_call_chain(session, class_name, method_name, max_depth, project_name)

    def _build_flows(self, call_chain: List[Dict], start_method: Optional[str] = None) -> Dict[str, List[Dict]]:
        return build_flows(call_chain, start_method)

    def _is_call_from_method(self, call: Dict, top_method: str) -> bool:
        return is_call_from_method(call, top_method)

    def _generate_mermaid_diagram(self, session, class_info: Dict, flows: Dict[str, List[Dict]], include_external_calls: bool, start_method: Optional[str], project_name: Optional[str]) -> str:
        """Generate Mermaid sequence diagram with proper activation lifecycle management."""
        main_class_name = class_info['name']
        main_class_package = class_info.get('package_name', '')
        all_calls = [call for flow in flows.values() for call in flow]

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

        # Add title using Mermaid's --- syntax
        if start_method:
            # Method-level diagram: show specific method
            title = f"{main_class_name}.{start_method}()"
        else:
            # Class-level diagram: show class name
            title = f"{main_class_name} Class Methods"
        
        diagram_lines = [
            "```mermaid",
            "---",
            f"title: {title}",
            "---",
            "sequenceDiagram"
        ]
        diagram_lines.append("")
        
        # Add participants with additional information using alias (without quotes)
        for p in final_participants_unique:
            if p == 'Client':
                diagram_lines.append(f"    actor {p}")
            elif p == 'SQL':
                # Add mapper file name and namespace as alias (SQL name changed to mapper file name)
                mapper_info = sql_mapper_info.get('SQL', {})
                file_name = mapper_info.get('file_name', '')
                namespace = mapper_info.get('namespace', '')
                
                if file_name and namespace:
                    diagram_lines.append(f'    participant {p} as {file_name}<br/>({namespace})')
                elif file_name:
                    diagram_lines.append(f'    participant {p} as {file_name}')
                else:
                    diagram_lines.append(f'    participant {p} as SQL statement')
            elif p in table_participants:
                # Add schema as alias (without quotes)
                schema = table_schemas.get(p, None)
                if schema:
                    diagram_lines.append(f'    participant {p} as Table : {p}<br/>(Schema : {schema})')
                else:
                    diagram_lines.append(f'    participant {p} as Table : {p}')
            else:
                # Add package information as alias if available (without quotes)
                package_info = participant_packages.get(p, '')
                if package_info and package_info.strip():
                    diagram_lines.append(f'    participant {p} as {p}<br/>({package_info})')
                else:
                    diagram_lines.append(f"    participant {p}")
        
        diagram_lines.append("")

        # Generate flows with proper activation lifecycle management
        is_single_method_flow = (len(flows) == 1)
        is_focused_method = (start_method is not None)

        for top_method, calls in flows.items():
            # Top-level 메서드의 실제 return type 조회
            top_method_return_type = self._get_method_return_type(session, main_class_name, top_method, project_name)
            
            if not is_single_method_flow and not is_focused_method:
                diagram_lines.append(f"    opt flow for {top_method}")

            # Client call
            diagram_lines.append(f"    Client->>{main_class_name}: {top_method}()")
            diagram_lines.append(f"    activate {main_class_name}")
            
            # Build properly ordered flow with activation stack management
            activation_events = self._build_activation_aware_flow(calls, main_class_name, top_method)

            # Normalize event payloads so downstream rendering can assume keys exist
            for event in activation_events:
                if event.get('type') == 'call':
                    call_details = event.get('call', {}) or {}
                    event.setdefault('source', call_details.get('source_class', main_class_name))
                    event.setdefault('target', call_details.get('target_class'))
                    event.setdefault('method', call_details.get('target_method'))
                    event.setdefault('return_type', call_details.get('return_type', 'void'))
                    event.setdefault('source_package', call_details.get('source_package'))
                    event.setdefault('target_package', call_details.get('target_package'))
                    event.setdefault('call', call_details)
            
            # Render the events with proper activation lifecycle
            activation_stack = []  # Track activation stack for proper lifecycle
            active_participants = {main_class_name}  # Keep track of active participants
            
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
                        call_str = f"    {source}->>{target}: 🔍 {method}"
                    elif target in table_participants:
                        call_str = f"    {source}->>{target}: 📊 {method}"
                    elif target == 'SQL':
                        call_str = f"    {source}->>{target}: {method}"
                    elif is_external_library:
                        call_str = f"    {source}->>{target}: {method}()"
                    else:
                        call_str = f"    {source}->>{target}: {method}()"
                    
                    diagram_lines.append(call_str)
                    
                    # Activate target if it's not an external library call
                    if not is_external_library or target not in ['String', 'Logger', 'System']:
                        diagram_lines.append(f"    activate {target}")
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
                        diagram_lines.append(f"    {source}-->>{target}: return ({return_type})")
                        diagram_lines.append(f"    deactivate {source}")
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
                        diagram_lines.append(f"    {source}-->>{target}: return (void)")
                        diagram_lines.append(f"    deactivate {source}")
                        active_participants.discard(source)

            # Final cleanup - return and deactivate any remaining active participants in reverse order
            # Exclude main_class_name from cleanup (it will be handled separately)
            remaining_active = list(active_participants - {main_class_name})
            remaining_active.sort(key=lambda x: final_participants_unique.index(x) if x in final_participants_unique else 999)
            
            for participant in remaining_active:
                # Return to caller before deactivating
                diagram_lines.append(f"    {participant}-->>{main_class_name}: return (void)")
                diagram_lines.append(f"    deactivate {participant}")
            
            # Client final return with actual return type
            final_return_type = top_method_return_type if top_method_return_type else "void"
            diagram_lines.append(f"    {main_class_name}-->>Client: return ({final_return_type})")
            diagram_lines.append(f"    deactivate {main_class_name}")

            if not is_single_method_flow and not is_focused_method:
                diagram_lines.append("    end")

        diagram_lines.append("```")
        return "\n".join(diagram_lines)

    def _build_activation_aware_flow(self, calls: List[Dict], main_class_name: str, top_method: str) -> List[Dict]:
        return build_activation_aware_flow(calls, main_class_name, top_method)

    def _is_external_library_call(self, call: Dict) -> bool:
        return is_external_library_call(call)

    def _get_table_schema(self, session, table_name: str, project_name: Optional[str]) -> Optional[str]:
        return get_table_schema(session, table_name, project_name)

    def _get_method_return_type(self, session, class_name: str, method_name: str, project_name: Optional[str]) -> Optional[str]:
        return get_method_return_type(session, class_name, method_name, project_name)

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

    def _convert_to_image(self, diagram_content: str, output_file: str, image_format: str, width: int, height: int) -> bool:
        """Convert Mermaid diagram to image using mermaid-cli"""
        # Try different possible locations for mmdc
        mmdc_commands = ['mmdc', 'mmdc.cmd', r'C:\Users\cjony\AppData\Roaming\npm\mmdc', r'C:\Users\cjony\AppData\Roaming\npm\mmdc.cmd']
        
        mmdc_cmd = None
        for cmd in mmdc_commands:
            try:
                subprocess.run([cmd, '--version'], capture_output=True, check=True, timeout=5)
                mmdc_cmd = cmd
                break
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
                continue
        
        if not mmdc_cmd:
            logger.error("mermaid-cli is not installed or not found in PATH.")
            logger.error("Please install it with: npm install -g @mermaid-js/mermaid-cli")
            return False
        
        try:
            # Create temporary file for mermaid content
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8', newline='') as temp_file:
                temp_file.write(diagram_content)
                temp_file_path = temp_file.name
            
            # Determine format from output file extension
            file_extension = output_file.split('.')[-1].lower()
            actual_format = file_extension if file_extension in ['png', 'svg', 'pdf'] else image_format
            
            # Convert to image using mermaid-cli
            cmd = [
                mmdc_cmd,
                '-i', temp_file_path,
                '-o', output_file,
                '-e', actual_format,
                '-w', str(width),
                '-H', str(height)
            ]
            
            # Add PDF-specific options
            if image_format.lower() == 'pdf':
                # Set background color for PDF
                cmd.extend(['-b', 'white'])
                # Add PDF fit option
                cmd.append('-f')
            
            logger.info(f"Running command: {' '.join(cmd)}")
            
            # Set environment variables for UTF-8 encoding
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            env['LANG'] = 'en_US.UTF-8'
            env['LC_ALL'] = 'en_US.UTF-8'
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, encoding='utf-8', errors='ignore', env=env)
            
            # Clean up temporary file
            os.unlink(temp_file_path)
            
            # Check if the expected output file was created
            if os.path.exists(output_file):
                logger.info(f"Image saved to: {output_file}")
                return True
            else:
                # Check for files with similar names (mermaid-cli sometimes adds numbers)
                import glob
                pattern = output_file.replace('.pdf', '-*.pdf').replace('.png', '-*.png').replace('.svg', '-*.svg')
                matching_files = glob.glob(pattern)
                if matching_files:
                    actual_file = matching_files[0]
                    # Rename the file to the intended name
                    try:
                        os.rename(actual_file, output_file)
                        logger.info(f"Image saved to: {output_file} (renamed from {actual_file})")
                        return True
                    except Exception as e:
                        logger.error(f"Failed to rename {actual_file} to {output_file}: {e}")
                        logger.info(f"Image saved to: {actual_file}")
                        return True
                else:
                    logger.error(f"Expected file {output_file} not found")
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

    def _should_filter_call(self, call: Dict) -> bool:
        return should_filter_call(call)

    def get_available_classes(self, project_name: Optional[str] = None) -> List[Dict]:
        pass

    def get_class_methods(self, class_name: str, project_name: Optional[str] = None) -> List[Dict]:
        pass

    def _is_external_call(self, package_name: Optional[str]) -> bool:
        pass
