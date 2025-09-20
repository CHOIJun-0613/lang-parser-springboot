import json

from neo4j import Driver, GraphDatabase

from src.models.graph_entities import Class, Package, Bean, BeanDependency, Endpoint, MyBatisMapper, SqlStatement, JpaEntity, ConfigFile, TestClass
from src.utils.logger import get_logger


class GraphDB:
    """A service for interacting with the Neo4j database."""

    def __init__(self, uri, user, password):
        """Initializes the database driver."""
        self._driver: Driver = GraphDatabase.driver(uri, auth=(user, password))
        self.logger = get_logger(__name__)

    def close(self):
        """Closes the database connection."""
        self._driver.close()

    def add_package(self, package_node: Package, project_name: str):
        """Adds a package to the database."""
        with self._driver.session() as session:
            session.execute_write(self._create_package_node_tx, package_node, project_name)

    def add_class(self, class_node: Class, package_name: str, project_name: str):
        """Adds a class and its relationships to the database
        in a single transaction."""
        with self._driver.session() as session:
            session.execute_write(self._create_class_node_tx, class_node, package_name, project_name)

    @staticmethod
    def _create_package_node_tx(tx, package_node: Package, project_name: str):
        """A transaction function to create a package node."""
        package_query = (
            "MERGE (p:Package {name: $name}) "
            "SET p.project_name = $project_name"
        )
        tx.run(
            package_query,
            name=package_node.name,
            project_name=project_name,
        )

    @staticmethod
    def _create_class_node_tx(tx, class_node: Class, package_name: str, project_name: str):
        """A transaction function to create a class, its properties,
        and its method calls."""
        # Create or merge the class node itself
        class_query = (
            "MERGE (c:Class {name: $name}) "
            "SET c.file_path = $file_path, c.type = $type, "
            "c.source = $source, c.logical_name = $logical_name, "
            "c.superclass = $superclass, c.interfaces = $interfaces, "
            "c.imports = $imports, c.package_name = $package_name, "
            "c.project_name = $project_name"  # Add project_name
        )
        tx.run(
            class_query,
            name=class_node.name,
            file_path=class_node.file_path,
            type=class_node.type,
            source=class_node.source,
            logical_name=class_node.logical_name,
            superclass=class_node.superclass,
            interfaces=class_node.interfaces,
            imports=class_node.imports,
            package_name=package_name,  # Add package_name
            project_name=project_name,  # Add project_name
        ) # Pass all class properties

        # Create relationship between package and class
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

        # --- Start of new inheritance relationships logic ---
        # Create EXTENDS relationship
        if class_node.superclass:
            # Split superclass into name and package
            # Assuming superclass is fully qualified or in the same package
            if '.' in class_node.superclass:
                superclass_package = ".".join(class_node.superclass.split('.')[:-1])
                superclass_name = class_node.superclass.split('.')[-1]
            else:
                superclass_package = package_name # Assume same package
                superclass_name = class_node.superclass

            extends_query = (
                "MATCH (c:Class {name: $class_name}) "
                "MERGE (s:Class {name: $superclass_name}) "
                "MERGE (c)-[:EXTENDS]->(s)"
            )
            tx.run(
                extends_query,
                class_name=class_node.name,
                superclass_name=superclass_name,
            )

        # Create IMPLEMENTS relationships
        for interface_fqn in class_node.interfaces:
            # Split interface FQN into name and package
            if '.' in interface_fqn:
                interface_package = ".".join(interface_fqn.split('.')[:-1])
                interface_name = interface_fqn.split('.')[-1]
            else:
                interface_package = package_name # Assume same package
                interface_name = interface_fqn

            implements_query = (
                "MATCH (c:Class {name: $class_name}) "
                "MERGE (i:Class {name: $interface_name}) "
                "MERGE (c)-[:IMPLEMENTS]->(i)"
            )
            tx.run(
                implements_query,
                class_name=class_node.name,
                interface_name=interface_name,
            )
        # --- End of new inheritance relationships logic ---

        # --- Start of new import relationships logic ---
        for imported_class_fqn in class_node.imports:
            # Split imported class FQN into name and package
            if '.' in imported_class_fqn:
                imported_class_package = ".".join(imported_class_fqn.split('.')[:-1])
                imported_class_name = imported_class_fqn.split('.')[-1]
            else:
                # This case should ideally not happen for imports, but for robustness
                imported_class_package = "" # Or some default/error handling
                imported_class_name = imported_class_fqn

            # Exclude java.io classes from being imported as nodes
            if imported_class_package.startswith("java.io"):
                continue

            imports_query = (
                "MATCH (c:Class {name: $class_name}) "
                "MERGE (i:Class {name: $imported_class_name}) "
                "MERGE (c)-[:IMPORTS]->(i)"
            )
            tx.run(
                imports_query,
                class_name=class_node.name,
                imported_class_name=imported_class_name,
            )
        # --- End of new import relationships logic ---

        # --- Start of new method relationships logic ---
        for method in class_node.methods:
            # Serialize parameters to JSON string
            parameters_json = json.dumps([p.dict() for p in method.parameters])
            # Serialize modifiers to JSON string
            modifiers_json = json.dumps(method.modifiers)
            # Serialize annotations to JSON string
            annotations_json = json.dumps([a.dict() for a in method.annotations])

            method_query = (
                "MATCH (c:Class {name: $class_name}) "
                "MERGE (m:Method {name: $method_name, class_name: $class_name}) " # Unique identifier for method
                "SET m.logical_name = $logical_name, "
                "m.return_type = $return_type, "
                "m.parameters_json = $parameters_json, "
                "m.modifiers_json = $modifiers_json, "
                "m.annotations_json = $annotations_json, "
                "m.source = $source, " # Add m.source
                "m.package_name = $package_name, " # Add package_name
                "m.project_name = $project_name " # Add project_name
                "MERGE (c)-[:HAS_METHOD]->(m)"
            )
            # Debug logging
            logger = get_logger(__name__)
            logger.debug(f"Method {method.name} - logical_name: {method.logical_name}, return_type: {method.return_type}, package_name: {method.package_name}")
            
            tx.run(
                method_query,
                class_name=class_node.name,
                method_name=method.name,
                logical_name=method.logical_name or "", # Handle None values
                return_type=method.return_type or "void", # Handle None values
                parameters_json=parameters_json,
                modifiers_json=modifiers_json,
                annotations_json=annotations_json,
                source=method.source or "", # Handle None values
                package_name=method.package_name or "", # Handle None values
                project_name=project_name, # Add project_name
            ) # Pass all method properties
        # --- End of new method relationships logic ---

        # Create properties and relationships
        for prop in class_node.properties:
            # Serialize modifiers to JSON string
            prop_modifiers_json = json.dumps(prop.modifiers)
            # Serialize annotations to JSON string
            prop_annotations_json = json.dumps([a.dict() for a in prop.annotations])
            
            prop_query = (
                "MATCH (c:Class {name: $class_name}) "
                "MERGE (p:Property {name: $prop_name, type: $prop_type}) "
                "SET p.logical_name = $prop_logical_name, " # Add logical_name
                "p.modifiers_json = $prop_modifiers_json, " # Set modifiers as JSON
                "p.annotations_json = $prop_annotations_json, " # Set annotations as JSON
                "p.initial_value = $prop_initial_value, " # Set initial value
                "p.package_name = $package_name, " # Add package_name
                "p.class_name = $class_name, " # Add class_name
                "p.project_name = $project_name " # Add project_name
                "MERGE (c)-[:HAS_PROPERTY]->(p)"
            )
            tx.run(
                prop_query,
                class_name=class_node.name,
                prop_name=prop.name,
                prop_type=prop.type,
                prop_logical_name=prop.logical_name or "", # Add logical_name
                prop_modifiers_json=prop_modifiers_json, # Pass modifiers as JSON
                prop_annotations_json=prop_annotations_json, # Pass annotations as JSON
                prop_initial_value=prop.initial_value or "", # Pass initial value
                package_name=prop.package_name, # Pass package_name
                project_name=project_name, # Add project_name
            )

        # Create method call relationships (method to method)
        for method_call in class_node.calls:
            # First, ensure the target class exists
            target_class_query = (
                "MERGE (tc:Class {name: $target_class})"
            )
            tx.run(
                target_class_query,
                target_class=method_call.target_class,
            )
            
            # Create the target method if it doesn't exist
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
            
            # Create the CALLS relationship between source method and target method
            call_query = (
                "MATCH (sm:Method {name: $source_method, class_name: $source_class}) "
                "MATCH (tm:Method {name: $target_method, class_name: $target_class}) "
                "MERGE (sm)-[r:CALLS]->(tm) "
                "SET r.source_package = $source_package, "
                "r.source_class = $source_class, "
                "r.source_method = $source_method, "
                "r.target_package = $target_package, "
                "r.target_class = $target_class, "
                "r.target_method = $target_method"
            )
            tx.run(
                call_query,
                source_method=method_call.source_method,
                source_class=class_node.name,
                source_package=package_name,
                target_method=method_call.target_method,
                target_class=method_call.target_class,
                target_package=method_call.target_package,
            )

    def add_bean(self, bean: Bean, project_name: str):
        """Adds a Spring Bean to the database."""
        with self._driver.session() as session:
            session.execute_write(self._create_bean_node_tx, bean, project_name)

    def add_bean_dependency(self, dependency: BeanDependency, project_name: str):
        """Adds a Bean dependency to the database."""
        with self._driver.session() as session:
            session.execute_write(self._create_bean_dependency_tx, dependency, project_name)

    def add_endpoint(self, endpoint: Endpoint, project_name: str):
        """Adds a REST API endpoint to the database."""
        with self._driver.session() as session:
            session.execute_write(self._create_endpoint_node_tx, endpoint, project_name)

    def add_mybatis_mapper(self, mapper: MyBatisMapper, project_name: str):
        """Adds a MyBatis mapper to the database."""
        with self._driver.session() as session:
            session.execute_write(self._create_mybatis_mapper_node_tx, mapper, project_name)

    def add_jpa_entity(self, entity: JpaEntity, project_name: str):
        """Adds a JPA entity to the database."""
        with self._driver.session() as session:
            session.execute_write(self._create_jpa_entity_node_tx, entity, project_name)

    def add_config_file(self, config_file: ConfigFile, project_name: str):
        """Adds a configuration file to the database."""
        with self._driver.session() as session:
            session.execute_write(self._create_config_file_node_tx, config_file, project_name)

    def add_test_class(self, test_class: TestClass, project_name: str):
        """Adds a test class to the database."""
        with self._driver.session() as session:
            session.execute_write(self._create_test_class_node_tx, test_class, project_name)

    def add_sql_statement(self, sql_statement: SqlStatement, project_name: str):
        """Adds a SQL statement to the database."""
        with self._driver.session() as session:
            session.execute_write(self._create_sql_statement_node_tx, sql_statement, project_name)

    @staticmethod
    def _create_bean_node_tx(tx, bean: Bean, project_name: str):
        """A transaction function to create a Spring Bean node."""
        bean_query = (
            "MERGE (b:Bean {name: $name}) "
            "SET b.type = $type, b.scope = $scope, b.class_name = $class_name, "
            "b.package_name = $package_name, b.annotation_names = $annotation_names, "
            "b.method_count = $method_count, b.property_count = $property_count, "
            "b.project_name = $project_name"
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
            project_name=project_name
        )

    @staticmethod
    def _create_bean_dependency_tx(tx, dependency: BeanDependency, project_name: str):
        """A transaction function to create a Bean dependency relationship."""
        # Create source and target beans if they don't exist
        source_bean_query = "MERGE (sb:Bean {name: $source_bean})"
        target_bean_query = "MERGE (tb:Bean {name: $target_bean})"
        
        tx.run(source_bean_query, source_bean=dependency.source_bean)
        tx.run(target_bean_query, target_bean=dependency.target_bean)
        
        # Create dependency relationship
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
            parameter_name=dependency.parameter_name
        )

    @staticmethod
    def _create_endpoint_node_tx(tx, endpoint: Endpoint, project_name: str):
        """A transaction function to create a REST API endpoint node."""
        endpoint_query = (
            "MERGE (e:Endpoint {path: $path, method: $method}) "
            "SET e.controller_class = $controller_class, e.handler_method = $handler_method, "
            "e.endpoint_parameters = $endpoint_parameters, e.return_type = $return_type, "
            "e.annotations = $annotations, e.full_path = $full_path, "
            "e.project_name = $project_name"
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
            project_name=project_name
        )

    @staticmethod
    def _create_mybatis_mapper_node_tx(tx, mapper: MyBatisMapper, project_name: str):
        """A transaction function to create a MyBatis mapper node."""
        mapper_query = (
            "MERGE (m:MyBatisMapper {name: $name}) "
            "SET m.type = $type, m.namespace = $namespace, m.methods = $methods, "
            "m.sql_statements = $sql_statements, m.file_path = $file_path, "
            "m.package_name = $package_name"
        )
        tx.run(
            mapper_query,
            name=mapper.name,
            type=mapper.type,
            namespace=mapper.namespace,
            methods=json.dumps(mapper.methods),
            sql_statements=json.dumps(mapper.sql_statements),
            file_path=mapper.file_path,
            package_name=mapper.package_name
        )

    @staticmethod
    def _create_jpa_entity_node_tx(tx, entity: JpaEntity, project_name: str):
        """A transaction function to create a JPA entity node."""
        entity_query = (
            "MERGE (e:JpaEntity {name: $name}) "
            "SET e.table_name = $table_name, e.columns = $columns, "
            "e.relationships = $relationships, e.annotations = $annotations, "
            "e.package_name = $package_name, e.file_path = $file_path"
        )
        tx.run(
            entity_query,
            name=entity.name,
            table_name=entity.table_name,
            columns=json.dumps(entity.columns),
            relationships=json.dumps(entity.relationships),
            annotations=json.dumps(entity.annotations),
            package_name=entity.package_name,
            file_path=entity.file_path
        )

    @staticmethod
    def _create_config_file_node_tx(tx, config_file: ConfigFile, project_name: str):
        """A transaction function to create a configuration file node."""
        config_query = (
            "MERGE (c:ConfigFile {name: $name}) "
            "SET c.file_path = $file_path, c.file_type = $file_type, "
            "c.properties = $properties, c.sections = $sections, "
            "c.profiles = $profiles, c.environment = $environment"
        )
        tx.run(
            config_query,
            name=config_file.name,
            file_path=config_file.file_path,
            file_type=config_file.file_type,
            properties=json.dumps(config_file.properties),
            sections=json.dumps(config_file.sections),
            profiles=json.dumps(config_file.profiles),
            environment=config_file.environment
        )

    @staticmethod
    def _create_test_class_node_tx(tx, test_class: TestClass, project_name: str):
        """A transaction function to create a test class node."""
        test_query = (
            "MERGE (t:TestClass {name: $name}) "
            "SET t.package_name = $package_name, t.test_framework = $test_framework, "
            "t.test_type = $test_type, t.annotations = $annotations, "
            "t.test_methods = $test_methods, t.setup_methods = $setup_methods, "
            "t.mock_dependencies = $mock_dependencies, t.test_configurations = $test_configurations, "
            "t.file_path = $file_path, t.project_name = $project_name"
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
            project_name=project_name
        )

    @staticmethod
    def _create_sql_statement_node_tx(tx, sql_statement: SqlStatement, project_name: str):
        """A transaction function to create a SQL statement node."""
        sql_query = (
            "MERGE (s:SqlStatement {id: $id, mapper_name: $mapper_name}) "
            "SET s.sql_type = $sql_type, s.sql_content = $sql_content, "
            "s.parameter_type = $parameter_type, s.result_type = $result_type, "
            "s.result_map = $result_map, s.annotations = $annotations, "
            "s.project_name = $project_name"
        )
        tx.run(
            sql_query,
            id=sql_statement.id,
            mapper_name=sql_statement.mapper_name,
            sql_type=sql_statement.sql_type,
            sql_content=sql_statement.sql_content,
            parameter_type=sql_statement.parameter_type,
            result_type=sql_statement.result_type,
            result_map=sql_statement.result_map,
            annotations=json.dumps([a.dict() for a in sql_statement.annotations]),
            project_name=project_name
        )

    @staticmethod
    def _create_mapper_sql_relationship_tx(tx, mapper_name: str, sql_id: str, project_name: str):
        """A transaction function to create a relationship between MyBatisMapper and SqlStatement."""
        relationship_query = (
            "MATCH (m:MyBatisMapper {name: $mapper_name, project_name: $project_name}) "
            "MATCH (s:SqlStatement {id: $sql_id, mapper_name: $mapper_name, project_name: $project_name}) "
            "MERGE (m)-[:HAS_SQL_STATEMENT]->(s)"
        )
        tx.run(
            relationship_query,
            mapper_name=mapper_name,
            sql_id=sql_id,
            project_name=project_name
        )

    def get_crud_matrix(self, project_name: str = None):
        """Get CRUD matrix showing class-table relationships."""
        query = """
        MATCH (c:Class {project_name: $project_name})
        OPTIONAL MATCH (c)-[:HAS_METHOD]->(m:Method)
        OPTIONAL MATCH (m)-[:CALLS]->(s:SqlStatement {project_name: $project_name})
        WITH c, m, s, 
             CASE 
               WHEN s.sql_type = 'SELECT' THEN 'R'
               WHEN s.sql_type = 'INSERT' THEN 'C'
               WHEN s.sql_type = 'UPDATE' THEN 'U'
               WHEN s.sql_type = 'DELETE' THEN 'D'
               ELSE 'O'
             END as crud_operation
        RETURN c.name as class_name,
               c.package_name as package_name,
               collect(DISTINCT s.mapper_name) as tables,
               collect(DISTINCT crud_operation) as operations,
               collect(DISTINCT s.id) as sql_statements
        ORDER BY c.name
        """
        
        with self._driver.session() as session:
            result = session.run(query, project_name=project_name)
            return [record.data() for record in result]

    def get_table_crud_summary(self, project_name: str = None):
        """Get CRUD summary for each table."""
        query = """
        MATCH (s:SqlStatement {project_name: $project_name})
        WITH s.mapper_name as table_name,
             s.sql_type as operation,
             count(s) as count
        RETURN table_name,
               collect({operation: operation, count: count}) as operations
        ORDER BY table_name
        """
        
        with self._driver.session() as session:
            result = session.run(query, project_name=project_name)
            return [record.data() for record in result]
