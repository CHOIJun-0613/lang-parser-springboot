# Data Model

This document defines the graph database schema based on the key entities identified in the feature specification.

## Node Labels

### `Class`
- **Description**: Represents a Java class, interface, or enum.
- **Properties**:
    - `name`: `String` (e.g., "MyClass")
    - `package`: `String` (e.g., "com.example.project")
    - `file_path`: `String` (Absolute path to the source file)
    - `type`: `String` ("class", "interface", "enum")

### `Property`
- **Description**: Represents a field or property within a class.
- **Properties**:
    - `name`: `String` (e.g., "myField")
    - `type`: `String` (e.g., "String", "int")

## Edge Labels

### `HAS_PROPERTY`
- **Description**: Connects a `Class` node to its `Property` nodes.
- **Direction**: `(Class) -[HAS_PROPERTY]-> (Property)`

### `CALLS`
- **Description**: Represents a method call from one class to another.
- **Direction**: `(Class) -[CALLS]-> (Class)`
- **Properties**:
    - `source_method`: `String` (The method making the call)
    - `target_method`: `String` (The method being called)
    - `line_number`: `Integer` (The line number of the call)
