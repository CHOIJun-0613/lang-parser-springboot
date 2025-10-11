import os

import click
from neo4j import GraphDatabase

from csa.cli.core.lifecycle import with_command_lifecycle
from csa.services.neo4j_connection_pool import get_connection_pool
from csa.services.sequence_diagram_generator import SequenceDiagramGenerator


@click.command(name="query")
@click.option("--neo4j-uri", default=os.getenv("NEO4J_URI", "bolt://localhost:7687"), help="Neo4j URI")
@click.option("--neo4j-user", default=os.getenv("NEO4J_USER", "neo4j"), help="Neo4j username")
@click.option("--neo4j-password", default=os.getenv("NEO4J_PASSWORD"), help="Neo4j password")
@click.option("--neo4j-database", default=os.getenv("NEO4J_DATABASE", "neo4j"), help="Neo4j database name")
@click.option("--query", help="Custom Cypher query to execute")
@click.option("--basic", is_flag=True, help="Run basic class query")
@click.option("--detailed", is_flag=True, help="Run detailed class query with methods and properties")
@click.option("--inheritance", is_flag=True, help="Run inheritance relationship query")
@click.option("--package", is_flag=True, help="Run package-based class query")
@with_command_lifecycle("query")
def query_command(neo4j_uri, neo4j_user, neo4j_password, neo4j_database, query, basic, detailed, inheritance, package):
    """Execute predefined or custom Cypher queries against Neo4j."""

    queries = {
        "basic": """
        MATCH (c:Class)
        RETURN
            c.name AS name,
            c.logical_name AS logical_name,
            c.file_path AS file_path,
            c.type AS type,
            c.source AS source
        ORDER BY c.name
        """,
        "detailed": """
        MATCH (c:Class)
        OPTIONAL MATCH (c)-[:HAS_METHOD]->(m:Method)
        OPTIONAL MATCH (c)-[:HAS_FIELD]->(p:Field)
        OPTIONAL MATCH (pkg:Package)-[:CONTAINS]->(c)
        RETURN
            c.name AS class_name,
            c.logical_name AS class_logical_name,
            c.file_path AS file_path,
            c.type AS class_type,
            pkg.name AS package_name,
            collect(DISTINCT m.name) AS methods,
            collect(DISTINCT p.name) AS properties
        ORDER BY c.name
        """,
        "inheritance": """
        MATCH (c:Class)
        OPTIONAL MATCH (c)-[:EXTENDS]->(super:Class)
        OPTIONAL MATCH (c)-[:IMPLEMENTS]->(impl:Class)
        RETURN
            c.name AS class_name,
            c.logical_name AS class_logical_name,
            c.type AS class_type,
            collect(DISTINCT super.name) AS extends,
            collect(DISTINCT impl.name) AS implements
        ORDER BY c.name
        """,
        "package": """
        MATCH (pkg:Package)-[:CONTAINS]->(c:Class)
        OPTIONAL MATCH (c)-[:HAS_METHOD]->(m:Method)
        OPTIONAL MATCH (c)-[:HAS_FIELD]->(p:Field)
        RETURN
            pkg.name AS package_name,
            pkg.logical_name AS package_logical_name,
            collect(DISTINCT c.name) AS classes,
            count(DISTINCT m) AS total_methods,
            count(DISTINCT p) AS total_properties
        ORDER BY pkg.name
        """,
    }

    if query:
        cypher_query = query
        description = "Custom Query"
    elif basic:
        cypher_query = queries["basic"]
        description = "Basic Class Query"
    elif detailed:
        cypher_query = queries["detailed"]
        description = "Detailed Class Query"
    elif inheritance:
        cypher_query = queries["inheritance"]
        description = "Inheritance Query"
    elif package:
        cypher_query = queries["package"]
        description = "Package Query"
    else:
        click.echo("Error: Please specify a query type or provide a custom query.")
        click.echo("Available options: --basic, --detailed, --inheritance, --package, or --query")
        return

    try:
        pool = get_connection_pool()
        if not pool.is_initialized():
            pool_size = int(os.getenv("NEO4J_POOL_SIZE", "10"))
            pool.initialize(neo4j_uri, neo4j_user, neo4j_password, neo4j_database, pool_size)

        conn = pool.acquire()
        try:
            with conn.session() as session:
                click.echo(f"Executing: {description}")
                click.echo("=" * 50)

                records = list(session.run(cypher_query))

                if not records:
                    click.echo("No results found.")
                    return

                headers = list(records[0].keys())
                click.echo(" | ".join(f"{header:20}" for header in headers))
                click.echo("-" * (len(headers) * 23))

                for record in records:
                    row = []
                    for header in headers:
                        value = record[header]
                        if value is None:
                            row.append("None")
                        elif isinstance(value, (list, dict)):
                            text_value = str(value)
                            row.append(text_value[:50] + "..." if len(text_value) > 50 else text_value)
                        else:
                            row.append(str(value)[:20])
                    click.echo(" | ".join(f"{cell:20}" for cell in row))

                click.echo(f"\nTotal: {len(records)} results found.")
        finally:
            pool.release(conn)
    except Exception as exc:  # pylint: disable=broad-except
        click.echo(f"Error executing query: {exc}")


