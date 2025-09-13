# Phase 0: Research

This document outlines the research required to resolve the `NEEDS CLARIFICATION` markers identified in the implementation plan.

## 1. Java Parsing Library for Python

- **Task**: Research and select a Python library for parsing Java source code.
- **Candidates**: `javalang`, `plyj`, `tree-sitter`.
- **Evaluation Criteria**:
    - Accuracy in parsing modern Java syntax.
    - Ease of traversing the Abstract Syntax Tree (AST).
    - Performance on large codebases.
    - Quality of documentation and community support.
- **Decision**: TBD
- **Rationale**: TBD

## 2. Target Platform and File Handling

- **Task**: Determine the primary operating system for this tool.
- **Considerations**:
    - File path conventions (e.g., `\` vs `/`).
    - Filesystem permissions.
    - Cross-platform compatibility of the chosen libraries.
- **Decision**: TBD
- **Rationale**: TBD

## 3. Neo4j Data Modeling

- **Task**: Define best practices for the graph schema.
- **Considerations**:
    - Node labels (e.g., `Class`, `Interface`, `Enum`).
    - Edge types (e.g., `CALLS`, `IMPLEMENTS`, `EXTENDS`).
    - Properties for nodes and edges (e.g., `name`, `signature`, `file_path`).
- **Decision**: TBD
- **Rationale**: TBD

## 4. Performance at Scale

- **Task**: Define performance goals.
- **Considerations**:
    - Average number of `.java` files in a target project.
    - Acceptable analysis time (e.g., seconds vs. minutes).
- **Decision**: TBD
- **Rationale**: TBD

