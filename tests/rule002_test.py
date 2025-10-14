"""
Rule002 Description Extraction 테스트
tests/sample_java_project/UserController.java를 분석하여 Class와 Method의 description을 추출하고 출력한다.
"""

import os
import sys

# 프로젝트 루트를 sys.path에 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from csa.vendor import javalang
from csa.services.java_analysis.utils import parse_annotations
from csa.parsers.java.description import JavaDescriptionExtractor


def test_description_extraction():
    """UserController.java에서 description 추출 테스트"""

    print("=" * 80)
    print("Rule002 Description Extraction 테스트")
    print("=" * 80)

    # 테스트 파일 경로
    test_file = "tests/sample_java_project/UserController.java"
    project_name = "car-center-devlab"

    if not os.path.exists(test_file):
        print(f"\n[ERROR] 테스트 파일을 찾을 수 없습니다: {test_file}")
        return False

    print(f"\n[*] 분석 파일: {test_file}")
    print(f"[*] 프로젝트: {project_name}")
    print()

    try:
        # 파일 읽기
        with open(test_file, 'r', encoding='utf-8') as f:
            java_source = f.read()

        # Java 파싱
        tree = javalang.parse.parse(java_source)

        # Description Extractor 생성
        extractor = JavaDescriptionExtractor(project_name)

        # 클래스 찾기
        for path, node in tree:
            if isinstance(node, javalang.tree.ClassDeclaration):
                class_name = node.name

                print("-" * 80)
                print(f"[Class] {class_name}")
                print("-" * 80)

                # 클래스 annotations 파싱
                class_description = ""
                if hasattr(node, 'annotations') and node.annotations:
                    class_annotations = parse_annotations(node.annotations, "class")

                    # Annotations 출력
                    print("\n[Class Annotations]")
                    for ann in class_annotations:
                        print(f"   - @{ann.name}")
                        if ann.parameters:
                            for key, value in ann.parameters.items():
                                print(f"      {key} = {value}")

                    # Description 추출
                    class_description = extractor.extract_class_description(class_annotations)

                # 결과 출력
                print(f"\n[Class Description]")
                if class_description:
                    print(f"   [OK] {class_description}")
                else:
                    print(f"   [WARN] (추출된 description 없음)")

                # 메서드 분석
                print(f"\n[Methods]")
                print()

                method_count = 0
                if hasattr(node, 'methods'):
                    for method_node in node.methods:
                        if isinstance(method_node, javalang.tree.MethodDeclaration):
                            method_count += 1
                            method_name = method_node.name

                            print(f"   [{method_count}] Method: {method_name}()")

                            # 메서드 annotations 파싱
                            method_description = ""
                            if hasattr(method_node, 'annotations') and method_node.annotations:
                                method_annotations = parse_annotations(method_node.annotations, "method")

                                # Annotations 출력
                                print(f"       [Annotations]")
                                for ann in method_annotations:
                                    print(f"          - @{ann.name}")
                                    if ann.parameters:
                                        for key, value in ann.parameters.items():
                                            # description만 출력
                                            if key == "description":
                                                print(f"             {key} = {value}")

                                # Description 추출
                                method_description = extractor.extract_method_description(method_annotations)

                            # 결과 출력
                            print(f"       [Description]")
                            if method_description:
                                print(f"          [OK] {method_description}")
                            else:
                                print(f"          [WARN] (추출된 description 없음)")
                            print()

                print("-" * 80)
                print(f"[OK] 총 {method_count}개의 메서드 분석 완료")
                print("-" * 80)

        print("\n" + "=" * 80)
        print("[OK] 테스트 완료")
        print("=" * 80)
        return True

    except Exception as e:
        print(f"\n[ERROR] 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_description_extraction_summary():
    """Description 추출 결과 요약"""

    print("\n\n")
    print("=" * 80)
    print("Rule002 Description Extraction 결과 요약")
    print("=" * 80)

    test_file = "tests/sample_java_project/UserController.java"
    project_name = "car-center-devlab"

    if not os.path.exists(test_file):
        print(f"\n[ERROR] 테스트 파일을 찾을 수 없습니다: {test_file}")
        return

    try:
        with open(test_file, 'r', encoding='utf-8') as f:
            java_source = f.read()

        tree = javalang.parse.parse(java_source)
        extractor = JavaDescriptionExtractor(project_name)

        results = {
            "class_name": "",
            "class_description": "",
            "methods": []
        }

        for path, node in tree:
            if isinstance(node, javalang.tree.ClassDeclaration):
                results["class_name"] = node.name

                # 클래스 description
                if hasattr(node, 'annotations') and node.annotations:
                    class_annotations = parse_annotations(node.annotations, "class")
                    results["class_description"] = extractor.extract_class_description(class_annotations)

                # 메서드 description
                if hasattr(node, 'methods'):
                    for method_node in node.methods:
                        if isinstance(method_node, javalang.tree.MethodDeclaration):
                            method_name = method_node.name
                            method_description = ""

                            if hasattr(method_node, 'annotations') and method_node.annotations:
                                method_annotations = parse_annotations(method_node.annotations, "method")
                                method_description = extractor.extract_method_description(method_annotations)

                            results["methods"].append({
                                "name": method_name,
                                "description": method_description
                            })

        # 요약 출력
        print(f"\n[Class] {results['class_name']}")
        print(f"   Description: {results['class_description'] or '(없음)'}")
        print()
        print("[Methods]")
        for idx, method in enumerate(results["methods"], 1):
            print(f"   [{idx}] {method['name']}()")
            print(f"       Description: {method['description'] or '(없음)'}")

        print("\n" + "=" * 80)

    except Exception as e:
        print(f"\n[ERROR] 요약 생성 실패: {e}")


if __name__ == "__main__":
    # 상세 테스트 실행
    success = test_description_extraction()

    # 요약 출력
    if success:
        test_description_extraction_summary()
