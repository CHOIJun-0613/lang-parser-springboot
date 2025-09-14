import json

from neo4j import Driver, GraphDatabase

from src.models.graph_entities import Class, Package


class GraphDB:
    """A service for interacting with the Neo4j database."""

    def __init__(self, uri, user, password):
        """Initializes the database driver."""
        self._driver: Driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        """Closes the database connection."""
        self._driver.close()

    def add_package(self, package_node: Package):
        """Adds a package to the database."""
        with self._driver.session() as session:
            session.write_transaction(self._create_package_node_tx, package_node)

    def add_class(self, class_node: Class, package_name: str):
        """Adds a class and its relationships to the database
        in a single transaction."""
        with self._driver.session() as session:
            session.write_transaction(self._create_class_node_tx, class_node, package_name)

    @staticmethod
    def _create_package_node_tx(tx, package_node: Package):
        """A transaction function to create a package node."""
        package_query = (
            "MERGE (p:Package {name: $name})"
        )
        tx.run(
            package_query,
            name=package_node.name,
        )

    @staticmethod
    def _create_class_node_tx(tx, class_node: Class, package_name: str):
        """A transaction function to create a class, its properties,
        and its method calls."""
        # Create or merge the class node itself
        class_query = (
            "MERGE (c:Class {name: $name}) "
            "SET c.file_path = $file_path, c.type = $type, "
            "c.source = $source"  # Add c.source
        )
        tx.run(
            class_query,
            name=class_node.name,
            file_path=class_node.file_path,
            type=class_node.type,
            source=class_node.source,
        ) # Pass source

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

            method_query = (
                "MATCH (c:Class {name: $class_name}) "
                "MERGE (m:Method {name: $method_name, class_name: $class_name}) " # Unique identifier for method
                "SET m.return_type = $return_type, "
                "m.parameters_json = $parameters_json, "
                "m.modifiers_json = $modifiers_json, m.source = $source " # Add m.source
                "MERGE (c)-[:HAS_METHOD]->(m)"
            )
            tx.run(
                method_query,
                class_name=class_node.name,
                method_name=method.name,
                return_type=method.return_type,
                parameters_json=parameters_json,
                modifiers_json=modifiers_json,
                source=method.source,
            ) # Pass source
        # --- End of new method relationships logic ---

        # Create properties and relationships
        for prop in class_node.properties:
            # Serialize modifiers to JSON string
            prop_modifiers_json = json.dumps(prop.modifiers)
            
            prop_query = (
                "MATCH (c:Class {name: $class_name}) "
                "MERGE (p:Property {name: $prop_name, type: $prop_type}) "
                "SET p.modifiers_json = $prop_modifiers_json " # Set modifiers as JSON
                "MERGE (c)-[:HAS_PROPERTY]->(p)"
            )
            tx.run(
                prop_query,
                class_name=class_node.name,
                prop_name=prop.name,
                prop_type=prop.type,
                prop_modifiers_json=prop_modifiers_json, # Pass modifiers as JSON
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
