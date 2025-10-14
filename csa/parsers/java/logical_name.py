"""
Java Parser Addon for Rule001 - Logical Name Extraction
프로젝트별 논리명 추출 규칙을 실시간으로 해석하여 Java 객체 분석 시 적용
"""

import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, Dict, Any, List
from csa.vendor import javalang

from csa.models.graph_entities import Class, Method
from csa.services.graph_db import GraphDB
from csa.utils.logger import get_logger


# 규칙 섹션별 기본 템플릿을 정의해 규칙 파일이 없을 때도 동작하도록 한다.
DEFAULT_RULE_TEMPLATES: Dict[str, str] = {
    "java_class": "/**\\n * {logical_name}\\n */",
    "java_method": "/**\\n * {logical_name}\\n */",
    "java_field": "/**\\n * {logical_name}\\n */",
    "mybatis_mapper": "<!-- {logical_name} -->",
    "xml_sql": "<!-- {logical_name} -->",
}


class LogicalNameExtractor:
    """프로젝트별 논리명 추출기 - 개선된 버전 (전역 규칙 매니저 사용)"""
    
    _instances = {}  # 프로젝트별 인스턴스 캐시
    
    def __new__(cls, project_name: str, rules_directory: str = "rules"):
        # 프로젝트별로 인스턴스를 캐시하여 재사용
        cache_key = f"{project_name}_{rules_directory}"
        if cache_key not in cls._instances:
            instance = super().__new__(cls)
            cls._instances[cache_key] = instance
        return cls._instances[cache_key]

    def __init__(self, project_name: str, rules_directory: str = "rules"):
        # 이미 초기화된 인스턴스는 재초기화하지 않음
        if hasattr(self, '_initialized'):
            return
            
        self.project_name = project_name
        self.rules_directory = rules_directory
        self.logger = get_logger(__name__)
        
        # 전역 규칙 매니저에서 규칙 가져오기
        from csa.utils.rules_manager import rules_manager
        self.rules = rules_manager.get_logical_name_rules(project_name)
        
        self._compiled_patterns: Dict[str, re.Pattern] = {}
        self._initialized = True
    
    

    def _parse_rules_content(self, content: str) -> Dict[str, Any]:
        """규칙 내용을 파싱해 구조화된 정보로 변환"""
        rules: Dict[str, Dict[str, Any]] = {}
        for key, template in DEFAULT_RULE_TEMPLATES.items():
            rules[key] = {
                "template": template,
                "pattern": self._convert_template_to_pattern(template),
                "description": "",
            }

        current_section: Optional[str] = None

        for raw_line in content.split('\n'):
            line = raw_line.strip()
            if not line:
                continue

            if line.startswith('##'):
                if 'Class' in line:
                    current_section = 'java_class'
                elif 'Method' in line:
                    current_section = 'java_method'
                elif 'MyBatis' in line:
                    current_section = 'mybatis_mapper'
                elif 'SQL' in line:
                    current_section = 'xml_sql'
                elif 'Field' in line:
                    current_section = 'java_field'
                else:
                    current_section = None
                continue

            if not current_section:
                continue

            if line.startswith('-') and ':' in line:
                description = line.split(':', 1)[1].strip()
                rules[current_section]['description'] = description
                continue

            template = self._extract_template_from_line(line)
            if template:
                pattern = self._convert_template_to_pattern(template)
                if pattern:
                    rules[current_section]['template'] = template
                    rules[current_section]['pattern'] = pattern

        return rules

    def _extract_template_from_line(self, line: str) -> Optional[str]:
        """라인에서 {logical_name} 플레이스홀더가 포함된 템플릿을 추출"""
        template_match = re.search(r"'([^']*{logical_name}[^']*)'", line)
        if template_match:
            return template_match.group(1).replace('{local_name}', '{logical_name}')
        
        template_match = re.search(r'`([^`]*{logical_name}[^`]*)`', line)
        if template_match:
            return template_match.group(1).replace('{local_name}', '{logical_name}')
        
        if '{logical_name}' in line and line.strip().startswith('<!--'):
            return line.strip()
        
        if '{local_name}' in line and line.strip().startswith('<!--'):
            return line.strip().replace('{local_name}', '{logical_name}')
        
        return None

    def _convert_template_to_pattern(self, template: str) -> Optional[str]:
        """템플릿 문자열을 정규식 패턴으로 변환"""
        placeholder = '{logical_name}'
        if placeholder not in template:
            return None

        normalized = template.strip().replace('\\n', '\n')
        segments = normalized.split(placeholder)
        escaped_segments = [re.escape(segment) for segment in segments]
        pattern = '(?P<logical_name>.+?)'.join(escaped_segments)

        pattern = pattern.replace('\n', r'\s*')
        pattern = re.sub(r'(\\ )+', r'\\s*', pattern)
        pattern = pattern.replace(r'\t', r'\s*')
        return pattern

    def _get_compiled_pattern(self, section_key: str) -> Optional[re.Pattern]:
        """섹션별 정규식을 컴파일하여 재사용"""
        if section_key in self._compiled_patterns:
            return self._compiled_patterns[section_key]

        rule = self.rules.get(section_key)
        if not rule:
            return None

        pattern = rule.get('pattern')
        if not pattern:
            return None

        try:
            compiled = re.compile(pattern, re.MULTILINE)
            self._compiled_patterns[section_key] = compiled
            return compiled
        except re.error as exc:
            self.logger.error(f"정규식 컴파일 실패({section_key}): {exc}")
            return None

    def _match_logical_name_from_rules(self, section_key: str, text: str) -> Optional[str]:
        """규칙 기반 패턴으로부터 논리명을 추출"""
        if not text:
            return None

        compiled = self._get_compiled_pattern(section_key)
        if not compiled:
            return None

        match = compiled.search(text)
        if not match:
            return None

        logical_name = match.groupdict().get('logical_name')
        if logical_name:
            return logical_name.strip()

        if match.groups():
            return match.group(1).strip()

        return None

    def update_class_logical_name(self, graph_db: GraphDB, class_name: str, project_name: str, logical_name: str):
        """클래스의 논리명을 DB에 업데이트"""
        try:
            with graph_db._driver.session() as session:
                query = """
                MATCH (c:Class {name: $class_name, project_name: $project_name})
                SET c.logical_name = $logical_name
                RETURN c.name as class_name
                """
                result = session.run(query, 
                                  class_name=class_name, 
                                  project_name=project_name, 
                                  logical_name=logical_name)
                
                if result.single():
                    self.logger.info(f"클래스 논리명 업데이트 완료: {class_name} -> {logical_name}")
                    return True
                else:
                    self.logger.warning(f"클래스 찾을 수 없음: {class_name}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"클래스 논리명 업데이트 실패: {e}")
            return False
    
    def update_method_logical_name(self, graph_db: GraphDB, class_name: str, method_name: str, project_name: str, logical_name: str):
        """메서드의 논리명을 DB에 업데이트"""
        try:
            with graph_db._driver.session() as session:
                query = """
                MATCH (m:Method {name: $method_name, class_name: $class_name, project_name: $project_name})
                SET m.logical_name = $logical_name
                RETURN m.name as method_name
                """
                result = session.run(query, 
                                  method_name=method_name,
                                  class_name=class_name,
                                  project_name=project_name, 
                                  logical_name=logical_name)
                
                if result.single():
                    self.logger.info(f"메서드 논리명 업데이트 완료: {class_name}.{method_name} -> {logical_name}")
                    return True
                else:
                    self.logger.warning(f"메서드 찾을 수 없음: {class_name}.{method_name}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"메서드 논리명 업데이트 실패: {e}")
            return False


class JavaLogicalNameExtractor(LogicalNameExtractor):
    """Java 파일 전용 논리명 추출기"""

    def __init__(self, project_name: str, rules_directory: str = "rules"):
        super().__init__(project_name, rules_directory)

    def _collect_comment_block(self, lines: List[str], start_index: int, max_scan: int = 30) -> str:
        """선언부 위쪽의 주석 블록을 역방향으로 수집한다."""
        comment_lines: list[str] = []
        captured = False

        for idx in range(start_index - 1, max(-1, start_index - max_scan) - 1, -1):
            raw_line = lines[idx]
            stripped = raw_line.strip()

            if not stripped and not captured:
                continue

            if not captured and (stripped.startswith('package ') or stripped.startswith('import ')):
                break

            if not captured and stripped.startswith('@'):
                # 어노테이션은 건너뛰고 계속 위로 올라간다.
                continue

            if not captured and re.fullmatch(r'[\)\}\],]+', stripped):
                # 어노테이션 블록의 닫는 괄호/중괄호만 있는 라인은 건너뛴다.
                continue

            if stripped.startswith('//'):
                return raw_line.strip()

            if stripped.endswith('*/') or stripped.startswith('*/'):
                captured = True
                comment_lines.append(raw_line)
                continue

            if captured:
                comment_lines.append(raw_line)
                if stripped.startswith('/**') or stripped.startswith('/*'):
                    break
            elif stripped.startswith('/**') or stripped.startswith('/*'):
                comment_lines.append(raw_line)
                captured = True
                break
            else:
                if stripped:
                    break

        if not comment_lines:
            return ""

        comment_lines.reverse()
        return '\n'.join(comment_lines)
    
    def extract_class_logical_name(self, java_source: str, class_name: str) -> Optional[str]:
        """클래스의 논리명 추출"""
        try:
            tree = javalang.parse.parse(java_source)
            lines = java_source.split('\n')

            for path, node in tree:
                if isinstance(node, javalang.tree.ClassDeclaration) and node.name == class_name:
                    class_line = (node.position.line - 1) if node.position else -1
                    if class_line < 0:
                        continue

                    comment_block = self._collect_comment_block(lines, class_line)
                    if comment_block:
                        logical_name = self._match_logical_name_from_rules('java_class', comment_block)
                        if logical_name:
                            self.logger.debug(f"클래스 {class_name} 논리명 추출 성공 (규칙 기반): {logical_name}")
                            return logical_name

                        for raw_line in comment_block.split('\n'):
                            stripped = raw_line.strip()
                            if stripped.startswith('//'):
                                stripped = stripped[2:].strip()
                            if stripped.startswith('/**') or stripped.startswith('/*') or stripped.startswith('*/'):
                                continue
                            if stripped.startswith('*'):
                                stripped = stripped[1:].strip()
                            if stripped and not stripped.startswith('@'):
                                self.logger.debug(f"클래스 {class_name} 논리명 추출 성공 (주석 파싱): {stripped}")
                                return stripped

                    self.logger.debug(f"클래스 {class_name} 논리명을 찾을 수 없음")
                    return ""

            return ""

        except Exception as e:
            self.logger.error(f"클래스 논리명 추출 실패: {e}")
            return ""

    def extract_method_logical_name(self, java_source: str, method_name: str) -> Optional[str]:
        """메서드의 논리명 추출"""
        try:
            tree = javalang.parse.parse(java_source)
            lines = java_source.split('\n')

            method_patterns_primary = [
                rf'\b(public|private|protected)\s+(static\s+)?\w+\s+{re.escape(method_name)}\s*\(',
            ]
            method_patterns_secondary = [
                rf'\b{re.escape(method_name)}\s*\(',
                rf'^\s*{re.escape(method_name)}\s*\(',
            ]
            actual_method_line = -1

            for patterns in (method_patterns_primary, method_patterns_secondary):
                for idx, line in enumerate(lines):
                    for pattern in patterns:
                        if re.search(pattern, line):
                            actual_method_line = idx
                            self.logger.debug(f"메서드 {method_name} 패턴 매칭 성공 (라인 {idx + 1}): {line.strip()}")
                            break
                    if actual_method_line != -1:
                        break
                if actual_method_line != -1:
                    break

            if actual_method_line == -1:
                for idx, line in enumerate(lines):
                    if f"{method_name}(" in line and any(kw in line for kw in ['public', 'private', 'protected']):
                        actual_method_line = idx
                        self.logger.debug(f"메서드 {method_name} 문자열 검증 성공 (라인 {idx + 1}): {line.strip()}")
                        break

            if actual_method_line == -1:
                self.logger.warning(f"메서드 {method_name} 선언을 찾을 수 없음")
                return ""

            self.logger.debug(f"메서드 {method_name} 실제 위치: 라인 {actual_method_line + 1}")

            comment_block = self._collect_comment_block(lines, actual_method_line)
            if comment_block:
                logical_name = self._match_logical_name_from_rules('java_method', comment_block)
                if logical_name:
                    self.logger.debug(f"메서드 {method_name} 논리명 추출 성공 (규칙 기반): {logical_name}")
                    return logical_name

                for raw_line in comment_block.split('\n'):
                    stripped = raw_line.strip()
                    if stripped.startswith('//'):
                        stripped = stripped[2:].strip()
                    if stripped.startswith('/**') or stripped.startswith('/*') or stripped.startswith('*/'):
                        continue
                    if stripped.startswith('*'):
                        stripped = stripped[1:].strip()
                    if stripped and not stripped.startswith('@'):
                        self.logger.debug(f"메서드 {method_name} 논리명 추출 성공 (주석 파싱): {stripped}")
                        return stripped

            self.logger.debug(f"메서드 {method_name} 논리명을 찾을 수 없음")
            return ""

        except Exception as e:
            self.logger.error(f"메서드 논리명 추출 실패: {e}")
            return ""
    
    def extract_field_logical_name(self, java_source: str, field_name: str) -> Optional[str]:
        """필드의 논리명 추출"""
        try:
            tree = javalang.parse.parse(java_source)
            lines = java_source.split('\n')
            
            # 필드 선언을 찾기 위한 패턴들
            field_patterns = [
                rf'\b(public|private|protected)?\s*(static)?\s*(final)?\s*\w+\s+{re.escape(field_name)}\s*[;=]',
                rf'\b{re.escape(field_name)}\s*[;=]',
                rf'^\s*{re.escape(field_name)}\s*[;=]',
                rf'{re.escape(field_name)}\s*[;=]'  # 가장 단순한 패턴
            ]
            actual_field_line = -1
            
            for i, line in enumerate(lines):
                for pattern in field_patterns:
                    if re.search(pattern, line):
                        actual_field_line = i
                        self.logger.debug(f"필드 {field_name} 패턴 매칭 성공 (라인 {i + 1}): {line.strip()}")
                        break
                if actual_field_line != -1:
                    break
            
            # 패턴 매칭이 실패한 경우, 단순 문자열 검색으로 시도
            if actual_field_line == -1:
                for i, line in enumerate(lines):
                    if f"{field_name}" in line and (";" in line or "=" in line) and ("public" in line or "private" in line or "protected" in line):
                        actual_field_line = i
                        self.logger.debug(f"필드 {field_name} 문자열 검색 성공 (라인 {i + 1}): {line.strip()}")
                        break
            
            if actual_field_line == -1:
                self.logger.warning(f"필드 {field_name} 선언을 찾을 수 없음")
                return ""
            
            self.logger.debug(f"필드 {field_name} 실제 위치: 라인 {actual_field_line + 1}")
            comment_block = self._collect_comment_block(lines, actual_field_line)
            if comment_block:
                logical_name = self._match_logical_name_from_rules('java_field', comment_block)
                if logical_name:
                    self.logger.debug(f"필드 {field_name} 논리명 추출 성공 (규칙 기반): {logical_name}")
                    return logical_name
            
            # 필드 선언 위의 주석 검색 (역순으로 가장 가까운 주석 찾기)
            for i in range(actual_field_line - 1, max(0, actual_field_line - 20) - 1, -1):
                line = lines[i].strip()
                
                # 클래스 선언이나 다른 필드 선언을 만나면 검색 중단
                if ('class ' in line and line.endswith('{')) or (line.endswith(';') and not line.startswith('*')):
                    self.logger.debug(f"검색 중단 (라인 {i + 1}): {line}")
                    break
                
                if line.startswith('/**'):
                    self.logger.debug(f"주석 시작 발견 (라인 {i + 1}): {line}")
                    # 여러 줄 주석 시작
                    logical_name = ""
                    for j in range(i + 1, min(len(lines), i + 20)):
                        comment_line = lines[j].strip()
                        self.logger.debug(f"주석 라인 {j + 1}: {comment_line}")
                        if comment_line.strip().startswith('*') and not comment_line.strip().startswith('*/'):
                            # 주석 내용에서 논리명 추출
                            content = comment_line.strip()[1:].strip()
                            self.logger.debug(f"주석 내용 분석: '{content}' (어노테이션 여부: {content.startswith('@')})")
                            if content and not content.startswith('@'):  # 어노테이션이 아닌 경우만
                                logical_name = content
                                self.logger.debug(f"논리명 추출: {logical_name}")
                                break
                        elif comment_line.endswith('*/'):
                            break
                    if logical_name:
                        self.logger.debug(f"필드 {field_name} 논리명 추출 성공: {logical_name}")
                        return logical_name
                elif line.startswith('/**') and line.endswith('*/'):
                    # 한 줄 주석에서 논리명 추출
                    match = re.search(r'\*\s*(.+)', line)
                    if match:
                        content = match.group(1).strip()
                        if content and not content.startswith('@'):  # 어노테이션이 아닌 경우만
                            self.logger.debug(f"필드 {field_name} 논리명 추출 성공 (한 줄): {content}")
                            return content
            
            self.logger.debug(f"필드 {field_name} 논리명을 찾을 수 없음")
            return ""
            
        except Exception as e:
            self.logger.error(f"필드 논리명 추출 실패: {e}")
            return ""


class MyBatisXmlLogicalNameExtractor(LogicalNameExtractor):
    """MyBatis XML 파일 전용 논리명 추출기"""

    def __init__(self, project_name: str, rules_directory: str = "rules"):
        super().__init__(project_name, rules_directory)
    
    def extract_mapper_logical_name(self, xml_source: str, mapper_name: str) -> Optional[str]:
        """MyBatis Mapper의 논리명 추출"""
        try:
            # XML 파싱
            root = ET.fromstring(xml_source)
            
            # mapper 태그 찾기
            mapper_tag = root.find('.//mapper')
            if mapper_tag is not None:
                # mapper 태그 위의 주석 찾기
                lines = xml_source.split('\n')
                
                # mapper 태그의 라인 번호 찾기
                mapper_line = -1
                for i, line in enumerate(lines):
                    if '<mapper' in line and mapper_name in line:
                        mapper_line = i
                        break
                
                if mapper_line > 0:
                    # mapper 태그 위의 주석 검색
                    for i in range(max(0, mapper_line - 10), mapper_line):
                        line = lines[i].strip()
                        if line.startswith('<!--') and line.endswith('-->'):
                            logical_name = self._match_logical_name_from_rules('mybatis_mapper', line)
                            if not logical_name:
                                logical_name = line[4:-3].strip()
                            if logical_name:
                                return logical_name
            
            return ""
            
        except Exception as e:
            self.logger.error(f"Mapper 논리명 추출 실패: {e}")
            return ""
    
    def extract_sql_logical_name(self, xml_source: str, sql_id: str) -> Optional[str]:
        """SQL 문의 논리명 추출"""
        try:
            lines = xml_source.split('\n')
            
            # SQL 태그 찾기
            sql_line = -1
            for i, line in enumerate(lines):
                if f'id="{sql_id}"' in line and any(tag in line for tag in ['<select', '<insert', '<update', '<delete']):
                    sql_line = i
                    break
            
            if sql_line > 0:
                # SQL 태그 위의 주석 검색 (역순으로 가장 가까운 주석 찾기)
                for i in range(sql_line - 1, max(0, sql_line - 5) - 1, -1):
                    line = lines[i].strip()
                    
                    # 다른 SQL 태그를 만나면 검색 중단
                    if any(tag in line for tag in ['</select>', '</insert>', '</update>', '</delete>']):
                        self.logger.debug(f"검색 중단 (라인 {i + 1}): {line}")
                        break
                    
                    if line.startswith('<!--') and line.endswith('-->'):
                        logical_name = self._match_logical_name_from_rules('xml_sql', line)
                        if not logical_name:
                            logical_name = line[4:-3].strip()
                        if logical_name:
                            return logical_name
            
            return ""
            
        except Exception as e:
            self.logger.error(f"SQL 논리명 추출 실패: {e}")
            return ""


class LogicalNameExtractorFactory:
    """논리명 추출기 팩토리"""

    @staticmethod
    def create_extractor(project_name: str, file_type: str, rules_directory: str = "rules"):
        """프로젝트와 파일 타입에 따라 적절한 추출기 생성"""
        
        if file_type == 'java':
            return JavaLogicalNameExtractor(project_name, rules_directory)
        elif file_type == 'mybatis_xml':
            return MyBatisXmlLogicalNameExtractor(project_name, rules_directory)
        else:
            raise ValueError(f"지원하지 않는 파일 타입: {file_type}")


def process_java_file_with_rule001(file_path: str, project_name: str, graph_db: GraphDB):
    """Rule001을 사용하여 Java 파일 처리"""
    extractor = LogicalNameExtractorFactory.create_extractor(project_name, 'java')
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            java_source = f.read()
        
        # 클래스 논리명 추출 및 업데이트
        tree = javalang.parse.parse(java_source)
        for path, node in tree:
            if isinstance(node, javalang.tree.ClassDeclaration):
                class_name = node.name
                logical_name = extractor.extract_class_logical_name(java_source, class_name)
                
                if logical_name:
                    extractor.update_class_logical_name(graph_db, class_name, project_name, logical_name)
                
                # 메서드 논리명 추출 및 업데이트
                for method_node in node.methods:
                    if isinstance(method_node, javalang.tree.MethodDeclaration):
                        method_name = method_node.name
                        method_logical_name = extractor.extract_method_logical_name(java_source, method_name)
                        
                        if method_logical_name:
                            extractor.update_method_logical_name(graph_db, class_name, method_name, project_name, method_logical_name)
        
        return True
        
    except Exception as e:
        extractor.logger.error(f"Java 파일 처리 실패: {file_path}, {e}")
        return False


def process_mybatis_xml_with_rule001(file_path: str, project_name: str, graph_db: GraphDB):
    """Rule001을 사용하여 MyBatis XML 파일 처리"""
    extractor = LogicalNameExtractorFactory.create_extractor(project_name, 'mybatis_xml')
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            xml_source = f.read()
        
        # Mapper 논리명 추출 및 업데이트
        root = ET.fromstring(xml_source)
        mapper_tag = root.find('.//mapper')
        
        if mapper_tag is not None:
            namespace = mapper_tag.get('namespace', '')
            if namespace:
                mapper_name = namespace.split('.')[-1]  # 패키지명에서 클래스명만 추출
                logical_name = extractor.extract_mapper_logical_name(xml_source, mapper_name)
                
                if logical_name:
                    # MyBatisMapper 노드의 논리명 업데이트
                    with graph_db._driver.session() as session:
                        query = """
                        MATCH (m:MyBatisMapper {name: $mapper_name, project_name: $project_name})
                        SET m.logical_name = $logical_name
                        RETURN m.name as mapper_name
                        """
                        result = session.run(query, 
                                          mapper_name=mapper_name,
                                          project_name=project_name, 
                                          logical_name=logical_name)
                        
                        if result.single():
                            extractor.logger.info(f"Mapper 논리명 업데이트 완료: {mapper_name} -> {logical_name}")
        
        # SQL 문 논리명 추출 및 업데이트
        sql_tags = ['select', 'insert', 'update', 'delete']
        for sql_tag in sql_tags:
            for element in root.findall(f'.//{sql_tag}'):
                sql_id = element.get('id')
                if sql_id:
                    logical_name = extractor.extract_sql_logical_name(xml_source, sql_id)
                    
                    if logical_name:
                        # SqlStatement 노드의 논리명 업데이트
                        with graph_db._driver.session() as session:
                            query = """
                            MATCH (s:SqlStatement {id: $sql_id, project_name: $project_name})
                            SET s.logical_name = $logical_name
                            RETURN s.id as sql_id
                            """
                            result = session.run(query, 
                                              sql_id=sql_id,
                                              project_name=project_name, 
                                              logical_name=logical_name)
                            
                            if result.single():
                                extractor.logger.info(f"SQL 논리명 업데이트 완료: {sql_id} -> {logical_name}")
        
        return True
        
    except Exception as e:
        extractor.logger.error(f"MyBatis XML 파일 처리 실패: {file_path}, {e}")
        return False


def extract_mapper_logical_name_from_xml_content(xml_content: str, namespace: str) -> str:
    """XML 내용에서 Mapper 논리명 추출"""
    lines = xml_content.split('\n')
    
    # <mapper> 태그 찾기
    mapper_line = -1
    for i, line in enumerate(lines):
        if '<mapper' in line and namespace in line:
            mapper_line = i
            break
    
    if mapper_line > 0:
        # mapper 태그 위의 주석 검색
        for i in range(max(0, mapper_line - 10), mapper_line):
            line = lines[i].strip()
            if line.startswith('<!--') and line.endswith('-->'):
                logical_name = line[4:-3].strip()
                if logical_name:
                    return logical_name
    
    return ""


def extract_sql_logical_name_from_xml_content(xml_content: str, sql_id: str) -> str:
    """XML 내용에서 SQL 논리명 추출"""
    lines = xml_content.split('\n')
    
    # SQL 태그 찾기
    sql_line = -1
    for i, line in enumerate(lines):
        if f'id="{sql_id}"' in line and any(tag in line for tag in ['<select', '<insert', '<update', '<delete']):
            sql_line = i
            break
    
    if sql_line > 0:
        # SQL 태그 위의 주석 검색
        for i in range(max(0, sql_line - 5), sql_line):
            line = lines[i].strip()
            if line.startswith('<!--') and line.endswith('-->'):
                logical_name = line[4:-3].strip()
                if logical_name:
                    return logical_name
    
    return ""


def extract_java_class_logical_name(java_content: str, class_name: str, project_name: str) -> Optional[str]:
    """Java 소스코드에서 클래스 논리명 추출 (개선된 버전 - 캐시된 인스턴스 재사용)"""
    try:
        # 캐시된 인스턴스 재사용
        extractor = JavaLogicalNameExtractor(project_name)
        return extractor.extract_class_logical_name(java_content, class_name)
    except Exception:
        return None


def extract_java_method_logical_name(java_content: str, method_name: str, project_name: str) -> Optional[str]:
    """Java 소스코드에서 메서드 논리명 추출 (개선된 버전 - 캐시된 인스턴스 재사용)"""
    try:
        # 캐시된 인스턴스 재사용
        extractor = JavaLogicalNameExtractor(project_name)
        return extractor.extract_method_logical_name(java_content, method_name)
    except Exception:
        return None


def extract_java_field_logical_name(java_content: str, field_name: str, project_name: str) -> Optional[str]:
    """Java 소스코드에서 필드 논리명 추출 (개선된 버전 - 캐시된 인스턴스 재사용)"""
    try:
        # 캐시된 인스턴스 재사용
        extractor = JavaLogicalNameExtractor(project_name)
        return extractor.extract_field_logical_name(java_content, field_name)
    except Exception:
        return None


def process_project_with_custom_rules(project_name: str, file_path: str, file_type: str, graph_db: GraphDB):
    """프로젝트별 커스텀 규칙으로 파일 처리"""
    
    try:
        if file_type == 'java':
            return process_java_file_with_rule001(file_path, project_name, graph_db)
        elif file_type == 'mybatis_xml':
            return process_mybatis_xml_with_rule001(file_path, project_name, graph_db)
        else:
            logger = get_logger(__name__)
            logger.warning(f"지원하지 않는 파일 타입: {file_type}")
            return False
            
    except Exception as e:
        logger = get_logger(__name__)
        logger.error(f"파일 처리 실패: {file_path}, {e}")
        return False


def get_file_type(file_path: str) -> str:
    """파일 경로에서 파일 타입 결정"""
    file_extension = Path(file_path).suffix.lower()
    
    if file_extension == '.java':
        return 'java'
    elif file_extension == '.xml':
        # MyBatis XML 파일인지 확인
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if '<mapper' in content or any(tag in content for tag in ['<select', '<insert', '<update', '<delete']):
                    return 'mybatis_xml'
        except:
            pass
        return 'xml'
    else:
        return 'unknown'
