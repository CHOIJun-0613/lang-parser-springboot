# CLI Contracts

This document defines the command-line interface for the Java code analyzer.

## `analyze` command

Analyzes a Java project directory and populates the graph database.

### Usage
```bash
python -m java_analyzer analyze [OPTIONS] <project_path>
```

### Arguments
- `<project_path>`: (Required) The path to the root directory of the Java project to analyze.

### Options
- `--neo4j-uri`: The URI for the Neo4j database. Defaults to `bolt://localhost:7687`.
- `--neo4j-user`: The username for the Neo4j database. Defaults to `neo4j`.
- `--neo4j-password`: The password for the Neo4j database.
- `--clean`: If set, the command will wipe all existing data from the database before starting the analysis.
