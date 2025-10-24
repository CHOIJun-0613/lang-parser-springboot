from __future__ import annotations

import json
from typing import Any, Optional

from csa.models.graph_entities import Class, Package, Project
from csa.services.graph_db.base import GraphDBBase
from csa.utils.logger import get_logger
from csa.utils.class_helpers import (
    is_external_library,
    extract_package_from_full_name,
    is_inner_class,
    extract_outer_class_name,
)


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
            "SET p.description = $description, "
            "p.ai_description = $ai_description, "
            "p.application_name = $application_name, "
            "p.number_of_files = $number_of_files, "
            "p.path = $path, "
            "p.updated_at = $updated_at, "
            "p.created_at = COALESCE(p.created_at, $created_at)"
        )
        tx.run(
            project_query,
            name=project.name or "",
            description=project.description or "",
            ai_description=project.ai_description or "",
            application_name=project.application_name or "",
            number_of_files=int(project.number_of_files or 0),
            path=project.path or "",
            updated_at=current_timestamp,
            created_at=created_at,
        )

    def add_package(self, package_node: Package, project_name: str) -> None:
        """Add or update a package node."""
        self._execute_write(self._create_package_node_tx, package_node, project_name)

    def add_packages_batch(self, packages: list[Package], project_name: str) -> None:
        """
        여러 패키지를 배치로 한 번에 저장 (성능 최적화)

        Args:
            packages: Package 노드 리스트
            project_name: 프로젝트명
        """
        if not packages:
            return
        self._execute_write(self._create_packages_batch_tx, packages, project_name)

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

    @staticmethod
    def _create_packages_batch_tx(tx, packages: list[Package], project_name: str) -> None:
        """
        여러 패키지를 배치로 생성하는 트랜잭션

        Args:
            tx: Neo4j 트랜잭션
            packages: Package 노드 리스트
            project_name: 프로젝트명
        """
        current_timestamp = GraphDBBase._get_current_timestamp()

        # 1. Package 노드 배치 생성
        package_records = []
        for pkg in packages:
            package_records.append({
                'name': pkg.name,
                'project_name': project_name,
                'description': pkg.description or "",
                'ai_description': pkg.ai_description or "",
                'updated_at': current_timestamp,
            })

        if package_records:
            tx.run(
                """
                UNWIND $packages AS pkg
                MERGE (p:Package {name: pkg.name})
                SET p.project_name = pkg.project_name,
                    p.description = pkg.description,
                    p.ai_description = pkg.ai_description,
                    p.updated_at = pkg.updated_at
                """,
                packages=package_records
            )

        # 2. Project-Package 관계 배치 생성
        project_package_records = []
        for pkg in packages:
            project_package_records.append({
                'project_name': project_name,
                'package_name': pkg.name,
            })

        if project_package_records:
            tx.run(
                """
                UNWIND $relations AS rel
                MATCH (proj:Project {name: rel.project_name})
                MATCH (pkg:Package {name: rel.package_name})
                MERGE (proj)-[:CONTAINS]->(pkg)
                """,
                relations=project_package_records
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
        self.logger.debug(f"Adding class: {class_node.name}, package_name: {package_name}, project: {project_name}")
        try:
            self._execute_write(self._create_class_node_tx, class_node, package_name, project_name)
            self.logger.debug(f"Successfully added class: {class_node.name}")
        except Exception as exc:
            self.logger.error(f"Error adding class {class_node.name}: {exc}")
            raise

    def add_classes_batch(
        self,
        classes_data: list[tuple[Class, str, str]],
    ) -> None:
        """
        여러 클래스를 배치로 한 번에 저장 (성능 최적화)

        Args:
            classes_data: [(class_node, package_name, project_name), ...] 튜플 리스트
        """
        if not classes_data:
            return

        self.logger.debug(f"Adding {len(classes_data)} classes in batch...")
        try:
            self._execute_write(self._create_classes_batch_tx, classes_data)
            self.logger.debug(f"Successfully added {len(classes_data)} classes in batch")
        except Exception as exc:
            self.logger.error(f"Error adding classes batch: {exc}")
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
            "MERGE (c:Class {name: $name, package_name: $package_name}) "
            "SET c.file_path = $file_path, c.type = $type, c.sub_type = $sub_type, "
            "c.source = $source, c.logical_name = $logical_name, "
            "c.superclass = $superclass, c.interfaces = $interfaces, "
            "c.imports = $imports, c.package_name = $package_name, "
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
            project_name=project_name,
            description=class_node.description or "",
            ai_description=class_node.ai_description or "",
            updated_at=current_timestamp,
        )
        if package_name:
            package_class_query = (
                "MATCH (p:Package {name: $package_name}) "
                "MATCH (c:Class {name: $class_name, package_name: $package_name}) "
                "MERGE (p)-[:CONTAINS]->(c)"
            )
            tx.run(
                package_class_query,
                package_name=package_name,
                class_name=class_node.name,
            )
        project_class_query = (
            "MATCH (proj:Project {name: $project_name}) "
            "MATCH (c:Class {name: $class_name, package_name: $package_name}) "
            "MERGE (proj)-[:CONTAINS]->(c)"
        )
        tx.run(
            project_class_query,
            project_name=project_name,
            class_name=class_node.name,
            package_name=package_name,
        )
        for import_class in class_node.imports:
            if is_external_library(import_class):
                # 외부 라이브러리: name만 사용, package는 빈 문자열
                import_query = (
                    "MERGE (imp:Class {name: $import_class, package_name: ''}) "
                    "SET imp.is_external = true "
                    "WITH imp "
                    "MATCH (c:Class {name: $class_name, package_name: $package_name}) "
                    "MERGE (c)-[:IMPORTS]->(imp)"
                )
                tx.run(
                    import_query,
                    import_class=import_class,
                    class_name=class_node.name,
                    package_name=package_name,
                )
            else:
                # 프로젝트 내부: name + package 조합
                simple_name, import_package = extract_package_from_full_name(import_class)
                import_query = (
                    "MERGE (imp:Class {name: $import_name, package_name: $import_package}) "
                    "SET imp.is_external = false "
                    "WITH imp "
                    "MATCH (c:Class {name: $class_name, package_name: $package_name}) "
                    "MERGE (c)-[:IMPORTS]->(imp)"
                )
                tx.run(
                    import_query,
                    import_name=simple_name,
                    import_package=import_package or "",
                    class_name=class_node.name,
                    package_name=package_name,
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
            if is_external_library(class_node.superclass):
                superclass_query = (
                    "MERGE (super:Class {name: $superclass, package_name: ''}) "
                    "SET super.is_external = true "
                    "WITH super "
                    "MATCH (c:Class {name: $class_name, package_name: $package_name}) "
                    "MERGE (c)-[:EXTENDS]->(super)"
                )
                tx.run(
                    superclass_query,
                    superclass=class_node.superclass,
                    class_name=class_node.name,
                    package_name=package_name,
                )
            else:
                simple_name, super_package = extract_package_from_full_name(class_node.superclass)
                superclass_query = (
                    "MERGE (super:Class {name: $superclass, package_name: $super_package}) "
                    "SET super.is_external = false "
                    "WITH super "
                    "MATCH (c:Class {name: $class_name, package_name: $package_name}) "
                    "MERGE (c)-[:EXTENDS]->(super)"
                )
                tx.run(
                    superclass_query,
                    superclass=simple_name,
                    super_package=super_package or "",
                    class_name=class_node.name,
                    package_name=package_name,
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
        method_records: list[dict[str, Any]] = []
        method_annotation_records: list[dict[str, str]] = []
        throws_records: list[dict[str, str]] = []
        parameter_records: list[dict[str, Any]] = []
        return_records: list[dict[str, Any]] = []
        statement_records: list[dict[str, Any]] = []

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

            try:
                parameters_json = json.dumps(serialized_parameters)
                annotations_json = json.dumps(serialized_annotations)
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
            method_records.append(
                {
                    "class_name": class_node.name,
                    "method_name": method.name,
                    "package_name": package_name,
                    "project_name": project_name,
                    "return_type": getattr(method, "return_type", "") or "",
                    "parameters_json": parameters_json,
                    "annotations_json": annotations_json,
                    "visibility": visibility,
                    "description": getattr(method, "description", "") or "",
                    "ai_description": getattr(method, "ai_description", "") or "",
                    "logical_name": getattr(method, "logical_name", "") or "",
                    "updated_at": current_timestamp,
                }
            )

            for annotation in method_annotations:
                annotation_name = getattr(annotation, "name", str(annotation))
                method_annotation_records.append(
                    {
                        "method_name": method.name,
                        "class_name": class_node.name,
                        "annotation_name": annotation_name,
                    }
                )
            for exception in getattr(method, "throws", []):
                throws_records.append(
                    {
                        "method_name": method.name,
                        "class_name": class_node.name,
                        "exception": exception,
                    }
                )
            for param_info in serialized_parameters:
                parameter_records.append(
                    {
                        "method_name": method.name,
                        "class_name": class_node.name,
                        "param_name": param_info["name"],
                        "param_type": param_info.get("type", ""),
                        "param_description": param_info.get("description", ""),
                        "param_ai_description": param_info.get("ai_description", ""),
                        "package_name": param_info.get("package_name", package_name),
                        "project_name": project_name,
                        "updated_at": current_timestamp,
                    }
                )
            if getattr(method, "return_type", None):
                return_records.append(
                    {
                        "method_name": method.name,
                        "class_name": class_node.name,
                        "return_type": method.return_type,
                        "return_description": getattr(method, "return_description", "") or "",
                        "return_ai_description": getattr(method, "return_ai_description", "") or "",
                        "package_name": package_name,
                        "project_name": project_name,
                        "updated_at": current_timestamp,
                    }
                )
            for statement in getattr(method, "statements", []):
                statement_records.append(
                    {
                        "method_name": method.name,
                        "class_name": class_node.name,
                        "statement_index": getattr(statement, "index", 0),
                        "statement_type": getattr(statement, "type", ""),
                        "statement_content": getattr(statement, "content", ""),
                        "updated_at": current_timestamp,
                    }
                )

        if method_records:
            tx.run(
                """
                UNWIND $methods AS m
                MATCH (c:Class {name: m.class_name, package_name: m.package_name})
                MERGE (meth:Method {name: m.method_name, class_name: m.class_name})
                SET meth.return_type = m.return_type,
                    meth.parameters = m.parameters_json,
                    meth.annotations = m.annotations_json,
                    meth.visibility = m.visibility,
                    meth.description = m.description,
                    meth.ai_description = m.ai_description,
                    meth.logical_name = m.logical_name,
                    meth.package_name = m.package_name,
                    meth.project_name = m.project_name,
                    meth.updated_at = m.updated_at
                MERGE (c)-[:HAS_METHOD]->(meth)
                """,
                methods=method_records,
            )
        if method_annotation_records:
            tx.run(
                """
                UNWIND $items AS item
                MATCH (m:Method {name: item.method_name, class_name: item.class_name})
                MERGE (a:Annotation {name: item.annotation_name})
                MERGE (m)-[:ANNOTATED_WITH]->(a)
                """,
                items=method_annotation_records,
            )
        if throws_records:
            tx.run(
                """
                UNWIND $throws AS t
                MATCH (m:Method {name: t.method_name, class_name: t.class_name})
                MERGE (e:Exception {name: t.exception})
                MERGE (m)-[:THROWS]->(e)
                """,
                throws=throws_records,
            )
        if parameter_records:
            tx.run(
                """
                UNWIND $params AS p
                MATCH (m:Method {name: p.method_name, class_name: p.class_name})
                MERGE (par:Parameter {name: p.param_name, method_name: p.method_name, class_name: p.class_name})
                SET par.type = p.param_type,
                    par.description = p.param_description,
                    par.ai_description = p.param_ai_description,
                    par.package_name = p.package_name,
                    par.project_name = p.project_name,
                    par.updated_at = p.updated_at
                MERGE (m)-[:HAS_PARAMETER]->(par)
                """,
                params=parameter_records,
            )
        if return_records:
            tx.run(
                """
                UNWIND $returns AS r
                MATCH (m:Method {name: r.method_name, class_name: r.class_name})
                MERGE (ret:ReturnType {name: r.return_type, method_name: r.method_name, class_name: r.class_name})
                SET ret.description = r.return_description,
                    ret.ai_description = r.return_ai_description,
                    ret.package_name = r.package_name,
                    ret.project_name = r.project_name,
                    ret.updated_at = r.updated_at
                MERGE (m)-[:RETURNS]->(ret)
                """,
                returns=return_records,
            )
        if statement_records:
            tx.run(
                """
                UNWIND $statements AS s
                MATCH (m:Method {name: s.method_name, class_name: s.class_name})
                MERGE (st:Statement {index: s.statement_index, method_name: s.method_name, class_name: s.class_name})
                SET st.type = s.statement_type,
                    st.content = s.statement_content,
                    st.updated_at = s.updated_at
                MERGE (m)-[:HAS_STATEMENT]->(st)
                """,
                statements=statement_records,
            )

        field_records: list[dict[str, Any]] = []
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
            field_records.append(
                {
                    "class_name": class_node.name,
                    "prop_name": prop.name,
                    "prop_type": prop.type,
                    "prop_logical_name": prop.logical_name or "",
                    "prop_modifiers_json": prop_modifiers_json,
                    "prop_annotations_json": prop_annotations_json,
                    "prop_initial_value": prop.initial_value or "",
                    "package_name": prop.package_name,
                    "project_name": project_name,
                    "prop_description": prop.description or "",
                    "prop_ai_description": prop.ai_description or "",
                    "updated_at": current_timestamp,
                }
            )
        if field_records:
            tx.run(
                """
                UNWIND $fields AS f
                MATCH (c:Class {name: f.class_name})
                MERGE (p:Field {name: f.prop_name, class_name: f.class_name, project_name: f.project_name})
                SET p.type = f.prop_type,
                    p.logical_name = f.prop_logical_name,
                    p.modifiers_json = f.prop_modifiers_json,
                    p.annotations_json = f.prop_annotations_json,
                    p.initial_value = f.prop_initial_value,
                    p.package_name = f.package_name,
                    p.project_name = f.project_name,
                    p.description = f.prop_description,
                    p.ai_description = f.prop_ai_description,
                    p.updated_at = f.updated_at
                MERGE (c)-[:HAS_FIELD]->(p)
                """,
                fields=field_records,
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

            target_package = method_call.target_package or ""

            if is_external_library(method_call.target_class, target_package):
                # 외부 라이브러리
                target_class_query = (
                    "MERGE (tc:Class {name: $target_class, package_name: ''}) "
                    "SET tc.is_external = true"
                )
                tx.run(
                    target_class_query,
                    target_class=method_call.target_class,
                )
                target_method_query = (
                    "MATCH (tc:Class {name: $target_class, package_name: ''}) "
                    "MERGE (tm:Method {name: $target_method, class_name: $target_class}) "
                    "MERGE (tc)-[:HAS_METHOD]->(tm)"
                )
                tx.run(
                    target_method_query,
                    target_class=method_call.target_class,
                    target_method=method_call.target_method,
                )
            else:
                # 프로젝트 내부 - Inner class 특별 처리
                if is_inner_class(method_call.target_class):
                    # Inner class: 외부 클래스와 동일한 패키지 사용
                    outer_class = extract_outer_class_name(method_call.target_class)

                    # Neo4j에서 외부 클래스의 정확한 패키지 조회
                    outer_class_result = tx.run(
                        "MATCH (oc:Class {name: $outer_class, project_name: $project_name}) "
                        "RETURN oc.package_name as package_name "
                        "LIMIT 1",
                        outer_class=outer_class,
                        project_name=project_name
                    )

                    record = outer_class_result.single()
                    if record and record['package_name']:
                        actual_target_package = record['package_name']
                    else:
                        # 외부 클래스를 찾지 못한 경우 target_package 사용
                        actual_target_package = target_package or package_name

                    target_class_query = (
                        "MERGE (tc:Class {name: $target_class, package_name: $target_package}) "
                        "SET tc.is_external = false, tc.is_inner_class = true"
                    )
                    tx.run(
                        target_class_query,
                        target_class=method_call.target_class,
                        target_package=actual_target_package,
                    )
                    target_method_query = (
                        "MATCH (tc:Class {name: $target_class, package_name: $target_package}) "
                        "MERGE (tm:Method {name: $target_method, class_name: $target_class}) "
                        "MERGE (tc)-[:HAS_METHOD]->(tm)"
                    )
                    tx.run(
                        target_method_query,
                        target_class=method_call.target_class,
                        target_package=actual_target_package,
                        target_method=method_call.target_method,
                    )
                else:
                    # 일반 클래스
                    target_class_query = (
                        "MERGE (tc:Class {name: $target_class, package_name: $target_package}) "
                        "SET tc.is_external = false"
                    )
                    tx.run(
                        target_class_query,
                        target_class=method_call.target_class,
                        target_package=target_package,
                    )
                    target_method_query = (
                        "MATCH (tc:Class {name: $target_class, package_name: $target_package}) "
                        "MERGE (tm:Method {name: $target_method, class_name: $target_class}) "
                        "MERGE (tc)-[:HAS_METHOD]->(tm)"
                    )
                    tx.run(
                        target_method_query,
                        target_class=method_call.target_class,
                        target_package=target_package,
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

    @staticmethod
    def _create_classes_batch_tx(tx, classes_data: list[tuple[Class, str, str]]) -> None:
        """
        여러 클래스를 배치로 생성하는 트랜잭션

        Args:
            tx: Neo4j 트랜잭션
            classes_data: [(class_node, package_name, project_name), ...] 튜플 리스트
        """
        logger = get_logger(__name__)
        current_timestamp = GraphDBBase._get_current_timestamp()

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

        # 1. 클래스 노드 배치 생성
        class_records = []
        for class_node, package_name, project_name in classes_data:
            class_records.append({
                'name': class_node.name,
                'file_path': class_node.file_path,
                'type': class_node.type,
                'sub_type': class_node.sub_type or "",
                'source': class_node.source,
                'logical_name': class_node.logical_name,
                'superclass': class_node.superclass,
                'interfaces': class_node.interfaces,
                'imports': class_node.imports,
                'package_name': package_name,
                'project_name': project_name,
                'description': class_node.description or "",
                'ai_description': class_node.ai_description or "",
                'updated_at': current_timestamp,
            })

        if class_records:
            tx.run(
                """
                UNWIND $classes AS c
                MERGE (cls:Class {name: c.name, package_name: c.package_name})
                SET cls.file_path = c.file_path,
                    cls.type = c.type,
                    cls.sub_type = c.sub_type,
                    cls.source = c.source,
                    cls.logical_name = c.logical_name,
                    cls.superclass = c.superclass,
                    cls.interfaces = c.interfaces,
                    cls.imports = c.imports,
                    cls.package_name = c.package_name,
                    cls.project_name = c.project_name,
                    cls.description = c.description,
                    cls.ai_description = c.ai_description,
                    cls.updated_at = c.updated_at
                """,
                classes=class_records
            )

        # 2. Package-Class 관계 배치 생성
        package_class_records = []
        for class_node, package_name, project_name in classes_data:
            if package_name:
                package_class_records.append({
                    'package_name': package_name,
                    'class_name': class_node.name,
                })

        if package_class_records:
            tx.run(
                """
                UNWIND $relations AS r
                MATCH (p:Package {name: r.package_name})
                MATCH (c:Class {name: r.class_name, package_name: r.package_name})
                MERGE (p)-[:CONTAINS]->(c)
                """,
                relations=package_class_records
            )

        # 3. Project-Class 관계 배치 생성
        project_class_records = []
        for class_node, package_name, project_name in classes_data:
            project_class_records.append({
                'project_name': project_name,
                'class_name': class_node.name,
                'package_name': package_name,
            })

        if project_class_records:
            tx.run(
                """
                UNWIND $relations AS r
                MATCH (proj:Project {name: r.project_name})
                MATCH (c:Class {name: r.class_name, package_name: r.package_name})
                MERGE (proj)-[:CONTAINS]->(c)
                """,
                relations=project_class_records
            )

        # 4. Import 관계 배치 생성
        import_records_external = []
        import_records_internal = []
        for class_node, package_name, project_name in classes_data:
            for import_class in class_node.imports:
                if is_external_library(import_class):
                    import_records_external.append({
                        'import_class': import_class,
                        'class_name': class_node.name,
                        'package_name': package_name,
                    })
                else:
                    simple_name, import_package = extract_package_from_full_name(import_class)
                    import_records_internal.append({
                        'import_name': simple_name,
                        'import_package': import_package or "",
                        'class_name': class_node.name,
                        'package_name': package_name,
                    })

        if import_records_external:
            tx.run(
                """
                UNWIND $imports AS imp
                MERGE (imported:Class {name: imp.import_class, package_name: ''})
                SET imported.is_external = true
                WITH imp, imported
                MATCH (c:Class {name: imp.class_name, package_name: imp.package_name})
                MERGE (c)-[:IMPORTS]->(imported)
                """,
                imports=import_records_external
            )

        if import_records_internal:
            tx.run(
                """
                UNWIND $imports AS imp
                MERGE (imported:Class {name: imp.import_name, package_name: imp.import_package})
                SET imported.is_external = false
                WITH imp, imported
                MATCH (c:Class {name: imp.class_name, package_name: imp.package_name})
                MERGE (c)-[:IMPORTS]->(imported)
                """,
                imports=import_records_internal
            )

        # 5. Annotation 관계 배치 생성
        annotation_records = []
        for class_node, package_name, project_name in classes_data:
            for annotation in class_node.annotations:
                annotation_name = getattr(annotation, "name", str(annotation))
                annotation_records.append({
                    'class_name': class_node.name,
                    'annotation_name': annotation_name,
                })

        if annotation_records:
            tx.run(
                """
                UNWIND $annotations AS ann
                MATCH (c:Class {name: ann.class_name})
                MERGE (a:Annotation {name: ann.annotation_name})
                MERGE (c)-[:ANNOTATED_WITH]->(a)
                """,
                annotations=annotation_records
            )

        # 6. Superclass 관계 배치 생성
        superclass_records_external = []
        superclass_records_internal = []
        for class_node, package_name, project_name in classes_data:
            if class_node.superclass:
                if is_external_library(class_node.superclass):
                    superclass_records_external.append({
                        'superclass': class_node.superclass,
                        'class_name': class_node.name,
                        'package_name': package_name,
                    })
                else:
                    simple_name, super_package = extract_package_from_full_name(class_node.superclass)
                    superclass_records_internal.append({
                        'superclass': simple_name,
                        'super_package': super_package or "",
                        'class_name': class_node.name,
                        'package_name': package_name,
                    })

        if superclass_records_external:
            tx.run(
                """
                UNWIND $supers AS sup
                MERGE (super:Class {name: sup.superclass, package_name: ''})
                SET super.is_external = true
                WITH sup, super
                MATCH (c:Class {name: sup.class_name, package_name: sup.package_name})
                MERGE (c)-[:EXTENDS]->(super)
                """,
                supers=superclass_records_external
            )

        if superclass_records_internal:
            tx.run(
                """
                UNWIND $supers AS sup
                MERGE (super:Class {name: sup.superclass, package_name: sup.super_package})
                SET super.is_external = false
                WITH sup, super
                MATCH (c:Class {name: sup.class_name, package_name: sup.package_name})
                MERGE (c)-[:EXTENDS]->(super)
                """,
                supers=superclass_records_internal
            )

        # 7. Interface 관계 배치 생성
        interface_records = []
        for class_node, package_name, project_name in classes_data:
            for interface in class_node.interfaces:
                interface_records.append({
                    'interface': interface,
                    'class_name': class_node.name,
                })

        if interface_records:
            tx.run(
                """
                UNWIND $interfaces AS iface
                MERGE (i:Interface {name: iface.interface})
                WITH iface, i
                MATCH (c:Class {name: iface.class_name})
                MERGE (c)-[:IMPLEMENTS]->(i)
                """,
                interfaces=interface_records
            )

        # 8. Method 및 관련 엔티티 배치 생성
        all_method_records = []
        all_method_annotation_records = []
        all_parameter_records = []
        all_return_records = []

        for class_node, package_name, project_name in classes_data:
            existing_method_names = {method.name for method in getattr(class_node, "methods", [])}

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

                try:
                    parameters_json = json.dumps(serialized_parameters)
                    annotations_json = json.dumps(serialized_annotations)
                except (TypeError, ValueError) as exc:
                    logger.error(
                        "Method serialization error: %s.%s -> %s",
                        class_node.name,
                        method.name,
                        exc,
                    )
                    raise

                all_method_records.append({
                    "class_name": class_node.name,
                    "method_name": method.name,
                    "package_name": package_name,
                    "project_name": project_name,
                    "return_type": getattr(method, "return_type", "") or "",
                    "parameters_json": parameters_json,
                    "annotations_json": annotations_json,
                    "visibility": visibility,
                    "description": getattr(method, "description", "") or "",
                    "ai_description": getattr(method, "ai_description", "") or "",
                    "logical_name": getattr(method, "logical_name", "") or "",
                    "updated_at": current_timestamp,
                })

                for annotation in method_annotations:
                    annotation_name = getattr(annotation, "name", str(annotation))
                    all_method_annotation_records.append({
                        "method_name": method.name,
                        "class_name": class_node.name,
                        "annotation_name": annotation_name,
                    })

                for param_info in serialized_parameters:
                    all_parameter_records.append({
                        "method_name": method.name,
                        "class_name": class_node.name,
                        "param_name": param_info["name"],
                        "param_type": param_info.get("type", ""),
                        "param_description": param_info.get("description", ""),
                        "param_ai_description": param_info.get("ai_description", ""),
                        "package_name": param_info.get("package_name", package_name),
                        "project_name": project_name,
                        "updated_at": current_timestamp,
                    })

                if getattr(method, "return_type", None):
                    all_return_records.append({
                        "method_name": method.name,
                        "class_name": class_node.name,
                        "return_type": method.return_type,
                        "return_description": getattr(method, "return_description", "") or "",
                        "return_ai_description": getattr(method, "return_ai_description", "") or "",
                        "package_name": package_name,
                        "project_name": project_name,
                        "updated_at": current_timestamp,
                    })

        if all_method_records:
            tx.run(
                """
                UNWIND $methods AS m
                MATCH (c:Class {name: m.class_name, package_name: m.package_name})
                MERGE (meth:Method {name: m.method_name, class_name: m.class_name})
                SET meth.return_type = m.return_type,
                    meth.parameters = m.parameters_json,
                    meth.annotations = m.annotations_json,
                    meth.visibility = m.visibility,
                    meth.description = m.description,
                    meth.ai_description = m.ai_description,
                    meth.logical_name = m.logical_name,
                    meth.package_name = m.package_name,
                    meth.project_name = m.project_name,
                    meth.updated_at = m.updated_at
                MERGE (c)-[:HAS_METHOD]->(meth)
                """,
                methods=all_method_records,
            )

        if all_method_annotation_records:
            tx.run(
                """
                UNWIND $items AS item
                MATCH (m:Method {name: item.method_name, class_name: item.class_name})
                MERGE (a:Annotation {name: item.annotation_name})
                MERGE (m)-[:ANNOTATED_WITH]->(a)
                """,
                items=all_method_annotation_records,
            )

        if all_parameter_records:
            tx.run(
                """
                UNWIND $params AS p
                MATCH (m:Method {name: p.method_name, class_name: p.class_name})
                MERGE (par:Parameter {name: p.param_name, method_name: p.method_name, class_name: p.class_name})
                SET par.type = p.param_type,
                    par.description = p.param_description,
                    par.ai_description = p.param_ai_description,
                    par.package_name = p.package_name,
                    par.project_name = p.project_name,
                    par.updated_at = p.updated_at
                MERGE (m)-[:HAS_PARAMETER]->(par)
                """,
                params=all_parameter_records,
            )

        if all_return_records:
            tx.run(
                """
                UNWIND $returns AS r
                MATCH (m:Method {name: r.method_name, class_name: r.class_name})
                MERGE (ret:ReturnType {name: r.return_type, method_name: r.method_name, class_name: r.class_name})
                SET ret.description = r.return_description,
                    ret.ai_description = r.return_ai_description,
                    ret.package_name = r.package_name,
                    ret.project_name = r.project_name,
                    ret.updated_at = r.updated_at
                MERGE (m)-[:RETURNS]->(ret)
                """,
                returns=all_return_records,
            )

        # 9. Field 배치 생성
        all_field_records = []
        for class_node, package_name, project_name in classes_data:
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
                all_field_records.append({
                    "class_name": class_node.name,
                    "prop_name": prop.name,
                    "prop_type": prop.type,
                    "prop_logical_name": prop.logical_name or "",
                    "prop_modifiers_json": prop_modifiers_json,
                    "prop_annotations_json": prop_annotations_json,
                    "prop_initial_value": prop.initial_value or "",
                    "package_name": prop.package_name,
                    "project_name": project_name,
                    "prop_description": prop.description or "",
                    "prop_ai_description": prop.ai_description or "",
                    "updated_at": current_timestamp,
                })

        if all_field_records:
            tx.run(
                """
                UNWIND $fields AS f
                MATCH (c:Class {name: f.class_name})
                MERGE (p:Field {name: f.prop_name, class_name: f.class_name, project_name: f.project_name})
                SET p.type = f.prop_type,
                    p.logical_name = f.prop_logical_name,
                    p.modifiers_json = f.prop_modifiers_json,
                    p.annotations_json = f.prop_annotations_json,
                    p.initial_value = f.prop_initial_value,
                    p.package_name = f.package_name,
                    p.project_name = f.project_name,
                    p.description = f.prop_description,
                    p.ai_description = f.prop_ai_description,
                    p.updated_at = f.updated_at
                MERGE (c)-[:HAS_FIELD]->(p)
                """,
                fields=all_field_records,
            )

        # 10. Method Call 관계 배치 생성
        call_records_external = []
        call_records_internal = []
        call_records_inner_class = []

        for class_node, package_name, project_name in classes_data:
            existing_method_names = {method.name for method in getattr(class_node, "methods", [])}

            for method_call in class_node.calls:
                if not getattr(method_call, "target_class", "") or not getattr(method_call, "target_method", ""):
                    continue

                if (
                    method_call.target_class == class_node.name
                    and method_call.target_method not in existing_method_names
                ):
                    continue

                target_package = method_call.target_package or ""

                if is_external_library(method_call.target_class, target_package):
                    call_records_external.append({
                        'target_class': method_call.target_class,
                        'target_method': method_call.target_method,
                        'source_method': method_call.source_method,
                        'source_class': class_node.name,
                        'source_package': package_name,
                        'target_package': method_call.target_package,
                        'call_order': method_call.call_order,
                        'line_number': method_call.line_number,
                    })
                elif is_inner_class(method_call.target_class):
                    outer_class = extract_outer_class_name(method_call.target_class)
                    call_records_inner_class.append({
                        'target_class': method_call.target_class,
                        'target_method': method_call.target_method,
                        'source_method': method_call.source_method,
                        'source_class': class_node.name,
                        'source_package': package_name,
                        'target_package': target_package or package_name,
                        'call_order': method_call.call_order,
                        'line_number': method_call.line_number,
                        'outer_class': outer_class,
                        'project_name': project_name,
                    })
                else:
                    call_records_internal.append({
                        'target_class': method_call.target_class,
                        'target_method': method_call.target_method,
                        'source_method': method_call.source_method,
                        'source_class': class_node.name,
                        'source_package': package_name,
                        'target_package': target_package,
                        'call_order': method_call.call_order,
                        'line_number': method_call.line_number,
                    })

        # 외부 라이브러리 호출
        if call_records_external:
            tx.run(
                """
                UNWIND $calls AS call
                MERGE (tc:Class {name: call.target_class, package_name: ''})
                SET tc.is_external = true
                WITH call, tc
                MERGE (tm:Method {name: call.target_method, class_name: call.target_class})
                MERGE (tc)-[:HAS_METHOD]->(tm)
                WITH call, tm
                MATCH (sm:Method {name: call.source_method, class_name: call.source_class})
                MERGE (sm)-[r:CALLS]->(tm)
                SET r.source_package = call.source_package,
                    r.source_class = call.source_class,
                    r.source_method = call.source_method,
                    r.target_package = call.target_package,
                    r.target_class = call.target_class,
                    r.target_method = call.target_method,
                    r.call_order = call.call_order,
                    r.line_number = call.line_number
                """,
                calls=call_records_external
            )

        # Inner class 호출
        if call_records_inner_class:
            # Inner class는 외부 클래스의 패키지를 조회해야 함
            for call in call_records_inner_class:
                outer_class_result = tx.run(
                    "MATCH (oc:Class {name: $outer_class, project_name: $project_name}) "
                    "RETURN oc.package_name as package_name "
                    "LIMIT 1",
                    outer_class=call['outer_class'],
                    project_name=call['project_name']
                )
                record = outer_class_result.single()
                if record and record['package_name']:
                    call['actual_target_package'] = record['package_name']
                else:
                    call['actual_target_package'] = call['target_package']

            tx.run(
                """
                UNWIND $calls AS call
                MERGE (tc:Class {name: call.target_class, package_name: call.actual_target_package})
                SET tc.is_external = false, tc.is_inner_class = true
                WITH call, tc
                MERGE (tm:Method {name: call.target_method, class_name: call.target_class})
                MERGE (tc)-[:HAS_METHOD]->(tm)
                WITH call, tm
                MATCH (sm:Method {name: call.source_method, class_name: call.source_class})
                MERGE (sm)-[r:CALLS]->(tm)
                SET r.source_package = call.source_package,
                    r.source_class = call.source_class,
                    r.source_method = call.source_method,
                    r.target_package = call.actual_target_package,
                    r.target_class = call.target_class,
                    r.target_method = call.target_method,
                    r.call_order = call.call_order,
                    r.line_number = call.line_number
                """,
                calls=call_records_inner_class
            )

        # 내부 프로젝트 호출
        if call_records_internal:
            tx.run(
                """
                UNWIND $calls AS call
                MERGE (tc:Class {name: call.target_class, package_name: call.target_package})
                SET tc.is_external = false
                WITH call, tc
                MERGE (tm:Method {name: call.target_method, class_name: call.target_class})
                MERGE (tc)-[:HAS_METHOD]->(tm)
                WITH call, tm
                MATCH (sm:Method {name: call.source_method, class_name: call.source_class})
                MERGE (sm)-[r:CALLS]->(tm)
                SET r.source_package = call.source_package,
                    r.source_class = call.source_class,
                    r.source_method = call.source_method,
                    r.target_package = call.target_package,
                    r.target_class = call.target_class,
                    r.target_method = call.target_method,
                    r.call_order = call.call_order,
                    r.line_number = call.line_number
                """,
                calls=call_records_internal
            )