@click.command(name="list-classes")
@click.option("--neo4j-uri", default=os.getenv("NEO4J_URI", "bolt://localhost:7687"), help="Neo4j URI")
@click.option("--neo4j-user", default=os.getenv("NEO4J_USER", "neo4j"), help="Neo4j username")
@click.option("--neo4j-database", default=os.getenv("NEO4J_DATABASE", "neo4j"), help="Neo4j database name")
@with_command_lifecycle("list-classes")
def list_classes_command(neo4j_uri, neo4j_user, neo4j_database):
    """List all available classes stored in Neo4j."""

    driver = None
    try:
        neo4j_password = os.getenv("NEO4J_PASSWORD")
        if not neo4j_password:
            click.echo("Error: NEO4J_PASSWORD environment variable is not set.")
            click.echo("Please set NEO4J_PASSWORD in your .env file or environment variables.")
            return

        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        generator = SequenceDiagramGenerator(driver)

        classes = generator.get_available_classes()
        if not classes:
            click.echo("No classes found in the database.")
            return

        click.echo("Available classes:")
        click.echo("=" * 80)
        click.echo(f"{'Class Name':<30} {'Package':<30} {'Type':<10}")
        click.echo("-" * 80)

        for cls in classes:
            package_name = cls.get("package_name") or "N/A"
            class_type = cls.get("type") or "N/A"
            click.echo(f"{cls['name']:<30} {package_name:<30} {class_type:<10}")

        click.echo(f"\nTotal: {len(classes)} classes found.")
    except Exception as exc:  # pylint: disable=broad-except
        click.echo(f"Error listing classes: {exc}")
    finally:
        if driver:
            driver.close()


@click.command(name="list-methods")
@click.option("--neo4j-uri", default=os.getenv("NEO4J_URI", "bolt://localhost:7687"), help="Neo4j URI")
@click.option("--neo4j-user", default=os.getenv("NEO4J_USER", "neo4j"), help="Neo4j username")
@click.option("--class-name", required=True, help="Name of the class to list methods for")
@with_command_lifecycle("list-methods")
def list_methods_command(neo4j_uri, neo4j_user, class_name):
    """List all methods declared for the specified class."""

    driver = None
    try:
        neo4j_password = os.getenv("NEO4J_PASSWORD")
        if not neo4j_password:
            click.echo("Error: NEO4J_PASSWORD environment variable is not set.")
            click.echo("Please set NEO4J_PASSWORD in your .env file or environment variables.")
            return

        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        generator = SequenceDiagramGenerator(driver)

        methods = generator.get_class_methods(class_name)
        if not methods:
            click.echo(f"No methods found for class '{class_name}'.")
            return

        click.echo(f"Methods for class '{class_name}':")
        click.echo("=" * 80)
        click.echo(f"{'Method Name':<30} {'Return Type':<20} {'Logical Name':<30}")
        click.echo("-" * 80)

        for method in methods:
            click.echo(f"{method['name']:<30} {method['return_type']:<20} {method['logical_name']:<30}")

        click.echo(f"\nTotal: {len(methods)} methods found.")
    except Exception as exc:  # pylint: disable=broad-except
        click.echo(f"Error listing methods: {exc}")
    finally:
        if driver:
            driver.close()


def register(cli: click.Group) -> None:
    """Attach graph-related commands to the given CLI group."""
    cli.add_command(query_command)
    cli.add_command(list_classes_command)
    cli.add_command(list_methods_command)


__all__ = ["register"]
