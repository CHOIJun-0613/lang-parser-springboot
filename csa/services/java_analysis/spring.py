"""
Spring framework bean and endpoint extraction helpers.
"""
from __future__ import annotations

from typing import Dict, List

from csa.models.graph_entities import Bean, BeanDependency, Class, Endpoint


def extract_beans_from_classes(classes: list[Class]) -> list[Bean]:
    """Extract Spring Beans from parsed classes.
    
    Args:
        classes: List of parsed Class objects
        
    Returns:
        List of Bean objects
    """
    beans = []
    
    for cls in classes:
        component_annotations = [ann for ann in cls.annotations if ann.category == "component"]
        
        has_repository_annotation = any(ann.name == "Repository" for ann in cls.annotations)
        
        if component_annotations or has_repository_annotation:
            bean_type = "component"  # default
            if any(ann.name in ["Service", "Service"] for ann in cls.annotations):
                bean_type = "service"
            elif any(ann.name in ["Repository", "Repository"] for ann in cls.annotations):
                bean_type = "repository"
            elif any(ann.name in ["Controller", "RestController"] for ann in cls.annotations):
                bean_type = "controller"
            elif any(ann.name in ["Configuration", "Configuration"] for ann in cls.annotations):
                bean_type = "configuration"
            
            scope = "singleton"
            for ann in cls.annotations:
                if ann.name == "Scope":
                    if "value" in ann.parameters:
                        scope = ann.parameters["value"]
                    elif "prototype" in str(ann.parameters):
                        scope = "prototype"
                    elif "request" in str(ann.parameters):
                        scope = "request"
                    elif "session" in str(ann.parameters):
                        scope = "session"
            
            bean_name = cls.name[0].lower() + cls.name[1:] if cls.name else cls.name
            
            bean_methods = []
            if bean_type == "configuration":
                for method in cls.methods:
                    if any(ann.name == "Bean" for ann in method.annotations):
                        bean_methods.append(method)
            
            bean = Bean(
                name=bean_name,
                type=bean_type,
                scope=scope,
                class_name=cls.name,
                package_name=cls.package_name,
                annotation_names=[ann.name for ann in cls.annotations] if cls.annotations else [],
                method_count=len(bean_methods) if bean_type == "configuration" else len(cls.methods) if cls.methods else 0,
                property_count=len(cls.properties) if cls.properties else 0
            )
            beans.append(bean)
    
    return beans

def analyze_bean_dependencies(classes: list[Class], beans: list[Bean]) -> list[BeanDependency]:
    """Analyze dependencies between Spring Beans.
    
    Args:
        classes: List of parsed Class objects
        beans: List of Bean objects
        
    Returns:
        List of BeanDependency objects
    """
    dependencies = []
    
    class_to_bean = {}
    for bean in beans:
        class_to_bean[bean.class_name] = bean.name
    
    for cls in classes:
        if cls.name not in class_to_bean:
            continue
            
        source_bean = class_to_bean[cls.name]
        
        for prop in cls.properties:
            if any(ann.category == "injection" for ann in prop.annotations):
                target_bean = None
                field_type = prop.type
                
                if field_type in class_to_bean:
                    target_bean = class_to_bean[field_type]
                else:
                    for bean in beans:
                        if field_type == bean.class_name:
                            target_bean = bean.name
                            break
                
                if target_bean:
                    injection_type = "field"
                    for ann in prop.annotations:
                        if ann.name == "Autowired":
                            injection_type = "field"
                        elif ann.name == "Resource":
                            injection_type = "field"
                        elif ann.name == "Value":
                            injection_type = "field"
                    
                    dependency = BeanDependency(
                        source_bean=source_bean,
                        target_bean=target_bean,
                        injection_type=injection_type,
                        field_name=prop.name
                    )
                    dependencies.append(dependency)
        
        for method in cls.methods:
            if method.name == cls.name:  # Constructor
                for param in method.parameters:
                    if any(ann.category == "injection" for ann in param.annotations):
                        target_bean = None
                        param_type = param.type
                        
                        if param_type in class_to_bean:
                            target_bean = class_to_bean[param_type]
                        else:
                            for bean in beans:
                                if param_type == bean.class_name:
                                    target_bean = bean.name
                                    break
                        
                        if target_bean:
                            dependency = BeanDependency(
                                source_bean=source_bean,
                                target_bean=target_bean,
                                injection_type="constructor",
                                parameter_name=param.name
                            )
                            dependencies.append(dependency)
        
        for method in cls.methods:
            if method.name.startswith("set") and len(method.parameters) == 1:
                if any(ann.category == "injection" for ann in method.annotations):
                    param = method.parameters[0]
                    target_bean = None
                    param_type = param.type
                    
                    if param_type in class_to_bean:
                        target_bean = class_to_bean[param_type]
                    else:
                        for bean in beans:
                            if param_type == bean.class_name:
                                target_bean = bean.name
                                break
                    
                    if target_bean:
                        dependency = BeanDependency(
                            source_bean=source_bean,
                            target_bean=target_bean,
                            injection_type="setter",
                            method_name=method.name,
                            parameter_name=param.name
                        )
                        dependencies.append(dependency)
    
    return dependencies

