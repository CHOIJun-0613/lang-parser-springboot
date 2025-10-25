"""
Java project parsing orchestration helpers.
"""
from __future__ import annotations

import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue
from threading import Lock
from typing import Dict, List, Optional, Tuple

from csa.vendor import javalang

from csa.models.graph_entities import (
    Bean,
    BeanDependency,
    Class, 
    ConfigFile,
    Endpoint,
    Field,
    Method,
    MethodCall,
    MyBatisMapper,
    Package,
    SqlStatement,
    TestClass,
)
from csa.services.graph_db import GraphDB
from csa.utils.logger import get_logger
from .config import extract_config_files
from .jpa import (
    analyze_jpa_entity_table_mapping,
    extract_jpa_entities_from_classes,
    extract_jpa_queries_from_repositories,
    extract_jpa_repositories_from_classes,
)
from .mybatis import (
    analyze_mybatis_resultmap_mapping,
    analyze_sql_method_relationships,
    extract_mybatis_mappers_from_classes,
    extract_mybatis_xml_mappers,
    extract_sql_statements_from_mappers,
    generate_db_call_chain_analysis,
)
from .spring import analyze_bean_dependencies, extract_beans_from_classes, extract_endpoints_from_classes
from .tests import extract_test_classes_from_classes
from .utils import (
    extract_project_name,
    extract_sub_type,
    generate_lombok_methods,
    parse_annotations,
)

# AI 분석 서비스
try:
    from csa.aiwork.ai_analyzer import get_ai_analyzer
    AI_ANALYZER_AVAILABLE = True
except ImportError:
    AI_ANALYZER_AVAILABLE = False
    get_ai_analyzer = None

def extract_inner_class_source(inner_class_declaration: javalang.tree.ClassDeclaration, file_content: str) -> str:
    """
    Inner class의 선언부 소스 코드 추출

    Args:
        inner_class_declaration: Inner class 선언 노드
        file_content: 전체 파일 소스 코드

    Returns:
        Inner class 선언부 소스 코드
    """
    if not inner_class_declaration.position:
        return ""

    lines = file_content.splitlines(keepends=True)
    start_line = inner_class_declaration.position.line - 1

    # 중괄호 개수로 클래스 선언 끝 위치 찾기
    brace_count = 0
    end_line = start_line
    found_opening_brace = False

    for i in range(start_line, len(lines)):
        line = lines[i]
        for char in line:
            if char == '{':
                brace_count += 1
                found_opening_brace = True
            elif char == '}':
                brace_count -= 1
                if found_opening_brace and brace_count == 0:
                    end_line = i
                    break

        if found_opening_brace and brace_count == 0:
            break

    return ''.join(lines[start_line:end_line + 1])


def parse_inner_classes(
    outer_class_declaration: javalang.tree.ClassDeclaration,
    outer_class_name: str,
    package_name: str,
    file_path: str,
    file_content: str,
    project_name: str,
    import_map: dict
) -> list[Class]:
    """
    재귀적으로 Inner class 파싱

    Args:
        outer_class_declaration: 외부 클래스 선언
        outer_class_name: 외부 클래스명
        package_name: 패키지명
        file_path: 파일 경로
        file_content: 소스 코드
        project_name: 프로젝트명
        import_map: import 맵

    Returns:
        Inner class 노드 리스트
    """
    logger = get_logger(__name__)
    inner_classes = []

    if not hasattr(outer_class_declaration, 'body') or not outer_class_declaration.body:
        return inner_classes

    for body_item in outer_class_declaration.body:
        if isinstance(body_item, javalang.tree.ClassDeclaration):
            # Inner class 이름
            inner_class_full_name = f"{outer_class_name}.{body_item.name}"

            inner_class_annotations = parse_annotations(body_item.annotations, "class") if hasattr(body_item, 'annotations') else []

            # Inner class 선언부 소스 추출
            inner_class_source = extract_inner_class_source(body_item, file_content)

            # 논리명 추출
            from csa.services.java_parser_addon_r001 import extract_java_class_logical_name
            inner_class_logical_name = extract_java_class_logical_name(file_content, body_item.name, project_name)

            # description 추출
            from csa.parsers.java.description import extract_java_class_description
            inner_class_description = extract_java_class_description(inner_class_annotations, project_name)

            # Inner class 노드 생성
            inner_class_node = Class(
                name=inner_class_full_name,
                logical_name=inner_class_logical_name if inner_class_logical_name else "",
                file_path=file_path,
                type="class",
                sub_type="inner_class",
                source=inner_class_source,
                annotations=inner_class_annotations,
                package_name=package_name,
                project_name=project_name,
                description=inner_class_description if inner_class_description else "",
                ai_description=""
            )

            # imports 추가
            for imp in import_map.values():
                inner_class_node.imports.append(imp)

            # 상속 관계 처리
            if hasattr(body_item, 'extends') and body_item.extends:
                superclass_name = body_item.extends.name
                if superclass_name in import_map:
                    inner_class_node.superclass = import_map[superclass_name]
                else:
                    inner_class_node.superclass = f"{package_name}.{superclass_name}" if package_name else superclass_name

            # 인터페이스 구현 처리
            if hasattr(body_item, 'implements') and body_item.implements:
                for impl_ref in body_item.implements:
                    interface_name = impl_ref.name
                    if interface_name in import_map:
                        inner_class_node.interfaces.append(import_map[interface_name])
                    else:
                        inner_class_node.interfaces.append(f"{package_name}.{interface_name}" if package_name else interface_name)

            # 필드 처리
            if hasattr(body_item, 'fields'):
                for field_declaration in body_item.fields:
                    for declarator in field_declaration.declarators:
                        field_type = field_declaration.type.name if hasattr(field_declaration.type, 'name') else str(field_declaration.type)

                        field_annotations = parse_annotations(field_declaration.annotations, "field") if hasattr(field_declaration, 'annotations') else []

                        initial_value = ""
                        if hasattr(declarator, 'initializer') and declarator.initializer:
                            if hasattr(declarator.initializer, 'value'):
                                initial_value = str(declarator.initializer.value)
                            elif hasattr(declarator.initializer, 'type'):
                                initial_value = str(declarator.initializer.type)

                        field = Field(
                            name=declarator.name,
                            type=field_type,
                            annotations=field_annotations,
                            initial_value=initial_value,
                            access_modifier="private"
                        )

                        inner_class_node.properties.append(field)

            # 메서드 처리
            if hasattr(body_item, 'methods'):
                call_order = 0
                for method_declaration in body_item.methods:
                    method_name = method_declaration.name
                    return_type = method_declaration.return_type.name if hasattr(method_declaration.return_type, 'name') else (str(method_declaration.return_type) if method_declaration.return_type else "void")

                    method_annotations = parse_annotations(method_declaration.annotations, "method") if hasattr(method_declaration, 'annotations') else []

                    # 메서드 파라미터를 Field 객체로 생성
                    parameters = []
                    if hasattr(method_declaration, 'parameters') and method_declaration.parameters:
                        for param in method_declaration.parameters:
                            param_type_name = 'Unknown'
                            if param.type:
                                if hasattr(param.type, 'sub_type') and param.type.sub_type:
                                    param_type_name = f"{param.type.name}.{param.type.sub_type.name}"
                                elif hasattr(param.type, 'name') and param.type.name:
                                    param_type_name = param.type.name

                            parameters.append(Field(
                                name=param.name,
                                logical_name=f"{package_name}.{outer_class_name}.{method_name}.{param.name}",
                                type=param_type_name,
                                package_name=package_name,
                                class_name=outer_class_name
                            ))

                    # 메서드 modifiers 추출
                    modifiers = list(method_declaration.modifiers) if hasattr(method_declaration, 'modifiers') else []

                    method = Method(
                        name=method_name,
                        return_type=return_type,
                        annotations=method_annotations,
                        parameters=parameters,
                        modifiers=modifiers
                    )

                    inner_class_node.methods.append(method)

            inner_classes.append(inner_class_node)

            # 중첩된 inner class (재귀)
            if hasattr(body_item, 'body') and body_item.body:
                nested = parse_inner_classes(
                    body_item, inner_class_full_name, package_name, file_path,
                    file_content, project_name, import_map
                )
                inner_classes.extend(nested)

    return inner_classes


