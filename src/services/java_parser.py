import javalang
import os
from src.models.graph_entities import Class, Property, Method, MethodCall

def parse_java_project(directory: str) -> list[Class]:
    """Parses all Java files in a directory and returns a list of Class objects."""
    classes = {}

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".java"):
                file_path = os.path.join(root, file)
                with open(file_path, 'r', encoding='utf-8') as f:
                    try:
                        tree = javalang.parse.parse(f.read())
                        package_name = tree.package.name if tree.package else ""
                        
                        import_map = {}
                        for imp in tree.imports:
                            class_name = imp.path.split('.')[-1]
                            import_map[class_name] = imp.path

                        for _, class_declaration in tree.filter(javalang.tree.ClassDeclaration):
                            class_name = class_declaration.name
                            class_key = f"{package_name}.{class_name}"
                            
                            if class_key not in classes:
                                classes[class_key] = Class(
                                    name=class_name,
                                    package=package_name,
                                    file_path=file_path,
                                    type="class" # Simplified for now
                                )
                            
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

                                method = Method(
                                    name=declaration.name,
                                    return_type=return_type,
                                    parameters=params
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
                                            target_package = ""
                                            if target_class_name in import_map:
                                                target_package = ".".join(import_map[target_class_name].split('.')[:-1])
                                            else:
                                                target_package = package_name

                                            call = MethodCall(
                                                source_package=package_name,
                                                source_class=class_name,
                                                source_method=declaration.name,
                                                target_package=target_package,
                                                target_class=target_class_name,
                                                target_method=invocation.member
                                            )
                                            classes[class_key].calls.append(call)

                    except (javalang.tokenizer.LexerError, javalang.parser.JavaSyntaxError) as e:
                        print(f"Error parsing {file_path}: {e}")

    return list(classes.values())