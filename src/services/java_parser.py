import os

import javalang

from src.models.graph_entities import Class, Method, MethodCall, Property


def parse_java_project(directory: str) -> list[Class]:
    """Parses all Java files in a directory and returns a list of Class objects."""
    classes = {}

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".java"):
                file_path = os.path.join(root, file)
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_content = f.read() # Read file content once
                try:
                    tree = javalang.parse.parse(file_content)
                    package_name = tree.package.name if tree.package else ""
                    
                    import_map = {}
                    for imp in tree.imports:
                        class_name = imp.path.split('.')[-1]
                        import_map[class_name] = imp.path

                    for _, class_declaration in tree.filter(
                        javalang.tree.ClassDeclaration
                    ):
                        class_name = class_declaration.name
                        class_key = f"{package_name}.{class_name}"
                        
                        # Extract class source code - use the entire file content
                        class_source = file_content


                        if class_key not in classes:
                            classes[class_key] = Class(
                                name=class_name,
                                package=package_name,
                                file_path=file_path,
                                type="class", # Simplified for now
                                source=class_source # Add class source
                            )
                        
                        # --- Start of new import logic ---
                        for imp in tree.imports:
                            classes[class_key].imports.append(imp.path)
                        # --- End of new import logic ---

                        # --- Start of new inheritance logic ---
                        # Handle 'extends'
                        if class_declaration.extends:
                            superclass_name = class_declaration.extends.name
                            # Try to resolve fully qualified name for superclass
                            if superclass_name in import_map:
                                classes[class_key].superclass = import_map[superclass_name]
                            else:
                                # Assume same package or fully qualified if not in import_map
                                classes[class_key].superclass = f"{package_name}.{superclass_name}" if package_name else superclass_name

                        # Handle 'implements'
                        if class_declaration.implements: # Add this check
                            for impl_ref in class_declaration.implements:
                                interface_name = impl_ref.name
                                # Try to resolve fully qualified name for interface
                                if interface_name in import_map:
                                    classes[class_key].interfaces.append(import_map[interface_name])
                                else:
                                    # Assume same package or fully qualified if not in import_map
                                    classes[class_key].interfaces.append(f"{package_name}.{interface_name}" if package_name else interface_name)
                        # --- End of new inheritance logic ---

                        field_map = {}
                        for field_declaration in class_declaration.fields:
                            for declarator in field_declaration.declarators:
                                field_map[declarator.name] = field_declaration.type.name
                                prop = Property(
                                    name=declarator.name,
                                    type=field_declaration.type.name
                                )
                                classes[class_key].properties.append(prop)

                        all_declarations = class_declaration.methods + class_declaration.constructors
                        for declaration in all_declarations:
                            local_var_map = field_map.copy()
                            params = []
                            for param in declaration.parameters:
                                param_type_name = 'Unknown'
                                if hasattr(param.type, 'name'):
                                    param_type_name = param.type.name
                                local_var_map[param.name] = param_type_name
                                params.append(Property(name=param.name, type=param_type_name))

                            if declaration.body:
                                for _, var_decl in declaration.filter(javalang.tree.LocalVariableDeclaration):
                                    for declarator in var_decl.declarators:
                                        local_var_map[declarator.name] = var_decl.type.name
                            
                            if isinstance(declaration, javalang.tree.MethodDeclaration):
                                return_type = declaration.return_type.name if declaration.return_type else "void"
                            else: # ConstructorDeclaration
                                return_type = "constructor"

                            # --- Start of new visibility logic ---
                            visibility = "package-private" # Default
                            if "public" in declaration.modifiers:
                                visibility = "public"
                            elif "private" in declaration.modifiers:
                                visibility = "private"
                            elif "protected" in declaration.modifiers:
                                visibility = "protected"
                            # --- End of new visibility logic ---

                            # Extract method source code
                            method_source = ""
                            if declaration.position:
                                lines = file_content.splitlines(keepends=True) # Keep line endings
                                start_line = declaration.position.line - 1
                                
                                # Find the end of the method by matching braces
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

                            method = Method(
                                name=declaration.name,
                                return_type=return_type,
                                parameters=params,
                                visibility=visibility,
                                source=method_source # Add method source
                            )
                            classes[class_key].methods.append(method)

                            for _, invocation in declaration.filter(javalang.tree.MethodInvocation):
                                if invocation.qualifier:
                                    target_class_name = None
                                    if invocation.qualifier in local_var_map:
                                        target_class_name = local_var_map[invocation.qualifier]
                                    else:
                                        target_class_name = invocation.qualifier

                                    if target_class_name:
                                        resolved_target_package = ""
                                        resolved_target_class_name = target_class_name

                                        if target_class_name == "System.out":
                                            resolved_target_package = "java.io"
                                            resolved_target_class_name = "PrintStream"
                                        else:
                                            if target_class_name in import_map:
                                                resolved_target_package = ".".join(import_map[target_class_name].split(".")[:-1])
                                            else:
                                                resolved_target_package = package_name

                                        call = MethodCall(
                                            source_package=package_name,
                                            source_class=class_name,
                                            source_method=declaration.name,
                                            target_package=resolved_target_package,
                                            target_class=resolved_target_class_name,
                                            target_method=invocation.member
                                        )
                                        classes[class_key].calls.append(call)
                except javalang.parser.JavaSyntaxError as e:
                    print(f"Syntax error in {file_path}: {e}")
                    continue
                except Exception as e:
                    print(f"Error parsing {file_path}: {e}")
                    continue
    
    return list(classes.values())