def parse_single_java_file(file_path: str, project_name: str, graph_db: GraphDB = None) -> tuple[Package, Class, list[Class], str]:
    """Parse a single Java file and return parsed entities."""
    logger = get_logger(__name__)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        file_content = f.read()
    
    try:
        tree = javalang.parse.parse(file_content)
        logger.debug(f"Successfully parsed file: {file_path}")
        
        package_name = tree.package.name if tree.package else ""
        logger.debug(f"Parsed package name: {package_name}")
        
        if package_name:
            package_node = Package(name=package_name)
        else:
            package_name = "default"
            package_node = Package(name=package_name)
        
        import_map = {}
        for imp in tree.imports:
            class_name = imp.path.split('.')[-1]
            import_map[class_name] = imp.path
        
        # 클래스 선언 찾기
        class_declaration = None
        for type_decl in tree.types:
            if isinstance(type_decl, (javalang.tree.ClassDeclaration, javalang.tree.InterfaceDeclaration)):
                class_declaration = type_decl
                break
        
        if not class_declaration:
            logger.error(f"No class declaration found in file: {file_path}")
            return None, None, [], ""
        
        class_name = class_declaration.name
        class_annotations = parse_annotations(class_declaration.annotations, "class") if hasattr(class_declaration, 'annotations') else []
        class_type = "interface" if isinstance(class_declaration, javalang.tree.InterfaceDeclaration) else "class"
        
        # sub_type 추출
        sub_type = extract_sub_type(package_name, class_name, class_annotations)
        
        # 논리명 추출 시도
        from csa.services.java_parser_addon_r001 import extract_java_class_logical_name
        class_logical_name = extract_java_class_logical_name(file_content, class_name, project_name)

        # description 추출 시도 (Rule002)
        from csa.parsers.java.description import extract_java_class_description
        class_description = extract_java_class_description(class_annotations, project_name)

        # AI 분석 수행 (오류 시 빈 문자열 반환)
        ai_description = ""
        if AI_ANALYZER_AVAILABLE:
            try:
                analyzer = get_ai_analyzer()
                if analyzer.is_available():
                    ai_description = analyzer.analyze_class(file_content, class_name)
            except Exception as e:
                logger.warning(f"AI Class 분석 실패 ({class_name}): {e}")
                ai_description = ""

        class_node = Class(
            name=class_name,
            logical_name=class_logical_name if class_logical_name else "",
            file_path=file_path,
            type=class_type,
            sub_type=sub_type,
            source=file_content,
            annotations=class_annotations,
            package_name=package_name,
            project_name=project_name,
            description=class_description if class_description else "",
            ai_description=ai_description
        )

        # imports 추가
        for imp in tree.imports:
            class_node.imports.append(imp.path)
        
        # 상속 관계 처리
        if class_declaration.extends:
            superclass_name = class_declaration.extends.name
            if superclass_name in import_map:
                class_node.superclass = import_map[superclass_name]
            else:
                class_node.superclass = f"{package_name}.{superclass_name}" if package_name else superclass_name
        
        # 인터페이스 구현 처리
        if hasattr(class_declaration, 'implements') and class_declaration.implements:
            for impl_ref in class_declaration.implements:
                interface_name = impl_ref.name
                if interface_name in import_map:
                    class_node.interfaces.append(import_map[interface_name])
                else:
                    class_node.interfaces.append(f"{package_name}.{interface_name}" if package_name else interface_name)
        
        # 필드 처리
        field_map = {}
        for field_declaration in class_declaration.fields:
            for declarator in field_declaration.declarators:
                field_map[declarator.name] = field_declaration.type.name
                
                field_annotations = parse_annotations(field_declaration.annotations, "field") if hasattr(field_declaration, 'annotations') else []
                
                initial_value = ""
                if hasattr(declarator, 'initializer') and declarator.initializer:
                    if hasattr(declarator.initializer, 'value'):
                        initial_value = str(declarator.initializer.value)
                    elif hasattr(declarator.initializer, 'type'):
                        initial_value = str(declarator.initializer.type)
                    else:
                        initial_value = str(declarator.initializer)
                
                # 필드 논리명 추출 시도
                from csa.services.java_parser_addon_r001 import extract_java_field_logical_name
                field_logical_name = extract_java_field_logical_name(file_content, declarator.name, project_name)
                
                prop = Field(
                    name=declarator.name,
                    logical_name=field_logical_name if field_logical_name else "",
                    type=field_declaration.type.name,
                    modifiers=list(field_declaration.modifiers),
                    package_name=package_name,
                    class_name=class_name,
                    annotations=field_annotations,
                    initial_value=initial_value,
                    description="",
                    ai_description=""
                )
                class_node.properties.append(prop)
        
        # 메서드 처리
        all_declarations = class_declaration.methods + class_declaration.constructors
        
        for declaration in all_declarations:
            local_var_map = field_map.copy()
            params = []
            for param in declaration.parameters:
                param_type_name = 'Unknown'
                if param.type:
                    if hasattr(param.type, 'sub_type') and param.type.sub_type:
                        param_type_name = f"{param.type.name}.{param.type.sub_type.name}"
                    elif hasattr(param.type, 'name') and param.type.name:
                        param_type_name = param.type.name
                local_var_map[param.name] = param_type_name
                params.append(Field(name=param.name, logical_name=f"{package_name}.{class_name}.{param.name}", type=param_type_name, package_name=package_name, class_name=class_name))
            
            if declaration.body:
                for _, var_decl in declaration.filter(javalang.tree.LocalVariableDeclaration):
                    for declarator in var_decl.declarators:
                        local_var_map[declarator.name] = var_decl.type.name
            
            if isinstance(declaration, javalang.tree.MethodDeclaration):
                return_type = declaration.return_type.name if declaration.return_type else "void"
            else:
                return_type = "constructor"
            
            modifiers = list(declaration.modifiers)
            method_annotations = parse_annotations(declaration.annotations, "method") if hasattr(declaration, 'annotations') else []
            
            method_source = ""
            if declaration.position:
                lines = file_content.splitlines(keepends=True)
                start_line = declaration.position.line - 1
                
                brace_count = 0
                end_line = start_line
                for i in range(start_line, len(lines)):
                    line = lines[i]
                    for char in line:
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                end_line = i
                                break
                    if brace_count == 0:
                        break
                
                method_source = "".join(lines[start_line:end_line + 1])
            
            # 논리명 추출 시도
            from csa.services.java_parser_addon_r001 import extract_java_method_logical_name
            method_logical_name = extract_java_method_logical_name(file_content, declaration.name, project_name)

            # description 추출 시도 (Rule002)
            from csa.parsers.java.description import extract_java_method_description
            method_description = extract_java_method_description(method_annotations, project_name)

            # AI 분석 수행 (오류 시 빈 문자열 반환)
            method_ai_description = ""
            if AI_ANALYZER_AVAILABLE and method_source:
                try:
                    analyzer = get_ai_analyzer()
                    if analyzer.is_available():
                        method_ai_description = analyzer.analyze_method(method_source, declaration.name)
                except Exception as e:
                    logger.warning(f"AI Method 분석 실패 ({class_name}.{declaration.name}): {e}")
                    method_ai_description = ""

            method = Method(
                name=declaration.name,
                logical_name=method_logical_name if method_logical_name else "",
                return_type=return_type,
                parameters=params,
                modifiers=modifiers,
                source=method_source,
                package_name=package_name,
                annotations=method_annotations,
                description=method_description if method_description else "",
                ai_description=method_ai_description,
                calls=[]  # 명시적으로 calls 속성 초기화
            )
            
            # 메서드 호출 분석 - MethodCall 객체 생성
            if declaration.body:
                call_order = 1
                for _, invocation in declaration.filter(javalang.tree.MethodInvocation):
                    if not invocation.position:
                        continue
                    
                    # 로그 메서드 자체 제외
                    if invocation.qualifier and invocation.qualifier in ['log', 'logger', 'LOGGER']:
                        if hasattr(invocation, 'member') and invocation.member in ['info', 'debug', 'warn', 'error', 'trace']:
                            continue
                    
                    target_class_name = None
                    resolved_target_package = ""
                    resolved_target_class_name = ""
                    
                    if invocation.qualifier:
                        if invocation.qualifier in local_var_map:
                            target_class_name = local_var_map[invocation.qualifier]
                        else:
                            target_class_name = invocation.qualifier
                        
                        if target_class_name:
                            if target_class_name == "System.out":
                                resolved_target_package = "java.io"
                                resolved_target_class_name = "PrintStream"
                            else:
                                if invocation.qualifier in local_var_map:
                                    resolved_target_class_name = target_class_name
                                    if target_class_name in import_map:
                                        resolved_target_package = ".".join(import_map[target_class_name].split(".")[:-1])
                                    else:
                                        # import_map에 없으면 현재 패키지만 사용
                                        # (잘못된 패키지 추론 로직 제거)
                                        resolved_target_package = package_name
                                
                                if '<' in target_class_name:
                                    base_type = target_class_name.split('<')[0]
                                    resolved_target_class_name = base_type
                                
                                if not resolved_target_class_name:
                                    if target_class_name in import_map:
                                        resolved_target_package = ".".join(import_map[target_class_name].split(".")[:-1])
                                    else:
                                        resolved_target_package = package_name
                                    resolved_target_class_name = target_class_name
                    else:
                        resolved_target_package = package_name
                        resolved_target_class_name = class_name

                    if resolved_target_class_name:
                        method_name = invocation.member
                        # Stream API 메서드 필터링
                        if method_name in {'collect', 'map', 'filter', 'forEach', 'stream', 'reduce', 'findFirst', 'findAny', 'anyMatch', 'allMatch', 'noneMatch', 'count', 'distinct', 'sorted', 'limit', 'skip', 'peek', 'flatMap', 'toArray'}:
                            continue
                            
                        line_number = invocation.position.line if invocation.position else 0

                        call = MethodCall(
                            source_package=package_name,
                            source_class=class_name,
                            source_method=declaration.name,
                            target_package=resolved_target_package,
                            target_class=resolved_target_class_name,
                            target_method=invocation.member,
                            call_order=call_order,
                            line_number=line_number,
                            return_type="void"
                        )
                        class_node.calls.append(call)
                        call_order += 1
            
            class_node.methods.append(method)

        # Inner class 파싱
        inner_classes = parse_inner_classes(
            class_declaration,
            class_name,
            package_name,
            file_path,
            file_content,
            project_name,
            import_map
        )

        logger.debug(f"Successfully parsed single file: {file_path} (found {len(inner_classes)} inner classes)")
        return package_node, class_node, inner_classes, package_name

    except Exception as e:
        logger.error(f"Error parsing file: {e}")
        return None, None, [], ""

