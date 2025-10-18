from __future__ import annotations

import json
from typing import List

from csa.models.graph_entities import Bean, BeanDependency, ConfigFile, Endpoint, TestClass
from csa.services.graph_db.base import GraphDBBase


class ApplicationMixin:
    """Handle Spring bean, endpoint, config, and test nodes."""

    def add_bean(self, bean: Bean, project_name: str) -> None:
        """Add or update a Spring bean node."""
        self._execute_write(self._create_bean_node_tx, bean, project_name)

    def add_beans_batch(self, beans: List[Bean], project_name: str) -> None:
        """Add or update multiple Spring bean nodes in a single transaction."""
        if not beans:
            return
        self._execute_write(self._create_beans_batch_tx, beans, project_name)

    def add_bean_dependency(self, dependency: BeanDependency, project_name: str) -> None:
        """Register dependency information between beans."""
        self._execute_write(self._create_bean_dependency_tx, dependency, project_name)

    def add_endpoint(self, endpoint: Endpoint, project_name: str) -> None:
        """Add REST endpoint metadata."""
        self._execute_write(self._create_endpoint_node_tx, endpoint, project_name)

    def add_config_file(self, config_file: ConfigFile, project_name: str) -> None:
        """Add configuration file metadata."""
        self._execute_write(self._create_config_file_node_tx, config_file, project_name)

    def add_test_class(self, test_class: TestClass, project_name: str) -> None:
        """Add test class metadata."""
        self._execute_write(self._create_test_class_node_tx, test_class, project_name)

    def add_endpoints_batch(self, endpoints: List[Endpoint], project_name: str) -> None:
        """Add or update multiple endpoint nodes in a single transaction."""
        if not endpoints:
            return
        self._execute_write(self._create_endpoints_batch_tx, endpoints, project_name)

    def add_test_classes_batch(self, test_classes: List[TestClass], project_name: str) -> None:
        """Add or update multiple test class nodes in a single transaction."""
        if not test_classes:
            return
        self._execute_write(self._create_test_classes_batch_tx, test_classes, project_name)

    @staticmethod
    def _create_bean_node_tx(tx, bean: Bean, project_name: str) -> None:
        current_timestamp = GraphDBBase._get_current_timestamp()
        bean_query = (
            "MERGE (b:Bean {name: $name}) "
            "SET b.type = $type, b.scope = $scope, b.class_name = $class_name, "
            "b.package_name = $package_name, b.annotation_names = $annotation_names, "
            "b.method_count = $method_count, b.property_count = $property_count, "
            "b.project_name = $project_name, b.description = $description, b.ai_description = $ai_description, "
            "b.updated_at = $updated_at"
        )
        tx.run(
            bean_query,
            name=bean.name,
            type=bean.type,
            scope=bean.scope,
            class_name=bean.class_name,
            package_name=bean.package_name,
            annotation_names=json.dumps(bean.annotation_names),
            method_count=bean.method_count,
            property_count=bean.property_count,
            project_name=project_name,
            description=bean.description or "",
            ai_description=bean.ai_description or "",
            updated_at=current_timestamp,
        )

    @staticmethod
    def _create_beans_batch_tx(tx, beans: List[Bean], project_name: str) -> None:
        """배치로 여러 Bean을 한 번의 트랜잭션에 저장"""
        current_timestamp = GraphDBBase._get_current_timestamp()
        bean_query = (
            "UNWIND $beans AS bean "
            "MERGE (b:Bean {name: bean.name}) "
            "SET b.type = bean.type, b.scope = bean.scope, b.class_name = bean.class_name, "
            "b.package_name = bean.package_name, b.annotation_names = bean.annotation_names, "
            "b.method_count = bean.method_count, b.property_count = bean.property_count, "
            "b.project_name = bean.project_name, b.description = bean.description, "
            "b.ai_description = bean.ai_description, b.updated_at = bean.updated_at"
        )
        beans_data = [
            {
                'name': bean.name,
                'type': bean.type,
                'scope': bean.scope,
                'class_name': bean.class_name,
                'package_name': bean.package_name,
                'annotation_names': json.dumps(bean.annotation_names),
                'method_count': bean.method_count,
                'property_count': bean.property_count,
                'project_name': project_name,
                'description': bean.description or "",
                'ai_description': bean.ai_description or "",
                'updated_at': current_timestamp,
            }
            for bean in beans
        ]
        tx.run(bean_query, beans=beans_data)

    @staticmethod
    def _create_bean_dependency_tx(tx, dependency: BeanDependency, project_name: str) -> None:
        source_bean_query = "MERGE (sb:Bean {name: $source_bean})"
        target_bean_query = "MERGE (tb:Bean {name: $target_bean})"
        tx.run(source_bean_query, source_bean=dependency.source_bean)
        tx.run(target_bean_query, target_bean=dependency.target_bean)
        dependency_query = (
            "MATCH (sb:Bean {name: $source_bean}), (tb:Bean {name: $target_bean}) "
            "MERGE (sb)-[r:DEPENDS_ON {injection_type: $injection_type, "
            "field_name: $field_name, method_name: $method_name, "
            "parameter_name: $parameter_name}]->(tb)"
        )
        tx.run(
            dependency_query,
            source_bean=dependency.source_bean,
            target_bean=dependency.target_bean,
            injection_type=dependency.injection_type,
            field_name=dependency.field_name,
            method_name=dependency.method_name,
            parameter_name=dependency.parameter_name,
        )

    @staticmethod
    def _create_endpoint_node_tx(tx, endpoint: Endpoint, project_name: str) -> None:
        current_timestamp = GraphDBBase._get_current_timestamp()
        endpoint_query = (
            "MERGE (e:Endpoint {path: $path, method: $method}) "
            "SET e.controller_class = $controller_class, e.handler_method = $handler_method, "
            "e.endpoint_parameters = $endpoint_parameters, e.return_type = $return_type, "
            "e.annotations = $annotations, e.full_path = $full_path, "
            "e.project_name = $project_name, e.description = $description, e.ai_description = $ai_description, "
            "e.updated_at = $updated_at"
        )
        tx.run(
            endpoint_query,
            path=endpoint.path,
            method=endpoint.method,
            controller_class=endpoint.controller_class,
            handler_method=endpoint.handler_method,
            endpoint_parameters=json.dumps(endpoint.parameters),
            return_type=endpoint.return_type,
            annotations=json.dumps(endpoint.annotations),
            full_path=endpoint.full_path,
            project_name=project_name,
            description=endpoint.description or "",
            ai_description=endpoint.ai_description or "",
            updated_at=current_timestamp,
        )

    @staticmethod
    def _create_config_file_node_tx(tx, config_file: ConfigFile, project_name: str) -> None:
        current_timestamp = GraphDBBase._get_current_timestamp()
        config_query = (
            "MERGE (c:ConfigFile {name: $name}) "
            "SET c.file_path = $file_path, c.file_type = $file_type, "
            "c.properties = $properties, c.sections = $sections, "
            "c.profiles = $profiles, c.environment = $environment, "
            "c.description = $description, c.ai_description = $ai_description, "
            "c.updated_at = $updated_at"
        )
        tx.run(
            config_query,
            name=config_file.name,
            file_path=config_file.file_path,
            file_type=config_file.file_type,
            properties=json.dumps(config_file.properties),
            sections=json.dumps(config_file.sections),
            profiles=json.dumps(config_file.profiles),
            environment=config_file.environment,
            description=config_file.description or "",
            ai_description=config_file.ai_description or "",
            updated_at=current_timestamp,
        )

    @staticmethod
    def _create_test_class_node_tx(tx, test_class: TestClass, project_name: str) -> None:
        current_timestamp = GraphDBBase._get_current_timestamp()
        test_query = (
            "MERGE (t:TestClass {name: $name}) "
            "SET t.package_name = $package_name, t.test_framework = $test_framework, "
            "t.test_type = $test_type, t.annotations = $annotations, "
            "t.test_methods = $test_methods, t.setup_methods = $setup_methods, "
            "t.mock_dependencies = $mock_dependencies, t.test_configurations = $test_configurations, "
            "t.file_path = $file_path, t.project_name = $project_name, "
            "t.description = $description, t.ai_description = $ai_description, "
            "t.updated_at = $updated_at"
        )
        tx.run(
            test_query,
            name=test_class.name,
            package_name=test_class.package_name,
            test_framework=test_class.test_framework,
            test_type=test_class.test_type,
            annotations=json.dumps(test_class.annotations),
            test_methods=json.dumps(test_class.test_methods),
            setup_methods=json.dumps(test_class.setup_methods),
            mock_dependencies=json.dumps(test_class.mock_dependencies),
            test_configurations=json.dumps(test_class.test_configurations),
            file_path=test_class.file_path,
            project_name=project_name,
            description=test_class.description or "",
            ai_description=test_class.ai_description or "",
            updated_at=current_timestamp,
        )

    @staticmethod
    def _create_endpoints_batch_tx(tx, endpoints: List[Endpoint], project_name: str) -> None:
        """배치로 여러 Endpoint를 한 번의 트랜잭션에 저장"""
        current_timestamp = GraphDBBase._get_current_timestamp()
        endpoint_query = (
            "UNWIND $endpoints AS ep "
            "MERGE (e:Endpoint {path: ep.path, method: ep.method}) "
            "SET e.controller_class = ep.controller_class, "
            "e.handler_method = ep.handler_method, "
            "e.endpoint_parameters = ep.endpoint_parameters, "
            "e.return_type = ep.return_type, "
            "e.annotations = ep.annotations, "
            "e.full_path = ep.full_path, "
            "e.project_name = ep.project_name, "
            "e.description = ep.description, "
            "e.ai_description = ep.ai_description, "
            "e.updated_at = ep.updated_at"
        )
        endpoints_data = [
            {
                'path': ep.path,
                'method': ep.method,
                'controller_class': ep.controller_class,
                'handler_method': ep.handler_method,
                'endpoint_parameters': json.dumps(ep.parameters),
                'return_type': ep.return_type,
                'annotations': json.dumps(ep.annotations),
                'full_path': ep.full_path,
                'project_name': project_name,
                'description': ep.description or "",
                'ai_description': ep.ai_description or "",
                'updated_at': current_timestamp,
            }
            for ep in endpoints
        ]
        tx.run(endpoint_query, endpoints=endpoints_data)

    @staticmethod
    def _create_test_classes_batch_tx(tx, test_classes: List[TestClass], project_name: str) -> None:
        """배치로 여러 TestClass를 한 번의 트랜잭션에 저장"""
        current_timestamp = GraphDBBase._get_current_timestamp()
        test_query = (
            "UNWIND $tests AS t "
            "MERGE (tc:TestClass {name: t.name}) "
            "SET tc.package_name = t.package_name, "
            "tc.test_framework = t.test_framework, "
            "tc.test_type = t.test_type, "
            "tc.annotations = t.annotations, "
            "tc.test_methods = t.test_methods, "
            "tc.setup_methods = t.setup_methods, "
            "tc.mock_dependencies = t.mock_dependencies, "
            "tc.test_configurations = t.test_configurations, "
            "tc.file_path = t.file_path, "
            "tc.project_name = t.project_name, "
            "tc.description = t.description, "
            "tc.ai_description = t.ai_description, "
            "tc.updated_at = t.updated_at"
        )
        tests_data = [
            {
                'name': tc.name,
                'package_name': tc.package_name,
                'test_framework': tc.test_framework,
                'test_type': tc.test_type,
                'annotations': json.dumps(tc.annotations),
                'test_methods': json.dumps(tc.test_methods),
                'setup_methods': json.dumps(tc.setup_methods),
                'mock_dependencies': json.dumps(tc.mock_dependencies),
                'test_configurations': json.dumps(tc.test_configurations),
                'file_path': tc.file_path,
                'project_name': project_name,
                'description': tc.description or "",
                'ai_description': tc.ai_description or "",
                'updated_at': current_timestamp,
            }
            for tc in test_classes
        ]
        tx.run(test_query, tests=tests_data)
