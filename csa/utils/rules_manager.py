"""
규칙 파일 중앙 관리자
애플리케이션 시작 시 모든 규칙 파일을 한 번만 로드하고 전역적으로 재사용
"""

import os
from typing import Dict, Any, Optional
from csa.utils.logger import get_logger


class RulesManager:
    """규칙 파일 중앙 관리자 - 싱글톤 패턴"""
    
    _instance: Optional['RulesManager'] = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return

        self._logger = None  # 지연 초기화: 첫 사용 시 생성
        self.rules_directory = "rules"
        self._logical_name_rules: Dict[str, Dict[str, Any]] = {}
        self._description_rules: Dict[str, Dict[str, Any]] = {}
        self._rules_loaded = False  # 규칙 로드 여부 플래그
        self._initialized = True

        # 규칙은 첫 사용 시 지연 로드

    @property
    def logger(self):
        """지연 초기화된 로거 프로퍼티"""
        if self._logger is None:
            self._logger = get_logger(__name__)
        return self._logger

    def _ensure_rules_loaded(self):
        """규칙이 로드되지 않았으면 로드"""
        if not self._rules_loaded:
            self._load_all_rules()
            self._rules_loaded = True

    def _load_all_rules(self):
        """모든 규칙 파일을 한 번에 로드"""
        self.logger.info("규칙 파일들을 로드 중...")
        
        # 논리명 추출 규칙들 로드
        self._load_logical_name_rules()
        
        # Description 추출 규칙들 로드  
        self._load_description_rules()
        
        self.logger.info(f"규칙 로드 완료 - 논리명: {len(self._logical_name_rules)}개, Description: {len(self._description_rules)}개")
    
    def _load_logical_name_rules(self):
        """논리명 추출 규칙들 로드"""
        # 기본 규칙 파일
        default_rule_file = f"{self.rules_directory}/rule001_extraction_logical_name.md"
        if os.path.exists(default_rule_file):
            self._logical_name_rules["default"] = self._parse_logical_name_rules(default_rule_file)
        
        # 프로젝트별 규칙 파일들 찾기
        if os.path.exists(self.rules_directory):
            for filename in os.listdir(self.rules_directory):
                if filename.endswith("_logical_name_rules.md"):
                    project_name = filename.replace("_logical_name_rules.md", "")
                    rule_file = f"{self.rules_directory}/{filename}"
                    self._logical_name_rules[project_name] = self._parse_logical_name_rules(rule_file)
    
    def _load_description_rules(self):
        """Description 추출 규칙들 로드"""
        rule_file = f"{self.rules_directory}/rule002_extraction_description.md"
        if os.path.exists(rule_file):
            self._description_rules["default"] = self._parse_description_rules(rule_file)
    
    def _parse_logical_name_rules(self, rule_file: str) -> Dict[str, Any]:
        """논리명 규칙 파일 파싱 - 순환 import 방지를 위해 내부 구현"""
        try:
            with open(rule_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 기본 템플릿 정의
            DEFAULT_RULE_TEMPLATES = {
                "java_class": "/**\\n * {logical_name}\\n */",
                "java_method": "/**\\n * {logical_name}\\n */",
                "java_field": "/**\\n * {logical_name}\\n */",
                "mybatis_mapper": "<!-- {logical_name} -->",
                "xml_sql": "<!-- {logical_name} -->",
            }
            
            # 규칙 파싱 로직
            rules = {}
            for key, template in DEFAULT_RULE_TEMPLATES.items():
                rules[key] = {
                    "template": template,
                    "pattern": self._convert_template_to_pattern(template),
                    "description": "",
                }

            current_section = None
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

            self.logger.debug(f"논리명 규칙 로드: {rule_file}")
            return rules
            
        except Exception as e:
            self.logger.error(f"논리명 규칙 파일 로드 실패: {rule_file}, {e}")
            return {}
    
    def _parse_description_rules(self, rule_file: str) -> Dict[str, Any]:
        """Description 규칙 파일 파싱 - 순환 import 방지를 위해 내부 구현"""
        try:
            with open(rule_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 현재는 고정 규칙 사용
            rules = {
                "class": {
                    "annotation": "Tag",
                    "parameter": "description",
                    "description": "Class의 @Tag annotation의 description 파라미터에서 추출"
                },
                "method": {
                    "annotation": "Operation",
                    "parameter": "description",
                    "description": "Method의 @Operation annotation의 description 파라미터에서 추출"
                }
            }
            
            self.logger.debug(f"Description 규칙 로드: {rule_file}")
            return rules
            
        except Exception as e:
            self.logger.error(f"Description 규칙 파일 로드 실패: {rule_file}, {e}")
            return {}
    
    def _extract_template_from_line(self, line: str) -> str:
        """라인에서 {logical_name} 플레이스홀더가 포함된 템플릿을 추출"""
        import re
        
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
    
    def _convert_template_to_pattern(self, template: str) -> str:
        """템플릿 문자열을 정규식 패턴으로 변환"""
        import re
        
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
    
    def get_logical_name_rules(self, project_name: str) -> Dict[str, Any]:
        """프로젝트별 논리명 규칙 반환"""
        self._ensure_rules_loaded()  # 첫 사용 시 로드
        return self._logical_name_rules.get(project_name, self._logical_name_rules.get("default", {}))

    def get_description_rules(self, project_name: str) -> Dict[str, Any]:
        """프로젝트별 Description 규칙 반환"""
        self._ensure_rules_loaded()  # 첫 사용 시 로드
        return self._description_rules.get(project_name, self._description_rules.get("default", {}))

    def reload_rules(self):
        """규칙 파일들 재로드 (개발 중 규칙 변경 시 사용)"""
        self.logger.info("규칙 파일들 재로드 중...")
        self._logical_name_rules.clear()
        self._description_rules.clear()
        self._rules_loaded = False
        self._ensure_rules_loaded()  # 즉시 재로드


# 전역 인스턴스
rules_manager = RulesManager()
