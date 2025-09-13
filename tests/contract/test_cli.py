import pytest
import subprocess
from neo4j import GraphDatabase
import os
from dotenv import load_dotenv
import sys # Import sys

load_dotenv()

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "password")

# Get the path to the virtual environment's python executable
PYTHON_EXECUTABLE = sys.executable

@pytest.fixture(scope="module")
def db_driver():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    yield driver
    driver.close()

@pytest.fixture(autouse=True)
def clean_db(db_driver):
    with db_driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
    yield
    with db_driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")

def test_analyze_command(db_driver):
    # Given
    java_source_folder = os.getenv("JAVA_SOURCE_FOLDER", "./tests/sample_java_project")

    # When
    result = subprocess.run(
        [
            PYTHON_EXECUTABLE, # Use the virtual environment's python
            "-m",
            "src.cli.main",
            "analyze",
            "--java-source-folder", java_source_folder,
            "--neo4j-uri", NEO4J_URI,
            "--neo4j-user", NEO4J_USER,
            "--neo4j-password", NEO4J_PASSWORD,
        ],
        capture_output=True,
        text=True,
    )

    # Then
    assert result.returncode == 0, f"CLI command failed with error: {result.stderr}"

    with db_driver.session() as session:
        class_nodes = session.run("MATCH (c:Class) RETURN c.name AS name").data()
        class_names = {node['name'] for node in class_nodes}
        assert "Main" in class_names
        assert "Greeter" in class_names

        calls_rel = session.run(
            "MATCH (c1:Class {name: 'Main'})-[r:CALLS]->(c2:Class {name: 'Greeter'}) "
            "WHERE r.source_package = 'com.example' AND r.source_class = 'Main' AND r.source_method = 'main' AND r.target_method = 'sayHello' AND r.target_package = 'com.example' "
            "RETURN r"
        ).single()
        assert calls_rel is not None