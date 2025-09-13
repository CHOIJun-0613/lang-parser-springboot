# Tasks for: Java Code Analyzer

This file outlines the development tasks for the Java Code Analyzer feature. Tasks are ordered by dependency, following a Test-Driven Development (TDD) approach.

## Phase 1: Setup & Configuration

*These tasks set up the project environment and basic structure.*

- **T001**: Initialize the project structure with `src` and `tests` directories.
- **T002**: Create `requirements.txt` and add initial dependencies: `pytest`, `neo4j`, `javalang`, `click`, `pydantic`.
- **T003**: Configure the `ruff` linter and formatter in `pyproject.toml`.

## Phase 2: Tests (TDD)

*Write tests before implementation. These tests will fail initially.*

- **T004** [P]: **Contract Test**: Create `tests/contract/test_cli.py`. Implement a test that runs the `analyze` command on a sample Java project and asserts that the correct nodes and edges are created in the Neo4j database.
- **T005** [P]: **Integration Test**: Create `tests/integration/test_end_to_end.py`. Implement the scenario from `quickstart.md`, simulating the full user journey from analysis to verification.

## Phase 3: Core Implementation

*Implement the core logic to make the tests pass.*

- **T006** [P]: **Data Models**: Create `src/models/graph_entities.py`. Define Pydantic models for `Class` and `Property` based on `data-model.md`.
- **T007**: **Neo4j Service**: Create `src/services/graph_db.py`. Implement a service to connect to Neo4j and include methods for adding `Class` and `Property` nodes, and `CALLS` relationships.
- **T008**: **Java Parsing Service**: Create `src/services/java_parser.py`. Implement a service that uses `javalang` to parse a directory of Java files and extracts the class, property, and method call information.
- **T009**: **CLI Implementation**: Create `src/cli/main.py`. Use `click` to implement the `analyze` command. This command will orchestrate the `java_parser` and `graph_db` services.

## Phase 4: Polish & Documentation

*Finalize the feature with unit tests and documentation.*

- **T010** [P]: **Unit Tests**: Add unit tests in `tests/unit/` for the `graph_db` and `java_parser` services, mocking external dependencies.
- **T011**: **Documentation**: Add docstrings to all new functions and classes. Update the main `README.md` with instructions on how to use the new analyzer tool.

## Parallel Execution Guide

The following tasks can be executed in parallel. 

### Group 1: Initial Tests
```bash
# These tests can be developed simultaneously as they test different aspects of the system.
gemini task T004
gemini task T005
```

### Group 2: Initial Implementation
```bash
# The data models can be created at the same time as the initial tests.
gemini task T006
```

### Group 3: Final Polish
```bash
# Unit tests can be written in parallel with documentation updates.
gemini task T010
```