def parse_java_project_full(directory: str, graph_db: GraphDB = None) -> tuple[list[Package], list[Class], dict[str, str], list[Bean], list[BeanDependency], list[Endpoint], list[MyBatisMapper], list[JpaEntity], list[JpaRepository], list[JpaQuery], list[ConfigFile], list[TestClass], list[SqlStatement], str]:
    """Parse Java project and return parsed entities."""
    logger = get_logger(__name__)
    
    project_name = extract_project_name(directory)
    packages = {}
    classes = {}
    class_to_package_map = {}
    
    logger.info(f"Starting Java project analysis in: {directory}")
    logger.info(f"Project name: {project_name}")

    java_file_count = 0
    processed_file_count = 0
    
    # 클래스 파싱 진행 상황 추적을 위한 변수들
    total_classes = 0
    processed_classes = 0
    last_logged_percent = 0
    
    # 먼저 전체 클래스 개수를 계산
    logger.info("클래스 개수 계산 중...")
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".java"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        file_content = f.read()
                    
                    tree = javalang.parse.parse(file_content)
                    for type_decl in tree.types:
                        if isinstance(type_decl, (javalang.tree.ClassDeclaration, javalang.tree.InterfaceDeclaration)):
                            total_classes += 1
                except Exception:
                    continue
    
    logger.info(f"총 {total_classes}개 클래스 발견")
    
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".java"):
                java_file_count += 1
                file_path = os.path.join(root, file)
                logger.debug(f"Processing Java file {java_file_count}: {file_path}")
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_content = f.read()
                
                try:
                    tree = javalang.parse.parse(file_content)
                    package_name = tree.package.name if tree.package else ""
                    logger.debug(f"Parsed file: {file_path}, package: {package_name}")
                    
                    if package_name and package_name not in packages:
                        packages[package_name] = Package(
                            name=package_name
                        )
                    elif not package_name:
                        package_name = "default"
                        if package_name not in packages:
                            packages[package_name] = Package(
                                name=package_name
                            )
                    
                    import_map = {}
                    for imp in tree.imports:
                        class_name = imp.path.split('.')[-1]
                        import_map[class_name] = imp.path

                    class_declarations = []
                    for type_decl in tree.types:
                        if isinstance(type_decl, (javalang.tree.ClassDeclaration, javalang.tree.InterfaceDeclaration)):
                            class_declarations.append((None, type_decl))
                    
                    for _, class_declaration in class_declarations:
                        class_name = class_declaration.name
                        class_key = f"{package_name}.{class_name}"
                        logger.debug(f"Processing class/interface: {class_name} (type: {type(class_declaration).__name__})")
                        
                        if class_key not in classes:
                            class_annotations = parse_annotations(class_declaration.annotations, "class") if hasattr(class_declaration, 'annotations') else []
                            class_type = "interface" if isinstance(class_declaration, javalang.tree.InterfaceDeclaration) else "class"
                            
                            # sub_type 추출 (package name의 마지막 단어)
                            sub_type = extract_sub_type(package_name, class_name, class_annotations)
                            
                            # 논리명 추출 시도
                            from csa.services.java_parser_addon_r001 import extract_java_class_logical_name
                            class_logical_name = extract_java_class_logical_name(file_content, class_name, project_name)

                            # description 추출 시도 (Rule002)
                            from csa.parsers.java.description import extract_java_class_description
                            class_description = extract_java_class_description(class_annotations, project_name)

                            classes[class_key] = Class(
                                name=class_name,
                                logical_name=class_logical_name if class_logical_name else "",
                                file_path=file_path,
                                type=class_type,
                                sub_type=sub_type,
                                source=file_content,
                                annotations=class_annotations,
                                package_name=package_name,
                                project_name=project_name,
                                description=class_description if class_description else "",
                                ai_description=""
                            )
                            class_to_package_map[class_key] = package_name
                            logger.debug(f"Successfully added class to classes dict: {class_name} (key: {class_key})")
                            
                            # 진행 상황을 10% 단위로 표시
                            processed_classes += 1
                            current_percent = int((processed_classes / total_classes) * 100) if total_classes > 0 else 0
                            
                            if current_percent >= last_logged_percent + 10 or processed_classes == total_classes:
                                last_logged_percent = current_percent
                                logger.info(f"클래스 파싱 진행중 [{processed_classes}/{total_classes}] ({current_percent}%) - 최근: {class_name}")
                        else:
                            logger.debug(f"Class {class_name} already exists, skipping")
                        
                        for imp in tree.imports:
                            classes[class_key].imports.append(imp.path)

                        if class_declaration.extends:
                            superclass_name = class_declaration.extends.name
                            if superclass_name in import_map:
                                classes[class_key].superclass = import_map[superclass_name]
                            else:
                                classes[class_key].superclass = f"{package_name}.{superclass_name}" if package_name else superclass_name

                        if hasattr(class_declaration, 'implements') and class_declaration.implements:
                            for impl_ref in class_declaration.implements:
                                interface_name = impl_ref.name
                                if interface_name in import_map:
                                    classes[class_key].interfaces.append(import_map[interface_name])
                                else:
                                    classes[class_key].interfaces.append(f"{package_name}.{interface_name}" if package_name else interface_name)

                        field_map = {}
                        for field_declaration in class_declaration.fields:
                            for declarator in field_declaration.declarators:
                                field_map[declarator.name] = field_declaration.type.name
                                
                                field_annotations = parse_annotations(field_declaration.annotations, "field") if hasattr(field_declaration, 'annotations') else []
                                
                                initial_value = ""
                                if hasattr(declarator, 'initializer') and declarator.initializer:
                                    if hasattr(declarator.initializer, 'value'):
                                        initial_value = str(declarator.initializer.value)
                                    elif hasattr(declarator.initializer, 'type'):
                                        initial_value = str(declarator.initializer.type)
                                    else:
                                        initial_value = str(declarator.initializer)
                                
                                # 필드 논리명 추출 시도
                                from csa.services.java_parser_addon_r001 import extract_java_field_logical_name
                                field_logical_name = extract_java_field_logical_name(file_content, declarator.name, project_name)
                                
                                prop = Field(
                                    name=declarator.name,
                                    logical_name=field_logical_name if field_logical_name else "",
                                    type=field_declaration.type.name,
                                    modifiers=list(field_declaration.modifiers),
                                    package_name=package_name,
                                    class_name=class_name,
                                    annotations=field_annotations,
                                    initial_value=initial_value,
                                    description="",
                                    ai_description=""
                                )
                                classes[class_key].properties.append(prop)

                        all_declarations = class_declaration.methods + class_declaration.constructors
                        
                        for declaration in all_declarations:
                            local_var_map = field_map.copy()
                            params = []
                            for param in declaration.parameters:
                                param_type_name = 'Unknown'
                                if param.type:
                                    # ReferenceType의 경우 - 내부 클래스 지원
                                    if hasattr(param.type, 'sub_type') and param.type.sub_type:
                                        # PaymentDto.RefundRequest 형태
                                        param_type_name = f"{param.type.name}.{param.type.sub_type.name}"
                                    elif hasattr(param.type, 'name') and param.type.name:
                                        # 일반 타입
                                        param_type_name = param.type.name
                                local_var_map[param.name] = param_type_name
                                params.append(Field(name=param.name, logical_name=f"{package_name}.{class_name}.{param.name}", type=param_type_name, package_name=package_name, class_name=class_name))

                            if declaration.body:
                                for _, var_decl in declaration.filter(javalang.tree.LocalVariableDeclaration):
                                    for declarator in var_decl.declarators:
                                        local_var_map[declarator.name] = var_decl.type.name
                            
                            if isinstance(declaration, javalang.tree.MethodDeclaration):
                                return_type = declaration.return_type.name if declaration.return_type else "void"
                            else:
                                return_type = "constructor"

                            modifiers = list(declaration.modifiers)
                            method_annotations = parse_annotations(declaration.annotations, "method") if hasattr(declaration, 'annotations') else []

                            method_source = ""
                            if declaration.position:
                                lines = file_content.splitlines(keepends=True)
                                start_line = declaration.position.line - 1
                                
                                brace_count = 0
                                end_line = start_line
                                for i in range(start_line, len(lines)):
                                    line = lines[i]
                                    for char in line:
                                        if char == '{':
                                            brace_count += 1
                                        elif char == '}':
                                            brace_count -= 1
                                            if brace_count == 0:
                                                end_line = i
                                                break
                                    if brace_count == 0:
                                        break
                                
                                method_source = "".join(lines[start_line:end_line + 1])

                            # 논리명 추출 시도
                            from csa.services.java_parser_addon_r001 import extract_java_method_logical_name
                            method_logical_name = extract_java_method_logical_name(file_content, declaration.name, project_name)

                            # description 추출 시도 (Rule002)
                            from csa.parsers.java.description import extract_java_method_description
                            method_description = extract_java_method_description(method_annotations, project_name)

                            method = Method(
                                name=declaration.name,
                                logical_name=method_logical_name if method_logical_name else "",
                                return_type=return_type,
                                parameters=params,
                                modifiers=modifiers,
                                source=method_source,
                                package_name=package_name,
                                annotations=method_annotations,
                                description=method_description if method_description else "",
                                ai_description=""
                            )
                            classes[class_key].methods.append(method)

                            # Step 1: 로그 메서드가 있는 라인 번호 수집 (더 포괄적으로)
                            log_lines = set()
                            for _, invocation in declaration.filter(javalang.tree.MethodInvocation):
                                # 로그 메서드 감지 (더 포괄적)
                                is_log_method = False
                                
                                # log.info, logger.debug 등
                                if invocation.qualifier and invocation.qualifier in ['log', 'logger', 'LOGGER']:
                                    if hasattr(invocation, 'member') and invocation.member in ['info', 'debug', 'warn', 'error', 'trace']:
                                        is_log_method = True
                                
                                # System.out.println, System.err.println
                                elif invocation.qualifier and invocation.qualifier in ['System']:
                                    if hasattr(invocation, 'member') and invocation.member in ['out', 'err']:
                                        is_log_method = True
                                
                                # println 메서드 직접 호출
                                elif hasattr(invocation, 'member') and invocation.member in ['println', 'print']:
                                    is_log_method = True
                                
                                if is_log_method and invocation.position:
                                    # 로그 메서드가 있는 라인과 인접한 라인들도 포함 (멀티라인 로그 지원)
                                    log_line = invocation.position.line
                                    log_lines.add(log_line)
                                    log_lines.add(log_line + 1)  # 다음 라인도 포함

                            # Step 2: 메서드 호출 추출 (로그 라인 제외)
                            call_order = 0
                            for _, invocation in declaration.filter(javalang.tree.MethodInvocation):
                                # position이 없는 호출은 건너뛰기 (순서를 알 수 없음)
                                if not invocation.position:
                                    continue
                                
                                # 로그 라인에 있는 모든 메서드 호출 제외
                                if invocation.position.line in log_lines:
                                    continue
                                
                                # 로그 메서드 자체 제외
                                if invocation.qualifier and invocation.qualifier in ['log', 'logger', 'LOGGER']:
                                    if hasattr(invocation, 'member') and invocation.member in ['info', 'debug', 'warn', 'error', 'trace']:
                                        continue
                                    
                                target_class_name = None
                                resolved_target_package = ""
                                resolved_target_class_name = ""
                                
                                if invocation.qualifier:
                                    if invocation.qualifier in local_var_map:
                                        target_class_name = local_var_map[invocation.qualifier]
                                    else:
                                        target_class_name = invocation.qualifier
                                    
                                    if target_class_name:
                                        if target_class_name == "System.out":
                                            resolved_target_package = "java.io"
                                            resolved_target_class_name = "PrintStream"
                                        else:
                                            if invocation.qualifier in local_var_map:
                                                resolved_target_class_name = target_class_name
                                                if target_class_name in import_map:
                                                    resolved_target_package = ".".join(import_map[target_class_name].split(".")[:-1])
                                                else:
                                                    # import_map에 없으면 현재 패키지만 사용
                                                    # (잘못된 패키지 추론 로직 제거)
                                                    resolved_target_package = package_name
                                                
                                                if '<' in target_class_name:
                                                    base_type = target_class_name.split('<')[0]
                                                    resolved_target_class_name = base_type
                                            else:
                                                if target_class_name in import_map:
                                                    resolved_target_package = ".".join(import_map[target_class_name].split(".")[:-1])
                                                else:
                                                    resolved_target_package = package_name
                                                resolved_target_class_name = target_class_name
                                else:
                                    resolved_target_package = package_name
                                    resolved_target_class_name = class_name

                                if resolved_target_class_name:
                                    method_name = invocation.member
                                    if method_name in {'collect', 'map', 'filter', 'forEach', 'stream', 'reduce', 'findFirst', 'findAny', 'anyMatch', 'allMatch', 'noneMatch', 'count', 'distinct', 'sorted', 'limit', 'skip', 'peek', 'flatMap', 'toArray'}:
                                        continue
                                        
                                    line_number = invocation.position.line if invocation.position else 0

                                    call = MethodCall(
                                        source_package=package_name,
                                        source_class=class_name,
                                        source_method=declaration.name,
                                        target_package=resolved_target_package,
                                        target_class=resolved_target_class_name,
                                        target_method=invocation.member,
                                        call_order=call_order,
                                        line_number=line_number,
                                        return_type="void"
                                    )
                                    classes[class_key].calls.append(call)
                                    call_order += 1
                        
                        has_data_annotation = any(ann.name == "Data" for ann in classes[class_key].annotations)
                        if has_data_annotation:
                            logger.debug(f"Found @Data annotation on {class_name}, generating Lombok methods")
                            lombok_methods = generate_lombok_methods(classes[class_key].properties, class_name, package_name)
                            classes[class_key].methods.extend(lombok_methods)
                            logger.debug(f"Generated {len(lombok_methods)} Lombok methods for {class_name}")
                    
                    processed_file_count += 1
                    logger.debug(f"Successfully processed file: {file_path}")
                    
                    # Rule001 논리명 추출 로직 제거 - 이미 파싱 시 처리됨
                
                except Exception as e:
                    logger.error(f"Error processing file {file_path}: {e}")
                    continue
    
    classes_list = list(classes.values())
    beans = extract_beans_from_classes(classes_list)

    # NOTE: Bean 의존성은 Neo4j에 저장된 후 resolve_bean_dependencies_from_neo4j()로 해결
    # 메모리 효율을 위해 파싱 단계에서는 의존성을 해결하지 않음 (방안 B)
    dependencies = []

    endpoints = extract_endpoints_from_classes(classes_list)
    mybatis_mappers = extract_mybatis_mappers_from_classes(classes_list)
    jpa_entities = extract_jpa_entities_from_classes(classes_list)
    jpa_repositories = extract_jpa_repositories_from_classes(classes_list)
    jpa_queries = extract_jpa_queries_from_repositories(jpa_repositories)
    config_files = extract_config_files(directory)
    test_classes = extract_test_classes_from_classes(classes_list)
    
    xml_mappers = extract_mybatis_xml_mappers(directory, project_name, graph_db)
    mybatis_mappers.extend(xml_mappers)
    
    sql_statements = extract_sql_statements_from_mappers(mybatis_mappers, project_name)
    
    resultmap_mapping_analysis = analyze_mybatis_resultmap_mapping(mybatis_mappers, sql_statements)
    sql_method_relationships = analyze_sql_method_relationships(sql_statements, classes_list)
    db_call_chain_analysis = generate_db_call_chain_analysis(sql_statements, classes_list)
    
    logger.info(f"Java project analysis complete:")
    logger.info(f"  - Java files processed: {processed_file_count}/{java_file_count}")
    logger.info(f"  - Packages found: {len(packages)}")
    logger.info(f"  - Classes found: {len(classes)}")
    logger.info(f"  - Classes list length: {len(classes_list)}")
    
    return (
        list(packages.values()),
        classes_list,
        class_to_package_map,
        beans,
        dependencies,
        endpoints,
        mybatis_mappers,
        jpa_entities,
        jpa_repositories,
        jpa_queries,
        config_files,
        test_classes,
        sql_statements,
        project_name,
    )

