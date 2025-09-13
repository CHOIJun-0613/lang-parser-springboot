# Quickstart

This guide provides a quick overview of how to use the Java Code Analyzer.

## 1. Prerequisites

- Python 3.11+
- An running instance of Neo4j.

## 2. Installation

```bash
# Clone the repository
git clone <repository_url>
cd <repository_directory>

# Install dependencies
pip install -r requirements.txt
```

## 3. Running the Analysis

1.  **Place your Java project** in a directory (e.g., `/path/to/my-java-project`).

2.  **Run the analyzer**:

    ```bash
    python -m java_analyzer analyze /path/to/my-java-project --neo4j-password <your_password>
    ```

## 4. Verifying the Results

1.  **Open the Neo4j Browser** (usually at `http://localhost:7474`).

2.  **Run a Cypher query** to explore the graph:

    ```cypher
    // Show all classes and their relationships
    MATCH (n:Class)-[r]->(m:Class)
    RETURN n, r, m
    LIMIT 25
    ```
