"""
Java Parser Addon for Rule001 - Logical Name Extraction
프로젝트별 논리명 추출 규칙을 실시간으로 해석하여 Java 객체 분석 시 적용
"""

import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, Dict, Any, List
import javalang

from csa.models.graph_entities import Class, Method
from csa.services.graph_db import GraphDB
from csa.utils.logger import get_logger


class LogicalNameExtractor:
    """프로젝트별 논리명 추출기 - 기본 클래스"""
    
    _instances = {}  # 프로젝트별 인스턴스 캐시
    _rules_cache = {}  # 규칙 파일 캐시
    
    def __new__(cls, project_name: str, rules_directory: str = "csa/rules"):
        # 프로젝트별로 인스턴스를 캐시하여 재사용
        cache_key = f"{project_name}_{rules_directory}"
        if cache_key not in cls._instances:
            instance = super().__new__(cls)
            cls._instances[cache_key] = instance
        return cls._instances[cache_key]
    
    def __init__(self, project_name: str, rules_directory: str = "csa/rules"):
        # 이미 초기화된 인스턴스는 재초기화하지 않음
        if hasattr(self, '_initialized'):
            return
            
        self.project_name = project_name
        self.rules_directory = rules_directory
        self.logger = get_logger(__name__)
        self.rules = self._load_project_rules()
        self._initialized = True
    
    def _load_project_rules(self) -> Dict[str, Any]:
        """프로젝트별 규칙 파일 로드 (캐싱 적용)"""
        # 프로젝트별 규칙 파일 경로 결정
        project_rule_file = f"{self.rules_directory}/{self.project_name}_logical_name_rules.md"
        default_rule_file = f"{self.rules_directory}/rule001_extraction_logical_name.md"
        
        rule_file_path = project_rule_file if os.path.exists(project_rule_file) else default_rule_file
        
        # 규칙 파일 캐시 확인
        if rule_file_path in self._rules_cache:
            self.logger.debug(f"프로젝트 {self.project_name} 규칙 파일 캐시 사용: {rule_file_path}")
            return self._rules_cache[rule_file_path]
        
        try:
            with open(rule_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 규칙 해석 로직
            rules = self._parse_rules_content(content)
            
            # 규칙 파일 캐시에 저장
            self._rules_cache[rule_file_path] = rules
            
            self.logger.info(f"프로젝트 {self.project_name} 규칙 파일 로드: {rule_file_path}")
            return rules
            
        except Exception as e:
            self.logger.error(f"규칙 파일 로드 실패: {e}")
            return {}
    
    def _parse_rules_content(self, content: str) -> Dict[str, Any]:
        """규칙 내용을 파싱하여 구조화된 데이터로 변환"""
        rules = {
            'java_class': {
                'pattern': r'/\*\*\s*\n\s*\*\s*(.+?)\s*\n\s*\*/',
                'description': 'Class 선언 위치의 상단에 코멘트로 기술'
            },
            'java_method': {
                'pattern': r'/\*\*\s*\n\s*\*\s*(.+?)\s*\n\s*\*/',
                'description': 'Method 선언 위치의 상단에 코멘트로 기술'
            },
            'mybatis_mapper': {
                'pattern': r'<!--\s*(.+?)\s*-->',
                'description': 'mapper 태그의 namespace 속성 위의 주석'
            },
            'xml_sql': {
                'pattern': r'<!--\s*(.+?)\s*-->',
                'description': '각 SQL 태그 위의 주석'
            }
        }
        
        # 마크다운 내용을 파싱하여 규칙 추출
        lines = content.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            
            # 섹션 헤더 파싱
            if line.startswith('## 1. Class'):
                current_section = 'java_class'
            elif line.startswith('## 2. Method'):
                current_section = 'java_method'
            elif line.startswith('## 3. MyBatis'):
                current_section = 'mybatis_mapper'
            elif line.startswith('## 4. SQL'):
                current_section = 'xml_sql'
            
            # 패턴 추출
            if line.startswith('- **논리명(logical name) 위치**:'):
                if current_section and current_section in rules:
                    rules[current_section]['description'] = line.split(':', 1)[1].strip()
            
            # 예시 코드에서 패턴 추출
            if line.startswith('```java') and current_section:
                # 다음 라인들에서 패턴 추출
                continue
        
        return rules
    
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
    
    def __init__(self, project_name: str, rules_directory: str = "csa/rules"):
        super().__init__(project_name, rules_directory)
    
    def extract_class_logical_name(self, java_source: str, class_name: str) -> Optional[str]:
        """클래스의 논리명 추출"""
        try:
            # javalang으로 파싱
            tree = javalang.parse.parse(java_source)
            
            for path, node in tree:
                if isinstance(node, javalang.tree.ClassDeclaration) and node.name == class_name:
                    # 클래스 선언 위의 주석 찾기
                    lines = java_source.split('\n')
                    class_line = node.position.line
                    
                    # 클래스 선언 위의 주석 검색 (import/package 기반 스마트 검색)
                    for i in range(class_line - 1, max(0, class_line - 30) - 1, -1):
                        line = lines[i].strip()
                        
                        # import문이나 package문을 만나면 검색 중단 (1순위, 2순위)
                        if line.startswith('import ') or line.startswith('package '):
                            self.logger.debug(f"검색 중단 - import/package 문 (라인 {i + 1}): {line}")
                            break
                        
                        # 다른 클래스 선언을 만나면 검색 중단
                        if 'class ' in line and '{' in line and i != class_line - 1:
                            self.logger.debug(f"검색 중단 - 다른 클래스 선언 (라인 {i + 1}): {line}")
                            break
                        
                        if line.startswith('/**') and line.endswith('*/'):
                            # 한 줄 주석에서 논리명 추출
                            match = re.search(r'\*\s*(.+)', line)
                            if match:
                                logical_name = match.group(1).strip()
                                self.logger.debug(f"클래스 {class_name} 논리명 추출 성공 (한 줄): {logical_name}")
                                return logical_name
                        elif line.startswith('/**'):
                            # 여러 줄 주석 시작
                            logical_name = ""
                            for j in range(i + 1, min(len(lines), i + 10)):
                                comment_line = lines[j].strip()
                                if comment_line.startswith('*') and not comment_line.startswith('*/'):
                                    logical_name = comment_line[1:].strip()
                                    break
                                elif comment_line.endswith('*/'):
                                    break
                            if logical_name:
                                self.logger.debug(f"클래스 {class_name} 논리명 추출 성공 (여러 줄): {logical_name}")
                                return logical_name
            
            return None
            
        except Exception as e:
            self.logger.error(f"클래스 논리명 추출 실패: {e}")
            return None
    
    def extract_method_logical_name(self, java_source: str, method_name: str) -> Optional[str]:
        """메서드의 논리명 추출"""
        try:
            tree = javalang.parse.parse(java_source)
            lines = java_source.split('\n')
            
            # 먼저 정규식으로 메서드 선언을 찾아서 실제 라인 번호 확인
            # 더 유연한 패턴으로 메서드 선언 찾기
            method_patterns = [
                rf'\b(public|private|protected)?\s*(static)?\s*\w+\s+{re.escape(method_name)}\s*\(',
                rf'\b{re.escape(method_name)}\s*\(',
                rf'^\s*{re.escape(method_name)}\s*\(',
                rf'{re.escape(method_name)}\s*\('  # 가장 단순한 패턴
            ]
            actual_method_line = -1
            
            for i, line in enumerate(lines):
                for pattern in method_patterns:
                    if re.search(pattern, line):
                        actual_method_line = i
                        self.logger.debug(f"메서드 {method_name} 패턴 매칭 성공 (라인 {i + 1}): {line.strip()}")
                        break
                if actual_method_line != -1:
                    break
            
            # 패턴 매칭이 실패한 경우, 단순 문자열 검색으로 시도
            if actual_method_line == -1:
                for i, line in enumerate(lines):
                    if f"{method_name}(" in line and ("public" in line or "private" in line or "protected" in line):
                        actual_method_line = i
                        self.logger.debug(f"메서드 {method_name} 문자열 검색 성공 (라인 {i + 1}): {line.strip()}")
                        break
            
            if actual_method_line == -1:
                self.logger.warning(f"메서드 {method_name} 선언을 찾을 수 없음")
                return None
            
            self.logger.debug(f"메서드 {method_name} 실제 위치: 라인 {actual_method_line + 1}")
            
            # 메서드 선언 위의 주석 검색 (역순으로 가장 가까운 주석 찾기)
            for i in range(actual_method_line - 1, max(0, actual_method_line - 20) - 1, -1):
                line = lines[i].strip()
                
                # 다른 메서드 선언이나 필드 선언을 만나면 검색 중단
                if (line.endswith('}') and ('public' in line or 'private' in line or 'protected' in line)) or (line.endswith(';') and not line.startswith('*')):
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
                        self.logger.debug(f"메서드 {method_name} 논리명 추출 성공: {logical_name}")
                        return logical_name
                elif line.startswith('/**') and line.endswith('*/'):
                    # 한 줄 주석에서 논리명 추출
                    match = re.search(r'\*\s*(.+)', line)
                    if match:
                        content = match.group(1).strip()
                        if content and not content.startswith('@'):  # 어노테이션이 아닌 경우만
                            self.logger.debug(f"메서드 {method_name} 논리명 추출 성공 (한 줄): {content}")
                            return content
            
            self.logger.debug(f"메서드 {method_name} 논리명을 찾을 수 없음")
            return None
            
        except Exception as e:
            self.logger.error(f"메서드 논리명 추출 실패: {e}")
            return None
    
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
                return None
            
            self.logger.debug(f"필드 {field_name} 실제 위치: 라인 {actual_field_line + 1}")
            
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
            return None
            
        except Exception as e:
            self.logger.error(f"필드 논리명 추출 실패: {e}")
            return None


class MyBatisXmlLogicalNameExtractor(LogicalNameExtractor):
    """MyBatis XML 파일 전용 논리명 추출기"""
    
    def __init__(self, project_name: str, rules_directory: str = "csa/rules"):
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
                            # 주석에서 논리명 추출
                            logical_name = line[4:-3].strip()
                            if logical_name:
                                return logical_name
            
            return None
            
        except Exception as e:
            self.logger.error(f"Mapper 논리명 추출 실패: {e}")
            return None
    
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
                        logical_name = line[4:-3].strip()
                        if logical_name:
                            return logical_name
            
            return None
            
        except Exception as e:
            self.logger.error(f"SQL 논리명 추출 실패: {e}")
            return None


class LogicalNameExtractorFactory:
    """논리명 추출기 팩토리"""
    
    @staticmethod
    def create_extractor(project_name: str, file_type: str, rules_directory: str = "csa/rules"):
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
    """Java 소스코드에서 클래스 논리명 추출 (None 반환 가능)
    
    Args:
        java_content: Java 소스 코드
        class_name: 클래스 이름
        project_name: 프로젝트 이름
        
    Returns:
        논리명 또는 None (추출 실패 시)
    """
    try:
        extractor = JavaLogicalNameExtractor(project_name)
        return extractor.extract_class_logical_name(java_content, class_name)
    except Exception:
        return None


def extract_java_method_logical_name(java_content: str, method_name: str, project_name: str) -> Optional[str]:
    """Java 소스코드에서 메서드 논리명 추출 (None 반환 가능)
    
    Args:
        java_content: Java 소스 코드
        method_name: 메서드 이름
        project_name: 프로젝트 이름
        
    Returns:
        논리명 또는 None (추출 실패 시)
    """
    try:
        extractor = JavaLogicalNameExtractor(project_name)
        return extractor.extract_method_logical_name(java_content, method_name)
    except Exception:
        return None


def extract_java_field_logical_name(java_content: str, field_name: str, project_name: str) -> Optional[str]:
    """Java 소스코드에서 필드 논리명 추출 (None 반환 가능)
    
    Args:
        java_content: Java 소스 코드
        field_name: 필드 이름
        project_name: 프로젝트 이름
        
    Returns:
        논리명 또는 None (추출 실패 시)
    """
    try:
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