def extract_endpoints_from_classes(classes: list[Class]) -> list[Endpoint]:
    """Extract REST API endpoints from controller classes.
    
    Args:
        classes: List of parsed Class objects
        
    Returns:
        List of Endpoint objects
    """
    endpoints = []
    
    for cls in classes:
        is_controller = any(ann.name in ["Controller", "RestController"] for ann in cls.annotations)
        
        if not is_controller:
            continue
            
        class_path = ""
        for ann in cls.annotations:
            if ann.name == "RequestMapping":
                if "value" in ann.parameters:
                    class_path = ann.parameters["value"]
                break
        
        for method in cls.methods:
            if method.name == cls.name:
                continue
                
            web_annotations = [ann for ann in method.annotations if ann.category == "web"]
            
            if not web_annotations:
                continue
            
            endpoint_path = ""
            http_method = "GET"  # default
            
            for ann in web_annotations:
                if ann.name in ["RequestMapping", "GetMapping", "PostMapping", "PutMapping", "DeleteMapping", "PatchMapping"]:
                    if "value" in ann.parameters:
                        endpoint_path = ann.parameters["value"]
                    elif "path" in ann.parameters:
                        endpoint_path = ann.parameters["path"]
                    
                    if ann.name == "GetMapping":
                        http_method = "GET"
                    elif ann.name == "PostMapping":
                        http_method = "POST"
                    elif ann.name == "PutMapping":
                        http_method = "PUT"
                    elif ann.name == "DeleteMapping":
                        http_method = "DELETE"
                    elif ann.name == "PatchMapping":
                        http_method = "PATCH"
                    elif ann.name == "RequestMapping":
                        if "method" in ann.parameters:
                            method_value = ann.parameters["method"]
                            if isinstance(method_value, list) and len(method_value) > 0:
                                http_method = method_value[0]
                            else:
                                http_method = str(method_value)
                        else:
                            http_method = "GET"  # default for RequestMapping
                    break
            
            full_path = class_path
            if endpoint_path:
                if full_path and not full_path.endswith("/") and not endpoint_path.startswith("/"):
                    full_path += "/"
                full_path += endpoint_path
            elif not full_path:
                full_path = "/"
            
            parameters = []
            for param in method.parameters:
                param_info = {
                    "name": param.name,
                    "type": param.type,
                    "annotations": [ann.name for ann in param.annotations if ann.category == "web"]
                }
                parameters.append(param_info)
            
            return_type = method.return_type if method.return_type != "constructor" else "void"
            
            endpoint = Endpoint(
                path=endpoint_path or "/",
                method=http_method,
                controller_class=cls.name,
                handler_method=method.name,
                parameters=parameters,
                return_type=return_type,
                annotations=[ann.name for ann in web_annotations],
                full_path=full_path
            )
            endpoints.append(endpoint)
    
    return endpoints

__all__ = [
    "analyze_bean_dependencies",
    "extract_beans_from_classes",
    "extract_endpoints_from_classes",
]
