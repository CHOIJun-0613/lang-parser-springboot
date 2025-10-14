"""
Java project parsing orchestration helpers.
"""
from __future__ import annotations

import os
import re
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

def parse_single_java_file(file_path: str, project_name: str, graph_db: GraphDB = None) -> tuple[Package, Class, str]:
    """Parse a single Java file and return parsed entities."""
    logger = get_logger(__name__)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        file_content = f.read()
    
    try:
        tree = javalang.parse.parse(file_content)
        logger.info(f"Successfully parsed file: {file_path}")
        
        package_name = tree.package.name if tree.package else ""
        logger.info(f"Parsed package name: {package_name}")
        
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
            return None, None, ""
        
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
            ai_description=""
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
                                        resolved_target_package = package_name
                                        
                                        # 패키지 기반 추론 로직
                                        if package_name and 'controller' in package_name:
                                            service_package = package_name.replace('controller', 'service')
                                            resolved_target_package = service_package
                                        
                                        elif package_name and 'domain' in package_name:
                                            domain_parts = package_name.split('.')
                                            if len(domain_parts) >= 3:
                                                domain_base = '.'.join(domain_parts[:3])
                                                service_package = f"{domain_base}.{domain_parts[2]}.service"
                                                resolved_target_package = service_package
                                
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
        
        logger.info(f"Successfully parsed single file: {file_path}")
        return package_node, class_node, package_name
        
    except Exception as e:
        logger.error(f"Error parsing file: {e}")
        return None, None, ""

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
                                                    resolved_target_package = package_name
                                                    
                                                    if package_name and 'controller' in package_name:
                                                        service_package = package_name.replace('controller', 'service')
                                                        resolved_target_package = service_package
                                                    
                                                    elif package_name and 'domain' in package_name:
                                                        domain_parts = package_name.split('.')
                                                        if len(domain_parts) >= 3:
                                                            domain_base = '.'.join(domain_parts[:3])
                                                            service_package = f"{domain_base}.{domain_parts[2]}.service"
                                                            resolved_target_package = service_package
                                                
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
    dependencies = analyze_bean_dependencies(classes_list, beans)
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
    "parse_single_java_file",
]

