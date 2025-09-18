import click
import sys
import os
from dotenv import load_dotenv

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.services.java_parser import parse_java_project
from src.services.graph_db import GraphDB
from neo4j import GraphDatabase

load_dotenv()

@click.group()
def cli():
    pass

@cli.command()
@click.option('--java-source-folder', default=os.getenv("JAVA_SOURCE_FOLDER"), help='Path to the Java source project folder.')
@click.option('--neo4j-uri', default=os.getenv("NEO4J_URI", "bolt://localhost:7687"), help='Neo4j URI')
@click.option('--neo4j-user', default=os.getenv("NEO4J_USER", "neo4j"), help='Neo4j username')
@click.option('--neo4j-password', default=os.getenv("NEO4J_PASSWORD"), help='Neo4j password')
@click.option('--clean', is_flag=True, help='Wipe the database before analysis.')
@click.option('--dry-run', is_flag=True, help='Parse Java files without connecting to database.')
def analyze(java_source_folder, neo4j_uri, neo4j_user, neo4j_password, clean, dry_run):
    """Analyzes a Java project and populates a Neo4j database."""
    if not java_source_folder:
        click.echo("Error: JAVA_SOURCE_FOLDER environment variable or --java-source-folder option is required.", err=True)
        exit(1)

    click.echo(f"Parsing Java project at: {java_source_folder}")
    packages_to_add, classes_to_add, class_to_package_map = parse_java_project(java_source_folder)
    
    click.echo(f"Found {len(packages_to_add)} packages and {len(classes_to_add)} classes.")
    
    if dry_run:
        click.echo("Dry run mode - not connecting to database.")
        for package_node in packages_to_add:
            click.echo(f"Package: {package_node.name}")
        for class_node in classes_to_add:
            click.echo(f"Class: {class_node.name}")
            click.echo(f"  Methods: {len(class_node.methods)}")
            click.echo(f"  Properties: {len(class_node.properties)}")
            click.echo(f"  Method calls: {len(class_node.calls)}")
        click.echo("Analysis complete (dry run).")
        return

    try:
        click.echo(f"Connecting to Neo4j at {neo4j_uri}...")
        db = GraphDB(uri=neo4j_uri, user=neo4j_user, password=neo4j_password)

        if clean:
            click.echo("Cleaning database...")
            with db._driver.session() as session:
                session.run("MATCH (n) DETACH DELETE n")

        click.echo("Adding packages to database...")
        for package_node in packages_to_add:
            db.add_package(package_node)
        
        click.echo("Adding classes to database...")
        for class_node in classes_to_add:
            # Find the package for this class using the mapping
            class_key = f"{class_to_package_map.get(class_node.name, '')}.{class_node.name}"
            package_name = class_to_package_map.get(class_key, None)
            
            if not package_name:
                # Fallback: try to find package by class name
                for key, pkg_name in class_to_package_map.items():
                    if key.endswith(f".{class_node.name}"):
                        package_name = pkg_name
                        break
            
            db.add_class(class_node, package_name)
        
        db.close()
        click.echo("Analysis complete.")
    except Exception as e:
        click.echo(f"Error connecting to database: {e}")
        click.echo("Use --dry-run flag to parse without database connection.")
        exit(1)

@cli.command()
@click.option('--neo4j-uri', default=os.getenv("NEO4J_URI", "bolt://localhost:7687"), help='Neo4j URI')
@click.option('--neo4j-user', default=os.getenv("NEO4J_USER", "neo4j"), help='Neo4j username')
@click.option('--neo4j-password', default=os.getenv("NEO4J_PASSWORD"), help='Neo4j password')
@click.option('--query', help='Custom Cypher query to execute')
@click.option('--basic', is_flag=True, help='Run basic class query')
@click.option('--detailed', is_flag=True, help='Run detailed class query with methods and properties')
@click.option('--inheritance', is_flag=True, help='Run inheritance relationship query')
@click.option('--package', is_flag=True, help='Run package-based class query')
def query(neo4j_uri, neo4j_user, neo4j_password, query, basic, detailed, inheritance, package):
    """Execute queries against the Neo4j database."""
    
    # 미리 정의된 쿼리들
    queries = {
        'basic': """
        MATCH (c:Class)
        RETURN 
            c.name AS name,
            c.logical_name AS logical_name,
            c.file_path AS file_path,
            c.type AS type,
            c.source AS source
        ORDER BY c.name
        """,
        'detailed': """
        MATCH (c:Class)
        OPTIONAL MATCH (c)-[:HAS_METHOD]->(m:Method)
        OPTIONAL MATCH (c)-[:HAS_PROPERTY]->(p:Property)
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
        'inheritance': """
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
        'package': """
        MATCH (pkg:Package)-[:CONTAINS]->(c:Class)
        OPTIONAL MATCH (c)-[:HAS_METHOD]->(m:Method)
        OPTIONAL MATCH (c)-[:HAS_PROPERTY]->(p:Property)
        RETURN 
            pkg.name AS package_name,
            pkg.logical_name AS package_logical_name,
            collect(DISTINCT c.name) AS classes,
            count(DISTINCT m) AS total_methods,
            count(DISTINCT p) AS total_properties
        ORDER BY pkg.name
        """
    }
    
    # 실행할 쿼리 결정
    if query:
        cypher_query = query
        description = "Custom Query"
    elif basic:
        cypher_query = queries['basic']
        description = "Basic Class Query"
    elif detailed:
        cypher_query = queries['detailed']
        description = "Detailed Class Query"
    elif inheritance:
        cypher_query = queries['inheritance']
        description = "Inheritance Query"
    elif package:
        cypher_query = queries['package']
        description = "Package Query"
    else:
        click.echo("Error: Please specify a query type or provide a custom query.")
        click.echo("Available options: --basic, --detailed, --inheritance, --package, or --query")
        return
    
    try:
        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        
        with driver.session() as session:
            click.echo(f"Executing: {description}")
            click.echo("=" * 50)
            
            result = session.run(cypher_query)
            records = list(result)
            
            if not records:
                click.echo("No results found.")
                return
            
            # 첫 번째 레코드의 키들을 헤더로 사용
            headers = list(records[0].keys())
            
            # 헤더 출력
            click.echo(" | ".join(f"{header:20}" for header in headers))
            click.echo("-" * (len(headers) * 23))
            
            # 데이터 출력
            for record in records:
                row = []
                for header in headers:
                    value = record[header]
                    if value is None:
                        row.append("None")
                    elif isinstance(value, (list, dict)):
                        row.append(str(value)[:50] + "..." if len(str(value)) > 50 else str(value))
                    else:
                        row.append(str(value)[:20])
                click.echo(" | ".join(f"{cell:20}" for cell in row))
            
            click.echo(f"\nTotal: {len(records)} results found.")
            
    except Exception as e:
        click.echo(f"Error executing query: {e}")
    finally:
        driver.close()

if __name__ == '__main__':
    cli()
