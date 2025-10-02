# Cypher 쿼리 설명

이 문서는 프로젝트 내 Python 코드에서 사용되는 주요 Cypher 쿼리의 기능과 목적을 설명합니다.

## 1. `src/cli/main.py`

CLI 명령어 실행 시 사용되는 쿼리들입니다. 주로 데이터 조회 및 삭제에 사용됩니다.

### `analyze` 명령어

-   **설명**: `--clean` 옵션과 함께 사용될 때, 분석 전 특정 타입의 노드들을 모두 삭제합니다.
-   **쿼리**:
    ```cypher
    MATCH (n:Package) DETACH DELETE n
    MATCH (n:Class) DETACH DELETE n
    MATCH (n:Method) DETACH DELETE n
    MATCH (n:Field) DETACH DELETE n
    MATCH (n:Bean) DETACH DELETE n
    MATCH (n:Endpoint) DETACH DELETE n
    MATCH (n:MyBatisMapper) DETACH DELETE n
    MATCH (n:JpaEntity) DETACH DELETE n
    MATCH (n:ConfigFile) DETACH DELETE n
    MATCH (n:TestClass) DETACH DELETE n
    MATCH (n:SqlStatement) DETACH DELETE n
    MATCH (n:Database) DETACH DELETE n
    MATCH (n:Table) DETACH DELETE n
    MATCH (n:Column) DETACH DELETE n
    MATCH (n:Index) DETACH DELETE n
    MATCH (n:Constraint) DETACH DELETE n
    ```

-   **설명**: `--clean` 옵션이 다른 분석 타입 지정 없이 단독으로 사용될 때, 데이터베이스의 모든 노드를 삭제합니다.
-   **쿼리**:
    ```cypher
    MATCH (n) DETACH DELETE n
    ```

### `query` 명령어

-   **설명**: `--basic` 옵션. 모든 클래스의 기본 정보(이름, 논리명, 파일 경로 등)를 조회합니다.
-   **쿼리**:
    ```cypher
    MATCH (c:Class)
    RETURN
        c.name AS name,
        c.logical_name AS logical_name,
        c.file_path AS file_path,
        c.type AS type,
        c.source AS source
    ORDER BY c.name
    ```

-   **설명**: `--detailed` 옵션. 클래스와 관련된 메서드, 속성, 패키지 정보를 함께 조회합니다.
-   **쿼리**:
    ```cypher
    MATCH (c:Class)
    OPTIONAL MATCH (c)-[:HAS_METHOD]->(m:Method)
    OPTIONAL MATCH (c)-[:HAS_FIELD]->(p:Field)
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
    ```

-   **설명**: `--inheritance` 옵션. 클래스의 상속(`EXTENDS`) 및 구현(`IMPLEMENTS`) 관계를 조회합니다.
-   **쿼리**:
    ```cypher
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
    ```

-   **설명**: `--package` 옵션. 패키지별로 포함된 클래스, 메서드, 속성의 개수를 집계하여 조회합니다.
-   **쿼리**:
    ```cypher
    MATCH (pkg:Package)-[:CONTAINS]->(c:Class)
    OPTIONAL MATCH (c)-[:HAS_METHOD]->(m:Method)
    OPTIONAL MATCH (c)-[:HAS_FIELD]->(p:Field)
    RETURN
        pkg.name AS package_name,
        pkg.logical_name AS package_logical_name,
        collect(DISTINCT c.name) AS classes,
        count(DISTINCT m) AS total_methods,
        count(DISTINCT p) AS total_properties
    ORDER BY pkg.name
    ```

---

## 2. `src/services/graph_db.py`

데이터베이스와 직접 상호작용하는 서비스로, 노드와 관계를 생성(MERGE), 수정, 삭제하는 대부분의 쿼리가 포함되어 있습니다.

-   **설명**: `_create_project_tx`. 프로젝트 노드가 없으면 생성하고, 있으면 기존 노드를 반환합니다.
-   **쿼리**:
    ```cypher
    MERGE (p:Project {name: $project_name})
    ON CREATE SET p.logical_name = $project_name
    RETURN p
    ```

-   **설명**: `_create_package_tx`. 특정 프로젝트 내에 패키지 노드를 생성하거나 가져오고, 프로젝트와 `HAS_PACKAGE` 관계로 연결합니다.
-   **쿼리**:
    ```cypher
    MERGE (p:Project {name: $project_name})
    MERGE (pkg:Package {name: $package_name, project_name: $project_name})
    ON CREATE SET pkg.logical_name = $package_name
    MERGE (p)-[:HAS_PACKAGE]->(pkg)
    ```

-   **설명**: `_create_class_tx`. 특정 패키지 내에 클래스 노드를 생성/가져오고, 패키지와 `CONTAINS` 관계로 연결합니다.
-   **쿼리**:
    ```cypher
    MATCH (p:Package {name: $package_name})
    MATCH (c:Class {name: $class_name})
    MERGE (p)-[:CONTAINS]->(c)
    ```

