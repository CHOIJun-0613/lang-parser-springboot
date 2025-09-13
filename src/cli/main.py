import click
from src.services.java_parser import parse_java_project
from src.services.graph_db import GraphDB
import os
from dotenv import load_dotenv

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
def analyze(java_source_folder, neo4j_uri, neo4j_user, neo4j_password, clean):
    """Analyzes a Java project and populates a Neo4j database."""
    if not java_source_folder:
        click.echo("Error: JAVA_SOURCE_FOLDER environment variable or --java-source-folder option is required.", err=True)
        exit(1)

    db = GraphDB(uri=neo4j_uri, user=neo4j_user, password=neo4j_password)

    if clean:
        click.echo("Cleaning database...")
        with db._driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")

    click.echo(f"Parsing Java project at: {java_source_folder}")
    classes_to_add = parse_java_project(java_source_folder)
    
    click.echo(f"Found {len(classes_to_add)} classes. Adding to database...")
    for class_node in classes_to_add:
        db.add_class(class_node)
    
    db.close()
    click.echo("Analysis complete.")

if __name__ == '__main__':
    cli()
