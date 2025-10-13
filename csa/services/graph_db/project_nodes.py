from __future__ import annotations

import json
from typing import Any, Optional

from csa.models.graph_entities import Class, Package, Project
from csa.services.graph_db.base import GraphDBBase
from csa.utils.logger import get_logger


class ProjectMixin:
    """Manage project, package, and class nodes."""

    def add_project(self, project: Project) -> None:
        """Add or update a project node."""
        self._execute_write(self._create_project_node_tx, project)

    @staticmethod
    def _create_project_node_tx(tx, project: Project) -> None:
        """Transaction that creates or updates a project node."""
        current_timestamp = GraphDBBase._get_current_timestamp()
        created_at = project.created_at if project.created_at else current_timestamp
        project_query = (
            "MERGE (p:Project {name: $name}) "
            "SET p.display_name = $display_name, "
            "p.description = $description, "
            "p.repository_url = $repository_url, "
            "p.language = $language, "
            "p.framework = $framework, "
            "p.version = $version, "
            "p.ai_description = $ai_description, "
            "p.updated_at = $updated_at, "
            "p.created_at = COALESCE(p.created_at, $created_at)"
        )
        tx.run(
            project_query,
            name=project.name,
            display_name=project.display_name or "",
            description=project.description or "",
            repository_url=project.repository_url or "",
            language=project.language or "Java",
            framework=project.framework or "",
            version=project.version or "",
            ai_description=project.ai_description or "",
            updated_at=current_timestamp,
            created_at=created_at,
        )

    def add_package(self, package_node: Package, project_name: str) -> None:
        """Add or update a package node."""
        self._execute_write(self._create_package_node_tx, package_node, project_name)

    @staticmethod
    def _create_package_node_tx(tx, package_node: Package, project_name: str) -> None:
        """Transaction that creates or updates a package node."""
        current_timestamp = GraphDBBase._get_current_timestamp()
        package_query = (
            "MERGE (p:Package {name: $name}) "
            "SET p.project_name = $project_name, p.description = $description, p.ai_description = $ai_description, "
            "p.updated_at = $updated_at"
        )
        tx.run(
            package_query,
            name=package_node.name,
            project_name=project_name,
            description=package_node.description or "",
            ai_description=package_node.ai_description or "",
            updated_at=current_timestamp,
        )
        project_package_query = (
            "MATCH (proj:Project {name: $project_name}) "
            "MATCH (pkg:Package {name: $package_name}) "
            "MERGE (proj)-[:CONTAINS]->(pkg)"
        )
        tx.run(
            project_package_query,
            project_name=project_name,
            package_name=package_node.name,
        )

    def add_class(
        self,
        class_node: Class,
        package_name: Optional[str] = None,
        project_name: Optional[str] = None,
    ) -> None:
        """Add a class node and all dependent relationships."""
        package_name = package_name or getattr(class_node, "package_name", None) or getattr(class_node, "package", "")
        project_name = project_name or getattr(class_node, "project_name", None) or getattr(class_node, "project", "")
        self.logger.debug(f"Adding class: {class_node.name}, package: {package_name}, project: {project_name}")
        try:
            self._execute_write(self._create_class_node_tx, class_node, package_name, project_name)
            self.logger.debug(f"Successfully added class: {class_node.name}")
        except Exception as exc:
            self.logger.error(f"Error adding class {class_node.name}: {exc}")
            raise

    @staticmethod
    def _create_class_node_tx(tx, class_node: Class, package_name: str, project_name: str) -> None:
        """Transaction that creates a class node and all related entities."""
        logger = get_logger(__name__)
        logger.debug(f"Creating class node: {class_node.name}")
        current_timestamp = GraphDBBase._get_current_timestamp()
        existing_method_names = {method.name for method in getattr(class_node, "methods", [])}

        def _normalise_annotation_params(raw: Any) -> dict[str, Any]:
            """어노테이션 파라미터를 안전한 dict 형태로 정규화한다."""
            if raw is None:
                return {}
            if isinstance(raw, dict):
                return raw
            if isinstance(raw, (list, tuple, set)):
                normalised: dict[str, Any] = {}
                for idx, item in enumerate(raw):
                    if isinstance(item, (list, tuple)) and len(item) == 2:
                        key, value = item
                        normalised[str(key)] = value
                    else:
                        normalised[str(idx)] = item
                return normalised
            return {"value": raw}
        class_query = (
            "MERGE (c:Class {name: $name, package: $package}) "
            "SET c.file_path = $file_path, c.type = $type, c.sub_type = $sub_type, "
            "c.source = $source, c.logical_name = $logical_name, "
            "c.superclass = $superclass, c.interfaces = $interfaces, "
            "c.imports = $imports, c.package_name = $package_name, c.package = $package_name, "
            "c.project_name = $project_name, c.description = $description, c.ai_description = $ai_description, "
            "c.updated_at = $updated_at"
        )
        tx.run(
            class_query,
            name=class_node.name,
            file_path=class_node.file_path,
            type=class_node.type,
            sub_type=class_node.sub_type or "",
            source=class_node.source,
            logical_name=class_node.logical_name,
            superclass=class_node.superclass,
            interfaces=class_node.interfaces,
            imports=class_node.imports,
            package_name=package_name,
            package=package_name,
            project_name=project_name,
            description=class_node.description or "",
            ai_description=class_node.ai_description or "",
            updated_at=current_timestamp,
        )
        if package_name:
            package_class_query = (
                "MATCH (p:Package {name: $package_name}) "
                "MATCH (c:Class {name: $class_name}) "
                "MERGE (p)-[:CONTAINS]->(c)"
            )
            tx.run(
                package_class_query,
                package_name=package_name,
                class_name=class_node.name,
            )
        project_class_query = (
            "MATCH (proj:Project {name: $project_name}) "
            "MATCH (c:Class {name: $class_name}) "
            "MERGE (proj)-[:CONTAINS]->(c)"
        )
        tx.run(
            project_class_query,
            project_name=project_name,
            class_name=class_node.name,
        )
        for import_class in class_node.imports:
            import_query = (
                "MERGE (imp:Class {name: $import_class}) "
                "MERGE (c:Class {name: $class_name}) "
                "MERGE (c)-[:IMPORTS]->(imp)"
            )
            tx.run(
                import_query,
                import_class=import_class,
                class_name=class_node.name,
            )
        for annotation in class_node.annotations:
            annotation_name = getattr(annotation, "name", str(annotation))
            annotation_query = (
                "MATCH (c:Class {name: $class_name}) "
                "MERGE (a:Annotation {name: $annotation_name}) "
                "MERGE (c)-[:ANNOTATED_WITH]->(a)"
            )
            tx.run(
                annotation_query,
                class_name=class_node.name,
                annotation_name=annotation_name,
            )
        if class_node.superclass:
            superclass_query = (
                "MERGE (super:Class {name: $superclass}) "
                "MERGE (c:Class {name: $class_name}) "
                "MERGE (c)-[:EXTENDS]->(super)"
            )
            tx.run(
                superclass_query,
                superclass=class_node.superclass,
                class_name=class_node.name,
            )
        for interface in class_node.interfaces:
            interface_query = (
                "MERGE (i:Interface {name: $interface}) "
                "MERGE (c:Class {name: $class_name}) "
                "MERGE (c)-[:IMPLEMENTS]->(i)"
            )
            tx.run(
                interface_query,
                interface=interface,
                class_name=class_node.name,
            )
        for method in class_node.methods:
            method_annotations = getattr(method, "annotations", [])
            serialized_annotations: list[dict[str, Any]] = []
            for annotation in method_annotations:
                annotation_name = getattr(annotation, "name", str(annotation))
                raw_params = getattr(annotation, "parameters", {})
                params_dict = _normalise_annotation_params(raw_params)
                serialized_annotations.append({"name": annotation_name, "parameters": params_dict})

            visibility = getattr(method, "visibility", None)
            if not visibility:
                visibility = next(
                    (
                        modifier
                        for modifier in getattr(method, "modifiers", [])
                        if modifier in {"public", "protected", "private"}
                    ),
                    "package",
                )

            method_parameters = getattr(method, "parameters", [])
            serialized_parameters: list[dict[str, Any]] = []
            for index, param in enumerate(method_parameters, start=1):
                if isinstance(param, dict):
                    param_name = param.get("name") or f"param_{index}"
                    param_type = param.get("type", "")
                    param_description = param.get("description", "")
                    param_ai_description = param.get("ai_description", "")
                    param_package_name = param.get("package_name", package_name)
                    annotation_source = param.get("annotations", [])
                else:
                    param_name = getattr(param, "name", None) or f"param_{index}"
                    param_type = getattr(param, "type", "")
                    param_description = getattr(param, "description", "")
                    param_ai_description = getattr(param, "ai_description", "")
                    param_package_name = getattr(param, "package_name", package_name)
                    annotation_source = getattr(param, "annotations", [])

                normalized_param_annotations = []
                for ann in annotation_source or []:
                    if isinstance(ann, dict):
                        ann_name = ann.get("name", str(ann))
                        params_raw = ann.get("parameters", {})
                    else:
                        ann_name = getattr(ann, "name", str(ann))
                        params_raw = getattr(ann, "parameters", {})
                    params_normalized = _normalise_annotation_params(params_raw)
                    normalized_param_annotations.append({"name": ann_name, "parameters": params_normalized})

                param_serialized = {
                    "name": param_name,
                    "type": param_type or "",
                    "order": index,
                    "description": param_description or "",
                    "ai_description": param_ai_description or "",
                    "package_name": param_package_name or package_name,
                }
                if normalized_param_annotations:
                    param_serialized["annotations"] = normalized_param_annotations

                serialized_parameters.append(param_serialized)

            method_query = (
                "MATCH (c:Class {name: $class_name}) "
                "MERGE (m:Method {name: $method_name, class_name: $class_name}) "
                "SET m.return_type = $return_type, m.parameters = $parameters_json, "
                "m.annotations = $annotations_json, m.visibility = $visibility, "
                "m.description = $description, m.ai_description = $ai_description, "
                "m.logical_name = $logical_name, "
                "m.package_name = $package_name, m.project_name = $project_name, "
                "m.updated_at = $updated_at "
                "MERGE (c)-[:HAS_METHOD]->(m)"
            )
            try:
                tx.run(
                    method_query,
                    class_name=class_node.name,
                    method_name=method.name,
                    return_type=getattr(method, "return_type", "") or "",
                    parameters_json=json.dumps(serialized_parameters),
                    annotations_json=json.dumps(serialized_annotations),
                    visibility=visibility,
                    description=getattr(method, "description", "") or "",
                    ai_description=getattr(method, "ai_description", "") or "",
                    logical_name=getattr(method, "logical_name", "") or "",
                    package_name=package_name,
                    project_name=project_name,
                    updated_at=current_timestamp,
                )
            except (TypeError, ValueError) as exc:
                logger.error(
                    "Method serialization error: %s.%s -> %s | annotations=%s | parameters=%s",
                    class_node.name,
                    method.name,
                    exc,
                    serialized_annotations,
                    serialized_parameters,
                )
                raise
            for exception in getattr(method, "throws", []):
                throws_query = (
                    "MATCH (m:Method {name: $method_name, class_name: $class_name}) "
                    "MERGE (e:Exception {name: $exception}) "
                    "MERGE (m)-[:THROWS]->(e)"
                )
                tx.run(
                    throws_query,
                    method_name=method.name,
                    class_name=class_node.name,
                    exception=exception,
                )
            for annotation in method_annotations:
                annotation_name = getattr(annotation, "name", str(annotation))
                method_annotation_query = (
                    "MATCH (m:Method {name: $method_name, class_name: $class_name}) "
                    "MERGE (a:Annotation {name: $annotation}) "
                    "MERGE (m)-[:ANNOTATED_WITH]->(a)"
                )
                tx.run(
                    method_annotation_query,
                    method_name=method.name,
                    class_name=class_node.name,
                    annotation=annotation_name,
                )
            for param_info in serialized_parameters:
                param_query = (
                    "MATCH (m:Method {name: $method_name, class_name: $class_name}) "
                    "MERGE (p:Parameter {name: $param_name, method_name: $method_name, class_name: $class_name}) "
                    "SET p.type = $param_type, p.description = $param_description, p.ai_description = $param_ai_description, "
                    "p.package_name = $package_name, p.project_name = $project_name, p.updated_at = $updated_at "
                    "MERGE (m)-[:HAS_PARAMETER]->(p)"
                )
                try:
                    tx.run(
                        param_query,
                        method_name=method.name,
                        class_name=class_node.name,
                        param_name=param_info["name"],
                        param_type=param_info.get("type", ""),
                        param_description=param_info.get("description", ""),
                        param_ai_description=param_info.get("ai_description", ""),
                        package_name=param_info.get("package_name", package_name),
                        project_name=project_name,
                        updated_at=current_timestamp,
                    )
                except (TypeError, ValueError) as exc:
                    logger.error(
                        "Parameter serialization error: %s.%s(%s) -> %s | data=%s",
                        class_node.name,
                        method.name,
                        param_info["name"],
                        exc,
                        param_info,
                    )
                    raise
            if getattr(method, "return_type", None):
                return_query = (
                    "MATCH (m:Method {name: $method_name, class_name: $class_name}) "
                    "MERGE (r:ReturnType {name: $return_type, method_name: $method_name, class_name: $class_name}) "
                    "SET r.description = $return_description, r.ai_description = $return_ai_description, "
                    "r.package_name = $package_name, r.project_name = $project_name, r.updated_at = $updated_at "
                    "MERGE (m)-[:RETURNS]->(r)"
                )
                tx.run(
                    return_query,
                    method_name=method.name,
                    class_name=class_node.name,
                    return_type=method.return_type,
                    return_description=getattr(method, "return_description", "") or "",
                    return_ai_description=getattr(method, "return_ai_description", "") or "",
                    package_name=package_name,
                    project_name=project_name,
                    updated_at=current_timestamp,
                )
            for statement in getattr(method, "statements", []):
                statement_query = (
                    "MATCH (m:Method {name: $method_name, class_name: $class_name}) "
                    "MERGE (s:Statement {index: $statement_index, method_name: $method_name, class_name: $class_name}) "
                    "SET s.type = $statement_type, s.content = $statement_content, s.updated_at = $updated_at "
                    "MERGE (m)-[:HAS_STATEMENT]->(s)"
                )
                tx.run(
                    statement_query,
                    method_name=method.name,
                    class_name=class_node.name,
                    statement_index=getattr(statement, "index", 0),
                    statement_type=getattr(statement, "type", ""),
                    statement_content=getattr(statement, "content", ""),
                    updated_at=current_timestamp,
                )
        for prop in class_node.properties:
            prop_modifiers_json = json.dumps(prop.modifiers) if prop.modifiers else json.dumps([])
            prop_annotations_json = json.dumps(
                [
                    {
                        "name": a.name,
                        "parameters": _normalise_annotation_params(getattr(a, "parameters", {})),
                    }
                    for a in prop.annotations
                ]
            )
            prop_query = (
                "MATCH (c:Class {name: $class_name}) "
                "MERGE (p:Field {name: $prop_name, class_name: $class_name, project_name: $project_name}) "
                "SET p.type = $prop_type, "
                "p.logical_name = $prop_logical_name, "
                "p.modifiers_json = $prop_modifiers_json, "
                "p.annotations_json = $prop_annotations_json, "
                "p.initial_value = $prop_initial_value, "
                "p.package_name = $package_name, "
                "p.project_name = $project_name, "
                "p.description = $prop_description, "
                "p.ai_description = $prop_ai_description, "
                "p.updated_at = $updated_at "
                "MERGE (c)-[:HAS_FIELD]->(p)"
            )
            tx.run(
                prop_query,
                class_name=class_node.name,
                prop_name=prop.name,
                prop_type=prop.type,
                prop_logical_name=prop.logical_name or "",
                prop_modifiers_json=prop_modifiers_json,
                prop_annotations_json=prop_annotations_json,
                prop_initial_value=prop.initial_value or "",
                package_name=prop.package_name,
                project_name=project_name,
                prop_description=prop.description or "",
                prop_ai_description=prop.ai_description or "",
                updated_at=current_timestamp,
            )
        for method_call in class_node.calls:
            if not getattr(method_call, "target_class", "") or not getattr(method_call, "target_method", ""):
                logger.debug(
                    "Skipping method call with incomplete target: %s.%s -> %s.%s",
                    class_node.name,
                    getattr(method_call, "source_method", ""),
                    getattr(method_call, "target_class", ""),
                    getattr(method_call, "target_method", ""),
                )
                continue

            if (
                method_call.target_class == class_node.name
                and method_call.target_method not in existing_method_names
            ):
                logger.debug(
                    "Skipping unresolved self-call %s.%s (method not declared)",
                    class_node.name,
                    method_call.target_method,
                )
                continue

            target_class_query = (
                "MERGE (tc:Class {name: $target_class})"
            )
            tx.run(
                target_class_query,
                target_class=method_call.target_class,
            )
            target_method_query = (
                "MATCH (tc:Class {name: $target_class}) "
                "MERGE (tm:Method {name: $target_method, class_name: $target_class}) "
                "MERGE (tc)-[:HAS_METHOD]->(tm)"
            )
            tx.run(
                target_method_query,
                target_class=method_call.target_class,
                target_method=method_call.target_method,
            )
            call_query = (
                "MATCH (sm:Method {name: $source_method, class_name: $source_class}) "
                "MATCH (tm:Method {name: $target_method, class_name: $target_class}) "
                "MERGE (sm)-[r:CALLS]->(tm) "
                "SET r.source_package = $source_package, "
                "r.source_class = $source_class, "
                "r.source_method = $source_method, "
                "r.target_package = $target_package, "
                "r.target_class = $target_class, "
                "r.target_method = $target_method, "
                "r.call_order = $call_order, "
                "r.line_number = $line_number"
            )
            tx.run(
                call_query,
                source_method=method_call.source_method,
                source_class=class_node.name,
                source_package=package_name,
                target_method=method_call.target_method,
                target_class=method_call.target_class,
                target_package=method_call.target_package,
                call_order=method_call.call_order,
                line_number=method_call.line_number,
            )