-   **설명**: `_create_method_tx`. 클래스에 메서드 노드를 생성/가져오고, `HAS_METHOD` 관계로 연결합니다.
-   **쿼리**:
    ```cypher
    MATCH (c:Class {name: $class_name})
    MERGE (m:Method {name: $method_name, class_name: $class_name})
    MERGE (c)-[:HAS_METHOD]->(m)
    ```

-   **설명**: `_create_method_call_tx`. 두 메서드(호출자, 피호출자) 사이에 `CALLS` 관계를 생성합니다.
-   **쿼리**:
    ```cypher
    MATCH (sm:Method {name: $source_method, class_name: $source_class})
    MATCH (tm:Method {name: $target_method, class_name: $target_class})
    MERGE (sm)-[:CALLS]->(tm)
    ```

-   **설명**: `delete_class_and_related_data`. 특정 클래스와 관련된 모든 하위 노드(메서드, 필드, 빈, 엔드포인트 등) 및 관계를 삭제합니다.
-   **쿼리**:
    ```cypher
    MATCH (m:Method {class_name: $class_name}) DETACH DELETE m
    MATCH (f:Field {class_name: $class_name, project_name: $project_name}) DETACH DELETE f
    MATCH (b:Bean {class_name: $class_name, project_name: $project_name}) DETACH DELETE b
    // ... (기타 관련 노드 삭제 쿼리)
    MATCH (c:Class {name: $class_name, project_name: $project_name}) DETACH DELETE c
    ```

---

## 3. `src/services/db_call_analysis.py`

DB 호출 관계 분석에 사용되는 복잡한 조회 쿼리들이 포함되어 있습니다.

-   **설명**: `analyze_call_chain`. 특정 클래스/메서드에서 시작하여 다른 메서드 호출, SQL문, 그리고 최종적으로 접근하는 테이블/컬럼까지의 전체 호출 경로를 추적합니다.
-   **쿼리**:
    ```cypher
    // 시작 메서드가 주어진 경우
    MATCH (c:Class {name: $class_name})-[:HAS_METHOD]->(m:Method {name: $method_name})
    OPTIONAL MATCH (m)-[:CALLS*0..5]->(target_method:Method)
    // ...
    // 시작 클래스만 주어진 경우
    MATCH (c:Class {name: $class_name})-[:HAS_METHOD]->(m:Method)
    OPTIONAL MATCH (m)-[:CALLS*0..5]->(target_method:Method)
    // ...
    ```

-   **설명**: `generate_crud_table_matrix`. 클래스가 메서드 호출을 통해 SQL문을 실행하고, 해당 SQL문이 특정 테이블에 대해 어떤 CRUD 작업을 수행하는지 분석하여 매트릭스를 생성합니다.
-   **쿼리**:
    ```cypher
    MATCH (c:Class)-[:HAS_METHOD]->(m:Method)
    MATCH (m)-[:CALLS]->(sql:SqlStatement)
    WHERE c.project_name = $project_name
    RETURN c.name AS class_name, c.package_name AS package_name, sql.type AS crud_type, sql.tables AS tables
    ```

---

## 4. `src/services/sequence_diagram_generator.py`

시퀀스 다이어그램 생성에 필요한 데이터를 조회하는 쿼리들입니다.

-   **설명**: `get_available_classes`. 데이터베이스에 존재하는 모든 클래스의 이름, 패키지, 타입을 조회합니다.
-   **쿼리**:
    ```cypher
    MATCH (c:Class)
    OPTIONAL MATCH (pkg:Package)-[:CONTAINS]->(c)
    RETURN c.name as name, pkg.name as package_name, c.type as type
    ORDER BY c.name
    ```

-   **설명**: `get_class_methods`. 특정 클래스에 속한 모든 메서드의 정보를 조회합니다.
-   **쿼리**:
    ```cypher
    MATCH (c:Class {name: $class_name})-[:HAS_METHOD]->(m:Method)
    RETURN m.name as name, m.return_type as return_type, m.logical_name as logical_name
    ORDER BY m.name
    ```

-   **설명**: `generate_sequence_diagram`. 특정 클래스/메서드에서 시작하는 메서드 호출 관계(`CALLS`)를 추적하여 시퀀스 다이어그램을 그리는 데 필요한 데이터를 수집합니다.
-   **쿼리**:
    ```cypher
    // 특정 메서드에 초점을 맞춘 경우
    MATCH (c:Class {name: $class_name})-[:HAS_METHOD]->(m:Method {name: $method_name})
    MATCH (m)-[:CALLS]->(target_method:Method)
    MATCH (target_method)<-[:HAS_METHOD]-(target_class:Class)
    RETURN ...

    // 클래스 전체의 호출 관계를 추적하는 경우 (최대 깊이 제한)
    MATCH (c:Class {{name: $class_name}})-[:HAS_METHOD]->(m:Method)
    MATCH (m)-[r:CALLS*1..{max_depth}]->(target_method:Method)
    MATCH (target_method)<-[:HAS_METHOD]-(target_class:Class)
    RETURN ...
    ```
