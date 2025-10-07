import json
from datetime import datetime

from neo4j import Driver, GraphDatabase

from src.models.graph_entities import Class, Package, Bean, BeanDependency, Endpoint, MyBatisMapper, SqlStatement, JpaEntity, JpaRepository, JpaQuery, ConfigFile, TestClass, Database, Table, Column, Index, Constraint
from src.utils.logger import get_logger


class GraphDB:
    """A service for interacting with the Neo4j database."""

    def __init__(self, uri, user, password):
        """Initializes the database driver."""
        self._driver: Driver = GraphDatabase.driver(uri, auth=(user, password))
        self.logger = get_logger(__name__)

    @staticmethod
    def _get_current_timestamp():
        """Get current timestamp in YYYY/MM/DD HH24:Mi:SS.sss format."""
        return datetime.now().strftime("%Y/%m/%d %H:%M:%S.%f")[:-3]  # Remove last 3 digits to get milliseconds

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
        self.logger.debug(f"Adding class: {class_node.name}, package: {package_name}, project: {project_name}")
        try:
            with self._driver.session() as session:
                session.execute_write(self._create_class_node_tx, class_node, package_name, project_name)
            self.logger.debug(f"Successfully added class: {class_node.name}")
        except Exception as e:
            self.logger.error(f"Error adding class {class_node.name}: {e}")
            raise

    @staticmethod
    def _create_package_node_tx(tx, package_node: Package, project_name: str):
        """A transaction function to create a package node."""
        current_timestamp = GraphDB._get_current_timestamp()
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

    @staticmethod
    def _create_class_node_tx(tx, class_node: Class, package_name: str, project_name: str):
        """A transaction function to create a class, its properties,
        and its method calls."""
        logger = get_logger(__name__)
        logger.debug(f"Creating class node: {class_node.name}")
        current_timestamp = GraphDB._get_current_timestamp()
        # Create or merge the class node itself
        class_query = (
            "MERGE (c:Class {name: $name}) "
            "SET c.file_path = $file_path, c.type = $type, c.sub_type = $sub_type, "
            "c.source = $source, c.logical_name = $logical_name, "
            "c.superclass = $superclass, c.interfaces = $interfaces, "
            "c.imports = $imports, c.package_name = $package_name, "
            "c.project_name = $project_name, c.description = $description, c.ai_description = $ai_description, "
            "c.updated_at = $updated_at"  # Add updated_at timestamp
        )
        tx.run(
            class_query,
            name=class_node.name,
            file_path=class_node.file_path,
            type=class_node.type,
            sub_type=class_node.sub_type or "",  # Add sub_type
            source=class_node.source,
            logical_name=class_node.logical_name,
            superclass=class_node.superclass,
            interfaces=class_node.interfaces,
            imports=class_node.imports,
            package_name=package_name,  # Add package_name
            project_name=project_name,  # Add project_name
            description=class_node.description or "",  # Add description
            ai_description=class_node.ai_description or "",  # Add ai_description
            updated_at=current_timestamp,  # Add updated_at timestamp
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
            parameters_json = json.dumps([{"name": p.name, "type": p.type} for p in method.parameters])
            # Serialize modifiers to JSON string
            modifiers_json = json.dumps(method.modifiers)
            # Serialize annotations to JSON string
            annotations_json = json.dumps([{"name": a.name, "parameters": a.parameters} for a in method.annotations])

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
                "m.project_name = $project_name, " # Add project_name
                "m.description = $description, " # Add description
                "m.ai_description = $ai_description, " # Add ai_description
                "m.updated_at = $updated_at " # Add updated_at timestamp
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
                description=method.description or "", # Add description
                ai_description=method.ai_description or "", # Add ai_description
                updated_at=current_timestamp, # Add updated_at timestamp
            ) # Pass all method properties
        # --- End of new method relationships logic ---

        # Create properties and relationships
        for prop in class_node.properties:
            # Serialize modifiers to JSON string
            prop_modifiers_json = json.dumps(prop.modifiers)
            # Serialize annotations to JSON string
            prop_annotations_json = json.dumps([{"name": a.name, "parameters": a.parameters} for a in prop.annotations])
            
            prop_query = (
                "MATCH (c:Class {name: $class_name}) "
                "MERGE (p:Field {name: $prop_name, class_name: $class_name, project_name: $project_name}) "
                "SET p.type = $prop_type, "
                "p.logical_name = $prop_logical_name, " # Add logical_name
                "p.modifiers_json = $prop_modifiers_json, " # Set modifiers as JSON
                "p.annotations_json = $prop_annotations_json, " # Set annotations as JSON
                "p.initial_value = $prop_initial_value, " # Set initial value
                "p.package_name = $package_name, " # Add package_name
                "p.project_name = $project_name, " # Add project_name
                "p.description = $prop_description, " # Add description
                "p.ai_description = $prop_ai_description, " # Add ai_description
                "p.updated_at = $updated_at " # Add updated_at timestamp
                "MERGE (c)-[:HAS_FIELD]->(p)"
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
                prop_description=prop.description or "", # Add description
                prop_ai_description=prop.ai_description or "", # Add ai_description
                updated_at=current_timestamp, # Add updated_at timestamp
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

    def add_jpa_repository(self, repository: JpaRepository, project_name: str):
        """Adds a JPA repository to the database."""
        with self._driver.session() as session:
            session.execute_write(self._create_jpa_repository_node_tx, repository, project_name)

    def add_jpa_query(self, query: JpaQuery, project_name: str):
        """Adds a JPA query to the database."""
        with self._driver.session() as session:
            session.execute_write(self._create_jpa_query_node_tx, query, project_name)

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

    def add_database(self, database: Database, project_name: str):
        """Adds a database to the graph."""
        with self._driver.session() as session:
            session.execute_write(self._create_database_node_tx, database, project_name)

    def add_table(self, table: Table, database_name: str, project_name: str):
        """Adds a table to the graph."""
        with self._driver.session() as session:
            session.execute_write(self._create_table_node_tx, table, database_name, project_name)

    def add_column(self, column: Column, table_name: str, project_name: str):
        """Adds a column to the graph."""
        with self._driver.session() as session:
            session.execute_write(self._create_column_node_tx, column, table_name, project_name)

    def add_index(self, index: Index, table_name: str, project_name: str):
        """Adds an index to the graph."""
        with self._driver.session() as session:
            session.execute_write(self._create_index_node_tx, index, table_name, project_name)

    def add_constraint(self, constraint: Constraint, table_name: str, project_name: str):
        """Adds a constraint to the graph."""
        with self._driver.session() as session:
            session.execute_write(self._create_constraint_node_tx, constraint, table_name, project_name)

    @staticmethod
    def _create_bean_node_tx(tx, bean: Bean, project_name: str):
        """A transaction function to create a Spring Bean node."""
        current_timestamp = GraphDB._get_current_timestamp()
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
            updated_at=current_timestamp
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
        current_timestamp = GraphDB._get_current_timestamp()
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
            updated_at=current_timestamp
        )

    @staticmethod
    def _create_mybatis_mapper_node_tx(tx, mapper: MyBatisMapper, project_name: str):
        """A transaction function to create a MyBatis mapper node."""
        current_timestamp = GraphDB._get_current_timestamp()
        mapper_query = (
            "MERGE (m:MyBatisMapper {name: $name, project_name: $project_name}) "
            "SET m.type = $type, m.namespace = $namespace, m.methods = $methods, "
            "m.sql_statements = $sql_statements, m.file_path = $file_path, "
            "m.package_name = $package_name, m.description = $description, m.ai_description = $ai_description, "
            "m.updated_at = $updated_at"
        )
        tx.run(
            mapper_query,
            name=mapper.name,
            project_name=project_name,
            type=mapper.type,
            namespace=mapper.namespace,
            methods=json.dumps(mapper.methods),
            sql_statements=json.dumps(mapper.sql_statements),
            file_path=mapper.file_path,
            package_name=mapper.package_name,
            description=mapper.description or "",
            ai_description=mapper.ai_description or "",
            updated_at=current_timestamp
        )

    @staticmethod
    def _create_jpa_entity_node_tx(tx, entity: JpaEntity, project_name: str):
        """A transaction function to create a JPA entity node."""
        current_timestamp = GraphDB._get_current_timestamp()
        entity_query = (
            "MERGE (e:JpaEntity {name: $name}) "
            "SET e.table_name = $table_name, e.columns = $columns, "
            "e.relationships = $relationships, e.annotations = $annotations, "
            "e.package_name = $package_name, e.file_path = $file_path, "
            "e.description = $description, e.ai_description = $ai_description, "
            "e.updated_at = $updated_at"
        )
        tx.run(
            entity_query,
            name=entity.name,
            table_name=entity.table_name,
            columns=json.dumps(entity.columns),
            relationships=json.dumps(entity.relationships),
            annotations=json.dumps(entity.annotations),
            package_name=entity.package_name,
            file_path=entity.file_path,
            project_name=project_name,
            description=entity.description or "",
            ai_description=entity.ai_description or "",
            updated_at=current_timestamp
        )

    @staticmethod
    def _create_jpa_repository_node_tx(tx, repository: JpaRepository, project_name: str):
        """A transaction function to create a JPA repository node."""
        current_timestamp = GraphDB._get_current_timestamp()
        repository_query = (
            "MERGE (r:JpaRepository {name: $name, project_name: $project_name}) "
            "SET r.entity_type = $entity_type, r.methods = $methods, "
            "r.package_name = $package_name, r.file_path = $file_path, "
            "r.annotations = $annotations, r.description = $description, "
            "r.ai_description = $ai_description, r.updated_at = $updated_at"
        )
        tx.run(
            repository_query,
            name=repository.name,
            project_name=project_name,
            entity_type=repository.entity_type,
            methods=json.dumps(repository.methods),
            package_name=repository.package_name,
            file_path=repository.file_path,
            annotations=json.dumps(repository.annotations),
            description=repository.description or "",
            ai_description=repository.ai_description or "",
            updated_at=current_timestamp
        )

    @staticmethod
    def _create_jpa_query_node_tx(tx, query: JpaQuery, project_name: str):
        """A transaction function to create a JPA query node."""
        current_timestamp = GraphDB._get_current_timestamp()
        query_query = (
            "MERGE (q:JpaQuery {name: $name, project_name: $project_name}) "
            "SET q.query_type = $query_type, q.query_content = $query_content, "
            "q.return_type = $return_type, q.parameters = $parameters, "
            "q.repository_name = $repository_name, q.method_name = $method_name, "
            "q.annotations = $annotations, q.description = $description, "
            "q.ai_description = $ai_description, q.updated_at = $updated_at"
        )
        parameters_dict = {
            "name": str(query.name) if query.name else "",
            "project_name": str(project_name) if project_name else "",
            "query_type": str(query.query_type) if query.query_type else "",
            "query_content": str(query.query_content) if query.query_content else "",
            "return_type": str(query.return_type) if query.return_type else "",
            "parameters": json.dumps(query.parameters if isinstance(query.parameters, list) else []),
            "repository_name": str(query.repository_name) if query.repository_name else "",
            "method_name": str(query.method_name) if query.method_name else "",
            "annotations": json.dumps(query.annotations if isinstance(query.annotations, list) else []),
            "description": str(query.description) if query.description else "",
            "ai_description": str(query.ai_description) if query.ai_description else "",
            "updated_at": current_timestamp
        }
        tx.run(query_query, parameters_dict)

    @staticmethod
    def _create_config_file_node_tx(tx, config_file: ConfigFile, project_name: str):
        """A transaction function to create a configuration file node."""
        current_timestamp = GraphDB._get_current_timestamp()
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
            updated_at=current_timestamp
        )

    @staticmethod
    def _create_test_class_node_tx(tx, test_class: TestClass, project_name: str):
        """A transaction function to create a test class node."""
        current_timestamp = GraphDB._get_current_timestamp()
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
            updated_at=current_timestamp
        )

    @staticmethod
    def _create_sql_statement_node_tx(tx, sql_statement: SqlStatement, project_name: str):
        """A transaction function to create a SQL statement node."""
        current_timestamp = GraphDB._get_current_timestamp()
        sql_query = (
            "MERGE (s:SqlStatement {id: $id, mapper_name: $mapper_name}) "
            "SET s.sql_type = $sql_type, s.sql_content = $sql_content, "
            "s.parameter_type = $parameter_type, s.result_type = $result_type, "
            "s.result_map = $result_map, s.annotations = $annotations, "
            "s.project_name = $project_name, s.description = $description, s.ai_description = $ai_description, "
            "s.complexity_score = $complexity_score, s.tables = $tables, s.columns = $columns, "
            "s.sql_analysis = $sql_analysis, s.updated_at = $updated_at"
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
            annotations=json.dumps([{"name": a.name, "parameters": a.parameters} for a in sql_statement.annotations]),
            project_name=project_name,
            description=sql_statement.description or "",
            ai_description=sql_statement.ai_description or "",
            complexity_score=sql_statement.complexity_score,
            tables=json.dumps(sql_statement.tables),
            columns=json.dumps(sql_statement.columns),
            sql_analysis=json.dumps(sql_statement.sql_analysis),
            updated_at=current_timestamp
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

    @staticmethod
    def _create_database_node_tx(tx, database: Database, project_name: str):
        """A transaction function to create a Database node."""
        current_timestamp = GraphDB._get_current_timestamp()
        database_query = (
            "MERGE (d:Database {name: $name}) "
            "SET d.version = $version, d.environment = $environment, "
            "d.project_name = $project_name, d.description = $description, "
            "d.ai_description = $ai_description, d.updated_at = $updated_at"
        )
        tx.run(
            database_query,
            name=database.name,
            version=database.version,
            environment=database.environment,
            project_name=project_name,
            description=database.description or "",
            ai_description=database.ai_description or "",
            updated_at=current_timestamp
        )

    @staticmethod
    def _create_table_node_tx(tx, table: Table, database_name: str, project_name: str):
        """A transaction function to create a Table node."""
        current_timestamp = GraphDB._get_current_timestamp()
        table_query = (
            "MERGE (t:Table {name: $name}) "
            "SET t.schema = $schema, t.database_name = $database_name, "
            "t.project_name = $project_name, t.comment = $comment, "
            "t.ai_description = $ai_description, t.updated_at = $updated_at"
        )
        tx.run(
            table_query,
            name=table.name,
            schema=table.schema,
            database_name=database_name,
            project_name=project_name,
            comment=table.comment or "",
            ai_description=table.ai_description or "",
            updated_at=current_timestamp
        )

        # Create relationship between database and table
        db_table_query = (
            "MATCH (d:Database {name: $database_name}) "
            "MATCH (t:Table {name: $table_name}) "
            "MERGE (d)-[:CONTAINS]->(t)"
        )
        tx.run(
            db_table_query,
            database_name=database_name,
            table_name=table.name
        )

    @staticmethod
    def _create_column_node_tx(tx, column: Column, table_name: str, project_name: str):
        """A transaction function to create a Column node."""
        current_timestamp = GraphDB._get_current_timestamp()
        column_query = (
            "MERGE (c:Column {name: $name, table_name: $table_name}) "
            "SET c.data_type = $data_type, c.nullable = $nullable, "
            "c.unique = $unique, c.primary_key = $primary_key, "
            "c.default_value = $default_value, c.constraints = $constraints, "
            "c.project_name = $project_name, c.comment = $comment, "
            "c.ai_description = $ai_description, c.updated_at = $updated_at"
        )
        tx.run(
            column_query,
            name=column.name,
            table_name=table_name,
            data_type=column.data_type,
            nullable=column.nullable,
            unique=column.unique,
            primary_key=column.primary_key,
            default_value=column.default_value or "",
            constraints=json.dumps(column.constraints),
            project_name=project_name,
            comment=column.comment or "",
            ai_description=column.ai_description or "",
            updated_at=current_timestamp
        )

        # Create relationship between table and column
        table_column_query = (
            "MATCH (t:Table {name: $table_name}) "
            "MATCH (c:Column {name: $column_name, table_name: $table_name}) "
            "MERGE (t)-[:HAS_COLUMN]->(c)"
        )
        tx.run(
            table_column_query,
            table_name=table_name,
            column_name=column.name
        )

    @staticmethod
    def _create_index_node_tx(tx, index: Index, table_name: str, project_name: str):
        """A transaction function to create an Index node."""
        current_timestamp = GraphDB._get_current_timestamp()
        index_query = (
            "MERGE (i:Index {name: $name, table_name: $table_name}) "
            "SET i.type = $type, i.columns = $columns, "
            "i.project_name = $project_name, i.description = $description, "
            "i.ai_description = $ai_description, i.updated_at = $updated_at"
        )
        tx.run(
            index_query,
            name=index.name,
            table_name=table_name,
            type=index.type,
            columns=json.dumps(index.columns),
            project_name=project_name,
            description=index.description or "",
            ai_description=index.ai_description or "",
            updated_at=current_timestamp
        )

        # Create relationship between table and index
        table_index_query = (
            "MATCH (t:Table {name: $table_name}) "
            "MATCH (i:Index {name: $index_name, table_name: $table_name}) "
            "MERGE (t)-[:HAS_INDEX]->(i)"
        )
        tx.run(
            table_index_query,
            table_name=table_name,
            index_name=index.name
        )

        # Create relationships between index and columns
        for column_name in index.columns:
            index_column_query = (
                "MATCH (i:Index {name: $index_name, table_name: $table_name}) "
                "MATCH (c:Column {name: $column_name, table_name: $table_name}) "
                "MERGE (i)-[:INCLUDES]->(c)"
            )
            tx.run(
                index_column_query,
                index_name=index.name,
                table_name=table_name,
                column_name=column_name
            )

    @staticmethod
    def _create_constraint_node_tx(tx, constraint: Constraint, table_name: str, project_name: str):
        """A transaction function to create a Constraint node."""
        current_timestamp = GraphDB._get_current_timestamp()
        constraint_query = (
            "MERGE (c:Constraint {name: $name, table_name: $table_name}) "
            "SET c.type = $type, c.definition = $definition, "
            "c.project_name = $project_name, c.description = $description, "
            "c.ai_description = $ai_description, c.updated_at = $updated_at"
        )
        tx.run(
            constraint_query,
            name=constraint.name,
            table_name=table_name,
            type=constraint.type,
            definition=constraint.definition or "",
            project_name=project_name,
            description=constraint.description or "",
            ai_description=constraint.ai_description or "",
            updated_at=current_timestamp
        )

        # Create relationship between table and constraint
        table_constraint_query = (
            "MATCH (t:Table {name: $table_name}) "
            "MATCH (c:Constraint {name: $constraint_name, table_name: $table_name}) "
            "MERGE (t)-[:HAS_CONSTRAINT]->(c)"
        )
        tx.run(
            table_constraint_query,
            table_name=table_name,
            constraint_name=constraint.name
        )

    def get_crud_matrix(self, project_name: str = None):
        """Get CRUD matrix showing class-table relationships."""
        query = """
        MATCH (c:Class)-[:HAS_METHOD]->(m:Method)
        MATCH (m)-[:CALLS]->(s:SqlStatement)
        WHERE s.tables IS NOT NULL AND s.tables <> '[]'
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
               s.tables as tables_json,
               crud_operation as operation,
               s.id as sql_id
        ORDER BY c.name
        """
        
        with self._driver.session() as session:
            result = session.run(query)
            raw_data = [record.data() for record in result]
            
            # 클래스별로 그룹화하여 매트릭스 생성
            class_matrix = {}
            for row in raw_data:
                class_name = row['class_name']
                if class_name not in class_matrix:
                    class_matrix[class_name] = {
                        'class_name': class_name,
                        'package_name': row['package_name'],
                        'tables': set(),
                        'operations': set(),
                        'sql_statements': set()
                    }
                
                # 실제 테이블 정보 파싱
                try:
                    tables_json = row['tables_json']
                    if tables_json and tables_json != '[]':
                        tables = json.loads(tables_json)
                        for table_info in tables:
                            if isinstance(table_info, dict) and 'name' in table_info:
                                class_matrix[class_name]['tables'].add(table_info['name'])
                except (json.JSONDecodeError, TypeError):
                    continue
                
                class_matrix[class_name]['operations'].add(row['operation'])
                class_matrix[class_name]['sql_statements'].add(row['sql_id'])
            
            # set을 list로 변환
            return [
                {
                    'class_name': data['class_name'],
                    'package_name': data['package_name'],
                    'tables': list(data['tables']),
                    'operations': list(data['operations']),
                    'sql_statements': list(data['sql_statements'])
                }
                for data in class_matrix.values()
            ]

    def get_table_crud_summary(self, project_name: str = None):
        """Get CRUD summary for each table."""
        query = """
        MATCH (s:SqlStatement {project_name: $project_name})
        WHERE s.tables IS NOT NULL AND s.tables <> '[]'
        RETURN s.tables as tables_json, s.sql_type as operation
        """
        
        with self._driver.session() as session:
            result = session.run(query, project_name=project_name)
            raw_data = [record.data() for record in result]
            
            # 테이블별 CRUD 통계 생성
            table_stats = {}
            for row in raw_data:
                try:
                    tables_json = row['tables_json']
                    operation = row['operation']
                    
                    if tables_json and tables_json != '[]':
                        tables = json.loads(tables_json)
                        for table_info in tables:
                            if isinstance(table_info, dict) and 'name' in table_info:
                                table_name = table_info['name']
                                if table_name not in table_stats:
                                    table_stats[table_name] = {}
                                if operation not in table_stats[table_name]:
                                    table_stats[table_name][operation] = 0
                                table_stats[table_name][operation] += 1
                except (json.JSONDecodeError, TypeError):
                    continue
            
            # 결과 형식으로 변환
            return [
                {
                    'table_name': table_name,
                    'operations': [{'operation': op, 'count': count} for op, count in operations.items()]
                }
                for table_name, operations in table_stats.items()
            ]

    def create_method_sql_relationships(self, project_name: str):
        """Create CALLS relationships between Methods and SqlStatements for MyBatis repositories."""
        with self._driver.session() as session:
            session.execute_write(self._create_method_sql_relationships_tx, project_name)

    @staticmethod
    def _create_method_sql_relationships_tx(tx, project_name: str):
        """Create CALLS relationships between Repository methods and their corresponding SQL statements."""
        # MyBatis Repository 메서드와 SqlStatement 간의 관계 생성
        relationship_query = """
        MATCH (c:Class {project_name: $project_name})
        WHERE c.name ENDS WITH 'Repository' OR c.name ENDS WITH 'Mapper'
        MATCH (c)-[:HAS_METHOD]->(m:Method)
        MATCH (s:SqlStatement {project_name: $project_name})
        WHERE s.mapper_name = c.name
        MERGE (m)-[:CALLS]->(s)
        RETURN count(*) as relationships_created
        """
        
        result = tx.run(relationship_query, project_name=project_name)
        return result.single()["relationships_created"]

    def delete_class_and_related_data(self, class_name: str, project_name: str):
        """Delete a specific class and all its related data from the database."""
        with self._driver.session() as session:
            session.execute_write(self._delete_class_and_related_data_tx, class_name, project_name)

    @staticmethod
    def _delete_class_and_related_data_tx(tx, class_name: str, project_name: str):
        """Transaction function to delete a class and all its related data."""
        
        # Use DETACH DELETE to remove nodes and all their relationships at once
        # This is more robust and handles all relationship types automatically
        
        # 1. Delete methods of this class (with all their relationships)
        delete_methods_query = """
        MATCH (m:Method {class_name: $class_name})
        DETACH DELETE m
        """
        tx.run(delete_methods_query, class_name=class_name)
        
        # 2. Delete fields of this class (with all their relationships)
        delete_fields_query = """
        MATCH (f:Field {class_name: $class_name, project_name: $project_name})
        DETACH DELETE f
        """
        tx.run(delete_fields_query, class_name=class_name, project_name=project_name)
        
        # 3. Delete beans related to this class (with all their relationships)
        delete_beans_query = """
        MATCH (b:Bean {class_name: $class_name, project_name: $project_name})
        DETACH DELETE b
        """
        tx.run(delete_beans_query, class_name=class_name, project_name=project_name)
        
        # 4. Delete endpoints related to this class (with all their relationships)
        delete_endpoints_query = """
        MATCH (e:Endpoint {controller_class: $class_name, project_name: $project_name})
        DETACH DELETE e
        """
        tx.run(delete_endpoints_query, class_name=class_name, project_name=project_name)
        
        # 5. Delete MyBatis mappers related to this class (with all their relationships)
        delete_mappers_query = """
        MATCH (m:MyBatisMapper {name: $class_name, project_name: $project_name})
        DETACH DELETE m
        """
        tx.run(delete_mappers_query, class_name=class_name, project_name=project_name)
        
        # 6. Delete SQL statements related to this class (with all their relationships)
        delete_sql_statements_query = """
        MATCH (s:SqlStatement {mapper_name: $class_name, project_name: $project_name})
        DETACH DELETE s
        """
        tx.run(delete_sql_statements_query, class_name=class_name, project_name=project_name)
        
        # 7. Delete JPA entities related to this class (with all their relationships)
        delete_jpa_entities_query = """
        MATCH (e:JpaEntity {name: $class_name, project_name: $project_name})
        DETACH DELETE e
        """
        tx.run(delete_jpa_entities_query, class_name=class_name, project_name=project_name)
        
        # 8. Delete test classes related to this class (with all their relationships)
        delete_test_classes_query = """
        MATCH (t:TestClass {name: $class_name, project_name: $project_name})
        DETACH DELETE t
        """
        tx.run(delete_test_classes_query, class_name=class_name, project_name=project_name)
        
        # 9. Finally, delete the class itself (with all its relationships)
        delete_class_query = """
        MATCH (c:Class {name: $class_name, project_name: $project_name})
        DETACH DELETE c
        """
        tx.run(delete_class_query, class_name=class_name, project_name=project_name)

    def get_sql_statistics(self, project_name: str = None) -> dict:
        """Get SQL statistics for the project."""
        with self._driver.session() as session:
            if project_name:
                query = """
                MATCH (s:SqlStatement)
                WHERE s.project_name = $project_name
                RETURN 
                    count(s) as total_sql,
                    sum(CASE WHEN s.sql_type = 'SELECT' THEN 1 ELSE 0 END) as SELECT,
                    sum(CASE WHEN s.sql_type = 'INSERT' THEN 1 ELSE 0 END) as INSERT,
                    sum(CASE WHEN s.sql_type = 'UPDATE' THEN 1 ELSE 0 END) as UPDATE,
                    sum(CASE WHEN s.sql_type = 'DELETE' THEN 1 ELSE 0 END) as DELETE
                """
                result = session.run(query, project_name=project_name)
            else:
                query = """
                MATCH (s:SqlStatement)
                RETURN 
                    count(s) as total_sql,
                    sum(CASE WHEN s.sql_type = 'SELECT' THEN 1 ELSE 0 END) as SELECT,
                    sum(CASE WHEN s.sql_type = 'INSERT' THEN 1 ELSE 0 END) as INSERT,
                    sum(CASE WHEN s.sql_type = 'UPDATE' THEN 1 ELSE 0 END) as UPDATE,
                    sum(CASE WHEN s.sql_type = 'DELETE' THEN 1 ELSE 0 END) as DELETE
                """
                result = session.run(query)
            
            record = result.single()
            if record:
                return {
                    'total_sql': record['total_sql'],
                    'SELECT': record['SELECT'],
                    'INSERT': record['INSERT'],
                    'UPDATE': record['UPDATE'],
                    'DELETE': record['DELETE']
                }
            return {}

    def get_table_usage_statistics(self, project_name: str = None) -> list:
        """Get table usage statistics."""
        with self._driver.session() as session:
            if project_name:
                query = """
                MATCH (s:SqlStatement)
                WHERE s.project_name = $project_name AND s.tables IS NOT NULL
                UNWIND s.tables as table_info
                WITH table_info.name as table_name, s.sql_type as operation
                RETURN 
                    table_name,
                    count(*) as access_count,
                    collect(DISTINCT operation) as operations
                ORDER BY access_count DESC
                """
                result = session.run(query, project_name=project_name)
            else:
                query = """
                MATCH (s:SqlStatement)
                WHERE s.tables IS NOT NULL
                UNWIND s.tables as table_info
                WITH table_info.name as table_name, s.sql_type as operation
                RETURN 
                    table_name,
                    count(*) as access_count,
                    collect(DISTINCT operation) as operations
                ORDER BY access_count DESC
                """
                result = session.run(query)
            
            return [record.data() for record in result]

    def get_sql_complexity_statistics(self, project_name: str = None) -> dict:
        """Get SQL complexity statistics."""
        with self._driver.session() as session:
            if project_name:
                query = """
                MATCH (s:SqlStatement)
                WHERE s.project_name = $project_name AND s.complexity_score IS NOT NULL
                WITH s.complexity_score as score,
                     CASE 
                         WHEN s.complexity_score <= 3 THEN 'simple'
                         WHEN s.complexity_score <= 7 THEN 'medium'
                         WHEN s.complexity_score <= 12 THEN 'complex'
                         ELSE 'very_complex'
                     END as complexity_level
                RETURN 
                    complexity_level,
                    count(*) as count
                """
                result = session.run(query, project_name=project_name)
            else:
                query = """
                MATCH (s:SqlStatement)
                WHERE s.complexity_score IS NOT NULL
                WITH s.complexity_score as score,
                     CASE 
                         WHEN s.complexity_score <= 3 THEN 'simple'
                         WHEN s.complexity_score <= 7 THEN 'medium'
                         WHEN s.complexity_score <= 12 THEN 'complex'
                         ELSE 'very_complex'
                     END as complexity_level
                RETURN 
                    complexity_level,
                    count(*) as count
                """
                result = session.run(query)
            
            stats = {}
            for record in result:
                stats[record['complexity_level']] = record['count']
            return stats

    def get_mapper_sql_distribution(self, project_name: str = None) -> list:
        """Get mapper SQL distribution."""
        with self._driver.session() as session:
            if project_name:
                query = """
                MATCH (s:SqlStatement)
                WHERE s.project_name = $project_name
                RETURN 
                    s.mapper_name as mapper_name,
                    count(*) as sql_count,
                    collect(DISTINCT s.sql_type) as sql_types
                ORDER BY sql_count DESC
                """
                result = session.run(query, project_name=project_name)
            else:
                query = """
                MATCH (s:SqlStatement)
                RETURN 
                    s.mapper_name as mapper_name,
                    count(*) as sql_count,
                    collect(DISTINCT s.sql_type) as sql_types
                ORDER BY sql_count DESC
                """
                result = session.run(query)
            
            return [record.data() for record in result]
