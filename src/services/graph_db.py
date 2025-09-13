from neo4j import GraphDatabase, Driver
from src.models.graph_entities import Class, MethodCall

class GraphDB:
    """A service for interacting with the Neo4j database."""

    def __init__(self, uri, user, password):
        """Initializes the database driver."""
        self._driver: Driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        """Closes the database connection."""
        self._driver.close()

    def add_class(self, class_node: Class):
        """Adds a class and its relationships to the database in a single transaction."""
        with self._driver.session() as session:
            session.write_transaction(self._create_class_node_tx, class_node)

    @staticmethod
    def _create_class_node_tx(tx, class_node: Class):
        """A transaction function to create a class, its properties, and its method calls."""
        # Create or merge the class node itself
        class_query = (
            "MERGE (c:Class {name: $name, package: $package}) "
            "SET c.file_path = $file_path, c.type = $type"
        )
        tx.run(class_query, name=class_node.name, package=class_node.package, file_path=class_node.file_path, type=class_node.type)

        # Create properties and relationships
        for prop in class_node.properties:
            prop_query = (
                "MATCH (c:Class {name: $class_name, package: $class_package}) "
                "MERGE (p:Property {name: $prop_name, type: $prop_type}) "
                "MERGE (c)-[:HAS_PROPERTY]->(p)"
            )
            tx.run(prop_query, class_name=class_node.name, class_package=class_node.package, 
                   prop_name=prop.name, prop_type=prop.type)

        # Create method call relationships
        for method_call in class_node.calls:
            call_query = (
                "MATCH (c1:Class {name: $class_name, package: $class_package}) "
                "MERGE (c2:Class {name: $target_class, package: $target_package}) "
                "MERGE (c1)-[r:CALLS]->(c2) "
                "SET r.source_method = $source_method, r.target_method = $target_method, r.target_package = $target_package, r.source_package = $source_package, r.source_class = $source_class"
            )
            tx.run(call_query, class_name=class_node.name, class_package=class_node.package, 
                   source_method=method_call.source_method, target_class=method_call.target_class,
                   target_package=method_call.target_package, target_method=method_call.target_method)
