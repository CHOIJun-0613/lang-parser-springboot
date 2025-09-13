# Java Code Analyzer

This project is a Python-based tool for analyzing Java source code and visualizing the class relationships as a graph in a Neo4j database.

## Features

- Parses Java projects to identify classes, properties, and method calls.
- Stores the code structure in a Neo4j graph database.
- Provides a CLI for triggering the analysis.

## Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd <repository_directory>
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Usage

To analyze a Java project, use the `analyze` command:

```bash
python -m src.cli.main analyze /path/to/your/java/project --neo4j-password <your_password>
```

For more detailed instructions and examples, please see the [Quickstart Guide](./specs/001-java-class-properyties/quickstart.md).
