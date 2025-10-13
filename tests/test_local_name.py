"""
샘플 Java 소스를 대상으로 클래스·메서드·필드의 logical_name을 추출해 출력하는 유틸 스크립트.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List

import javalang

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from csa.parsers.java import JavaLogicalNameExtractor

JAVA_SAMPLE_PATH = Path("tests/sample_java_project/UserController.java")
# 기본 프로젝트명으로 설정하면 개별 프로젝트 규칙이 없을 때 rule001 규칙을 사용한다.
PROJECT_NAME = "default"


def extract_logical_names(java_path: Path, project_name: str = PROJECT_NAME) -> Dict[str, Dict[str, str]]:
    """
    Java 소스 파일에서 클래스·메서드·필드의 논리명을 추출한다.

    Args:
        java_path: 분석할 Java 파일 경로.
        project_name: 규칙 파일을 탐색할 프로젝트명.

    Returns:
        요소 유형(class/method/field)별 {이름: 논리명} 매핑.
    """
    source = java_path.read_text(encoding="utf-8")
    extractor = JavaLogicalNameExtractor(project_name)
    tree = javalang.parse.parse(source)

    result: Dict[str, Dict[str, str]] = {"class": {}, "method": {}, "field": {}}

    for _, class_node in tree.filter(javalang.tree.ClassDeclaration):
        class_name = class_node.name
        class_logical = extractor.extract_class_logical_name(source, class_name) or ""
        result["class"][class_name] = class_logical

        for field in class_node.fields:
            for declarator in field.declarators:
                field_name = declarator.name
                field_logical = extractor.extract_field_logical_name(source, field_name) or ""
                result["field"][field_name] = field_logical

        for method in class_node.methods:
            method_name = method.name
            method_logical = extractor.extract_method_logical_name(source, method_name) or ""
            result["method"][method_name] = method_logical

    return result


def print_logical_names(logical_names: Dict[str, Dict[str, str]]) -> None:
    """추출 결과를 보기 좋게 출력한다."""
    print("=== logical_name 추출 결과 ===")

    class_entries = logical_names.get("class", {})
    print("\n[Class]")
    for name, logical_name in class_entries.items():
        print(f" - {name}: {logical_name or '(미추출)'}")

    field_entries = logical_names.get("field", {})
    print("\n[Field]")
    for name, logical_name in field_entries.items():
        print(f" - {name}: {logical_name or '(미추출)'}")

    method_entries = logical_names.get("method", {})
    print("\n[Method]")
    for name, logical_name in method_entries.items():
        print(f" - {name}: {logical_name or '(미추출)'}")


def main() -> None:
    """스크립트 진입점."""
    if not JAVA_SAMPLE_PATH.exists():
        raise FileNotFoundError(f"Java 샘플 파일을 찾을 수 없습니다: {JAVA_SAMPLE_PATH}")

    logical_names = extract_logical_names(JAVA_SAMPLE_PATH, PROJECT_NAME)
    print_logical_names(logical_names)


if __name__ == "__main__":
    main()