def _parse_single_file_wrapper(file_path: str, project_name: str) -> tuple:
    """
    병렬 처리용 파싱 래퍼 함수 (Neo4j 연결 없이 파싱만 수행)

    Args:
        file_path: Java 파일 경로
        project_name: 프로젝트명

    Returns:
        tuple: (file_path, package_node, class_node, inner_classes, package_name) 또는 (file_path, None, None, [], None) on error
    """
    try:
        package_node, class_node, inner_classes, package_name = parse_single_java_file(
            file_path, project_name, None  # graph_db=None for parsing only
        )
        return (file_path, package_node, class_node, inner_classes, package_name)
    except Exception as e:
        # 예외 발생 시 None 반환 (메인 스레드에서 로깅)
        return (file_path, None, None, [], str(e))


def parse_java_project_streaming(
    directory: str,
    graph_db: GraphDB,
    project_name: str,
    parallel_workers: int = 8,
) -> dict:
    """
    스트리밍 방식 Java 프로젝트 파싱

    파일을 하나씩 파싱하고 즉시 Neo4j에 저장한 후 메모리에서 제거합니다.
    메모리 사용량을 최소화하여 대규모 프로젝트 분석이 가능합니다.

    Args:
        directory: Java 소스 디렉토리 경로
        graph_db: Neo4j GraphDB 인스턴스
        project_name: 프로젝트명

    Returns:
        dict: 분석 통계
            {
                'total_files': int,
                'processed_files': int,
                'packages': int,
                'classes': int,
                'beans': int,
                'endpoints': int,
                'jpa_entities': int,
                'jpa_repositories': int,
                'jpa_queries': int,
                'test_classes': int,
                'mybatis_mappers': int,
                'sql_statements': int,
                'config_files': int,
            }
    """
    from csa.services.analysis.neo4j_writer import add_single_class_objects_streaming

    logger = get_logger(__name__)

    logger.info(f"Starting Java project streaming analysis in: {directory}")
    logger.info(f"Project name: {project_name}")

    packages_saved = set()
    stats = {
        'total_files': 0,
        'processed_files': 0,
        'packages': 0,
        'classes': 0,
        'beans': 0,
        'endpoints': 0,
        'jpa_entities': 0,
        'jpa_repositories': 0,
        'jpa_queries': 0,
        'test_classes': 0,
        'mybatis_mappers': 0,
        'sql_statements': 0,
        'config_files': 0,
    }

    # 진행 상황 추적 (스레드 안전)
    processed_classes = 0
    last_logged_percent = 0
    progress_lock = Lock()

    # 1회 스캔: 모든 .java 파일 경로 수집
    logger.info("Java 파일 수집 중...")
    java_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".java"):
                java_files.append(os.path.join(root, file))

    total_files = len(java_files)
    stats['total_files'] = total_files
    logger.info(f"총 {total_files}개 Java 파일 발견")

    # 환경 변수에서 병렬 워커 수 가져오기 (기본값 8)
    parallel_workers = int(os.getenv("JAVA_PARSE_WORKERS", str(parallel_workers)))
    batch_size = int(os.getenv("NEO4J_BATCH_SIZE", "50"))  # 배치 크기
    logger.info(f"병렬 파싱 워커 수: {parallel_workers}, Neo4j 배치 크기: {batch_size}")

    # 0. Package 사전 생성 (성능 최적화)
    logger.info("Package 정보 수집 중...")
    package_names = set()
    package_pattern = re.compile(r'^\s*package\s+([\w.]+)\s*;', re.MULTILINE)

    for file_path in java_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read(500)  # 첫 500자만 읽기 (package는 파일 상단에 위치)
                match = package_pattern.search(content)
                if match:
                    package_names.add(match.group(1))
        except Exception as e:
            logger.debug(f"Package 추출 실패 (무시): {file_path} - {e}")
            continue

    # 모든 Package를 한 번에 생성 (배치 처리)
    if package_names:
        logger.info(f"총 {len(package_names)}개 패키지 발견, 배치 생성 중...")
        package_start = time.time()
        package_nodes = [Package(name=pkg_name) for pkg_name in package_names]
        graph_db.add_packages_batch(package_nodes, project_name)
        packages_saved.update(package_names)
        stats['packages'] = len(package_names)
        package_elapsed = time.time() - package_start
        logger.info(f"Package 배치 생성 완료 ({package_elapsed:.2f}초)")

    # 1. 병렬 파일 파싱 + 배치 Neo4j 저장
    logger.info("병렬 파싱 시작...")
    parse_start_time = time.time()

    # 파싱된 결과를 임시 저장할 버퍼
    parsed_buffer = []

    with ThreadPoolExecutor(max_workers=parallel_workers) as executor:
        # 모든 파일을 병렬로 파싱 제출
        future_to_file = {
            executor.submit(_parse_single_file_wrapper, file_path, project_name): file_path
            for file_path in java_files
        }

        # 완료된 순서대로 처리
        for future in as_completed(future_to_file):
            file_path = future_to_file[future]
            try:
                # 파싱 결과 획득
                _, package_node, class_node, inner_classes, package_name = future.result()

                # 파싱 실패 시 (에러 메시지가 package_name에 담김)
                if class_node is None:
                    if isinstance(package_name, str) and package_name:
                        logger.error(f"Error parsing {file_path}: {package_name}")
                    continue

                # 버퍼에 추가 (스레드 안전)
                with progress_lock:
                    # Top-level 클래스와 Inner classes를 함께 저장
                    parsed_buffer.append((package_node, class_node, inner_classes, package_name))
                    processed_classes += 1

                    # 진행 상황 로깅 (파싱 단계) - 10% 단위로만 출력
                    current_percent = int((processed_classes / total_files) * 100) if total_files > 0 else 0
                    if current_percent > last_logged_percent and current_percent % 10 == 0:
                        last_logged_percent = current_percent
                        logger.info(f"파싱 진행중 [{processed_classes}/{total_files}] ({current_percent}%)")

                    # 배치 크기에 도달하거나 마지막 파일인 경우 저장
                    if len(parsed_buffer) >= batch_size or processed_classes == total_files:
                        batch_start_time = time.time()
                        logger.debug(f"배치 저장 시작 ({len(parsed_buffer)}개 클래스)")

                        # Package는 이미 사전 생성되어 있으므로 건너뜀

                        # Class 배치 저장 (Top-level + Inner classes)
                        classes_to_save = []
                        class_to_package = {}

                        for package_node, class_node, inner_classes, package_name in parsed_buffer:
                            classes_to_save.append(class_node)
                            class_to_package[class_node.name] = package_name

                            # Inner classes도 저장
                            for inner_class in inner_classes:
                                classes_to_save.append(inner_class)
                                class_to_package[inner_class.name] = package_name

                        # 클래스 배치 저장 (성능 최적화)
                        classes_batch_data = [
                            (cls, class_to_package.get(cls.name, ""), project_name)
                            for cls in classes_to_save
                        ]
                        graph_db.add_classes_batch(classes_batch_data)
                        stats['classes'] += len(classes_to_save)

                        # Bean/Endpoint 등 배치 저장
                        from csa.services.analysis.neo4j_writer import add_batch_class_objects_streaming
                        batch_stats = add_batch_class_objects_streaming(
                            graph_db, parsed_buffer, project_name, logger
                        )

                        # 통계 누적
                        stats['beans'] += batch_stats.get('beans', 0)
                        stats['endpoints'] += batch_stats.get('endpoints', 0)
                        stats['jpa_entities'] += batch_stats.get('jpa_entities', 0)
                        stats['jpa_repositories'] += batch_stats.get('jpa_repositories', 0)
                        stats['jpa_queries'] += batch_stats.get('jpa_queries', 0)
                        stats['test_classes'] += batch_stats.get('test_classes', 0)
                        stats['mybatis_mappers'] += batch_stats.get('mybatis_mappers', 0)
                        stats['sql_statements'] += batch_stats.get('sql_statements', 0)

                        stats['processed_files'] += len(parsed_buffer)

                        # 버퍼 비우기
                        parsed_buffer.clear()
                        batch_elapsed = time.time() - batch_start_time
                        logger.debug(f"배치 저장 완료 ({batch_elapsed:.2f}초)")

            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
                continue

    parse_elapsed = time.time() - parse_start_time
    logger.info(f"파싱 및 저장 완료 - 소요 시간: {parse_elapsed:.2f}초 (파일당 평균: {parse_elapsed/total_files*1000:.0f}ms)")

    # 2. MyBatis XML mappers 추출 및 저장
    logger.info("MyBatis XML mappers 처리 중...")
    xml_mappers = extract_mybatis_xml_mappers(directory, project_name, graph_db)
    for mapper in xml_mappers:
        graph_db.add_mybatis_mapper(mapper, project_name)
        stats['mybatis_mappers'] += 1

        # XML mapper의 SQL statements 즉시 추출 및 저장
        sql_statements = extract_sql_statements_from_mappers([mapper], project_name)
        if sql_statements:
            relationships = []
            for sql_statement in sql_statements:
                graph_db.add_sql_statement(sql_statement, project_name)
                relationships.append(
                    {
                        "mapper_name": sql_statement.mapper_name,
                        "sql_id": sql_statement.id,
                    }
                )
            if relationships:
                graph_db.add_mapper_sql_relationships_batch(relationships, project_name)
            stats['sql_statements'] += len(sql_statements)


    # 3. Config files 처리
    logger.info("Config files 처리 중...")
    config_files = extract_config_files(directory)
    for config in config_files:
        graph_db.add_config_file(config, project_name)
        stats['config_files'] += 1

    # 4. Bean 의존성 해결 (Neo4j 쿼리)
    if stats['beans'] > 0:
        logger.info("")
        from csa.services.java_analysis.bean_dependency_resolver import (
            resolve_bean_dependencies_from_neo4j
        )
        resolve_bean_dependencies_from_neo4j(graph_db, project_name, logger)

    logger.info(f"Java project streaming analysis complete:")
    logger.info(f"  - Java files processed: {stats['processed_files']}/{stats['total_files']}")
    logger.info(f"  - Packages found: {stats['packages']}")
    logger.info(f"  - Classes found: {stats['classes']}")
    logger.info(f"  - Beans: {stats['beans']}")
    logger.info(f"  - Endpoints: {stats['endpoints']}")
    logger.info(f"  - JPA Repositories: {stats['jpa_repositories']}")
    logger.info(f"  - JPA Queries: {stats['jpa_queries']}")
    logger.info(f"  - MyBatis Mappers: {stats['mybatis_mappers']}")
    logger.info(f"  - SQL Statements: {stats['sql_statements']}")

    return stats


def parse_java_project(directory: str, graph_db: GraphDB = None) -> list[Class]:
    """
    Compatibility wrapper that returns only the parsed classes.

    The full parser returns additional metadata required by the analyzer,
    but lightweight callers (including unit tests) expect only the class list.
    """

    # Provide legacy attribute accessors once at class definition level.
    if not hasattr(Class, "package"):
        setattr(Class, "package", property(lambda self: getattr(self, "package_name", "")))
    if not hasattr(Class, "project"):
        setattr(Class, "project", property(lambda self: getattr(self, "project_name", "")))

    _, classes, *_ = parse_java_project_full(directory, graph_db)
    return classes


__all__ = [
    "parse_java_project",
    "parse_java_project_full",
    "parse_java_project_streaming",
    "parse_single_java_file",
]

