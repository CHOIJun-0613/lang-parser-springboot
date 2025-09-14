import click
import sys
import os
from dotenv import load_dotenv

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.services.java_parser import parse_java_project
from src.services.graph_db import GraphDB

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

if __name__ == '__main__':
    cli()
