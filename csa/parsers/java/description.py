"""
Java Parser Addon for Rule002 - Description Extraction
프로젝트별 description 추출 규칙을 실시간으로 해석하여 Java 객체 분석 시 적용
"""

import os
import re
from pathlib import Path
from typing import Optional, Dict, Any, List
from csa.vendor import javalang

from csa.models.graph_entities import Class, Method, Annotation
from csa.services.graph_db import GraphDB
from csa.utils.logger import get_logger


class DescriptionExtractor:
    """Description 추출기 - 개선된 버전 (전역 규칙 매니저 사용)"""
    
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
        self.rules = rules_manager.get_description_rules(project_name)
        
        self._initialized = True


    def _parse_rules_content(self, content: str) -> Dict[str, Any]:
        """규칙 내용 파싱 - 현재는 고정 규칙 사용"""
        return {
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

    def extract_class_description(self, annotations: List[Annotation]) -> str:
        """클래스의 description 추출

        Args:
            annotations: 클래스의 Annotation 객체 리스트

        Returns:
            description 문자열 (추출 실패 시 빈 문자열)
        """
        if not annotations:
            return ""

        # @Tag annotation의 description 파라미터 찾기
        for annotation in annotations:
            if annotation.name == "Tag" or annotation.name.endswith(".Tag"):
                if "description" in annotation.parameters:
                    desc = annotation.parameters["description"]
                    # 따옴표 제거
                    desc = desc.strip('"').strip("'")
                    self.logger.debug(f"클래스 description 추출 성공: {desc}")
                    return desc

        self.logger.debug("클래스 description를 찾을 수 없음")
        return ""

    def extract_method_description(self, annotations: List[Annotation]) -> str:
        """메서드의 description 추출

        Args:
            annotations: 메서드의 Annotation 객체 리스트

        Returns:
            description 문자열 (추출 실패 시 빈 문자열)
        """
        if not annotations:
            return ""

        # @Operation annotation의 description 파라미터 찾기
        for annotation in annotations:
            if annotation.name == "Operation" or annotation.name.endswith(".Operation"):
                if "description" in annotation.parameters:
                    desc = annotation.parameters["description"]
                    # 따옴표 제거
                    desc = desc.strip('"').strip("'")
                    self.logger.debug(f"메서드 description 추출 성공: {desc}")
                    return desc

        self.logger.debug("메서드 description를 찾을 수 없음")
        return ""

    def update_class_description(self, graph_db: GraphDB, class_name: str, project_name: str, description: str):
        """클래스의 description을 DB에 업데이트"""
        try:
            with graph_db._driver.session() as session:
                query = """
                MATCH (c:Class {name: $class_name, project_name: $project_name})
                SET c.description = $description
                RETURN c.name as class_name
                """
                result = session.run(query,
                                  class_name=class_name,
                                  project_name=project_name,
                                  description=description)

                if result.single():
                    self.logger.info(f"클래스 description 업데이트 완료: {class_name} -> {description}")
                    return True
                else:
                    self.logger.warning(f"클래스 찾을 수 없음: {class_name}")
                    return False

        except Exception as e:
            self.logger.error(f"클래스 description 업데이트 실패: {e}")
            return False

    def update_method_description(self, graph_db: GraphDB, class_name: str, method_name: str, project_name: str, description: str):
        """메서드의 description을 DB에 업데이트"""
        try:
            with graph_db._driver.session() as session:
                query = """
                MATCH (m:Method {name: $method_name, class_name: $class_name, project_name: $project_name})
                SET m.description = $description
                RETURN m.name as method_name
                """
                result = session.run(query,
                                  method_name=method_name,
                                  class_name=class_name,
                                  project_name=project_name,
                                  description=description)

                if result.single():
                    self.logger.info(f"메서드 description 업데이트 완료: {class_name}.{method_name} -> {description}")
                    return True
                else:
                    self.logger.warning(f"메서드 찾을 수 없음: {class_name}.{method_name}")
                    return False

        except Exception as e:
            self.logger.error(f"메서드 description 업데이트 실패: {e}")
            return False


class JavaDescriptionExtractor(DescriptionExtractor):
    """Java 파일 전용 description 추출기"""

    def __init__(self, project_name: str, rules_directory: str = "rules"):
        super().__init__(project_name, rules_directory)


def extract_java_class_description(annotations: List[Annotation], project_name: str) -> str:
    """Java 클래스의 description 추출 (개선된 버전 - 캐시된 인스턴스 재사용)

    Args:
        annotations: 클래스의 Annotation 객체 리스트
        project_name: 프로젝트 이름

    Returns:
        description 또는 빈 문자열
    """
    try:
        # 캐시된 인스턴스 재사용
        extractor = JavaDescriptionExtractor(project_name)
        return extractor.extract_class_description(annotations)
    except Exception:
        return ""


def extract_java_method_description(annotations: List[Annotation], project_name: str) -> str:
    """Java 메서드의 description 추출 (개선된 버전 - 캐시된 인스턴스 재사용)

    Args:
        annotations: 메서드의 Annotation 객체 리스트
        project_name: 프로젝트 이름

    Returns:
        description 또는 빈 문자열
    """
    try:
        # 캐시된 인스턴스 재사용
        extractor = JavaDescriptionExtractor(project_name)
        return extractor.extract_method_description(annotations)
    except Exception:
        return ""


def process_java_file_with_rule002(file_path: str, project_name: str, graph_db: GraphDB):
    """Rule002를 사용하여 Java 파일의 description 추출 및 업데이트"""
    extractor = JavaDescriptionExtractor(project_name)

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            java_source = f.read()

        # Java 파싱
        tree = javalang.parse.parse(java_source)

        # Annotation 파싱 헬퍼 import
        from csa.services.java_analysis.utils import parse_annotations

        # 클래스 찾기
        for path, node in tree:
            if isinstance(node, javalang.tree.ClassDeclaration):
                class_name = node.name

                # 클래스 annotations 파싱
                if hasattr(node, 'annotations') and node.annotations:
                    class_annotations = parse_annotations(node.annotations, "class")
                    class_description = extractor.extract_class_description(class_annotations)

                    if class_description:
                        extractor.update_class_description(graph_db, class_name, project_name, class_description)

                # 메서드 annotations 파싱
                if hasattr(node, 'methods'):
                    for method_node in node.methods:
                        if isinstance(method_node, javalang.tree.MethodDeclaration):
                            method_name = method_node.name

                            if hasattr(method_node, 'annotations') and method_node.annotations:
                                method_annotations = parse_annotations(method_node.annotations, "method")
                                method_description = extractor.extract_method_description(method_annotations)

                                if method_description:
                                    extractor.update_method_description(graph_db, class_name, method_name, project_name, method_description)

        return True

    except Exception as e:
        extractor.logger.error(f"Java 파일 처리 실패: {file_path}, {e}")
        return False
