# Mapper Class Method와 SqlStatement 관계 설정 수정 (2025-10-22)

## 1. 문제 상황

### 1-1. 증상
- `Method -[:CALLS]-> SqlStatement` 관계가 Neo4j에 생성되지 않음
- 시퀀스 다이어그램 생성 시 Mapper 클래스 메서드에서 SQL 호출이 누락됨

### 1-2. 확인 결과
```cypher
// Method -> SqlStatement CALLS 관계 개수 확인
MATCH (m:Method)-[r:CALLS]->(s:SqlStatement)
RETURN count(r) as calls_count

// 결과: 0
```

```cypher
// Class -> Method -> SqlStatement 체인 확인
MATCH (c:Class {project_name: 'car-center-devlab'})
MATCH (c)-[:HAS_METHOD]->(m:Method)
MATCH (m)-[:CALLS]->(s:SqlStatement)
RETURN c.name as class_name,
       m.name as method_name,
       s.id as sql_id,
       s.sql_type as sql_type
LIMIT 20

// 결과: No changes, no records
```

### 1-3. 영향 범위
- 시퀀스 다이어그램에서 Repository/Mapper → SQL → Table 호출 체인이 표시되지 않음
- DB 호출 관계 분석 기능이 정상 작동하지 않음
- CRUD 매트릭스 생성 시 메서드-SQL 매핑이 누락됨

---

## 2. 문제 원인 분석

### 2-1. Neo4j 관계 구조

**정상적인 관계 구조:**
```
Class -[:HAS_METHOD]-> Method -[:CALLS]-> SqlStatement
                                            ↑
                                [:HAS_SQL_STATEMENT]
                                            |
                                     MyBatisMapper
```

### 2-2. 관계 생성 로직

**MyBatisMapper -[:HAS_SQL_STATEMENT]-> SqlStatement 관계:**
- **생성 위치**: `csa/services/analysis/neo4j_writer.py:196-209`
- **생성 시점**: `analyze` 명령어 실행 시 SqlStatement 저장 직후
- **상태**: ✅ 정상 생성됨

**Method -[:CALLS]-> SqlStatement 관계:**
- **생성 위치**: `csa/services/graph_db/persistence_nodes.py:214-231`
- **생성 함수**: `create_method_sql_relationships()`
- **호출 위치**: `db_calls`, `crud` 명령어에서만 호출
- **상태**: ❌ `analyze` 명령어에서 호출되지 않음

### 2-3. 근본 원인

**`analyze` 명령어 실행 시 `create_method_sql_relationships()` 함수가 호출되지 않아** Method와 SqlStatement 간의 CALLS 관계가 생성되지 않음.

**관계 생성 함수 (`csa/services/graph_db/persistence_nodes.py:218-231`):**
```python
@staticmethod
def _create_method_sql_relationships_tx(tx, project_name: str) -> int:
    relationship_query = """
    MATCH (c:Class {project_name: $project_name})
    WHERE c.name ENDS WITH 'Repository' OR c.name ENDS WITH 'Mapper'
    MATCH (c)-[:HAS_METHOD]->(m:Method)
    MATCH (s:SqlStatement {project_name: $project_name})
    WHERE s.mapper_name = c.name
      AND s.id = m.name
    MERGE (m)-[:CALLS]->(s)
    RETURN count(*) as relationships_created
    """
    result = tx.run(relationship_query, project_name=project_name)
    return result.single()["relationships_created"]
```

**매칭 조건:**
1. 클래스명이 `Repository` 또는 `Mapper`로 끝남
2. `SqlStatement.mapper_name == Class.name`
3. `SqlStatement.id == Method.name`

---

## 3. 해결 방법

### 3-1. 즉시 해결 (수동 관계 생성)

Neo4j Browser에서 다음 Cypher 쿼리를 실행하여 관계를 수동으로 생성:

```cypher
// Method -> SqlStatement CALLS 관계 생성
MATCH (c:Class {project_name: 'car-center-devlab'})
WHERE c.name ENDS WITH 'Repository' OR c.name ENDS WITH 'Mapper'
MATCH (c)-[:HAS_METHOD]->(m:Method)
MATCH (s:SqlStatement {project_name: 'car-center-devlab'})
WHERE s.mapper_name = c.name
  AND s.id = m.name
MERGE (m)-[:CALLS]->(s)
RETURN count(*) as relationships_created
```

### 3-2. 근본 해결 (코드 수정)

**환경**: 스트리밍 모드(`USE_STREAMING_PARSE=true`) 및 배치 모드 모두 지원

#### 3-2-1. 스트리밍 모드 수정

**파일**: `csa/services/analysis/java_pipeline.py`

**수정 위치**: `_analyze_with_streaming()` 함수 내, 스트리밍 파싱 완료 후

**수정 내용**:

```python
logger.info("Streaming parsing complete:")
logger.info("  - Packages: %s", stats['packages'])
logger.info("  - Classes: %s", stats['classes'])
logger.info("  - Beans: %s", stats['beans'])
logger.info("  - Endpoints: %s", stats['endpoints'])

# Method -> SqlStatement CALLS 관계 생성 (스트리밍 모드) (추가)
if stats.get('sql_statements', 0) > 0:
    logger.info("")
    logger.info("Creating Method -> SqlStatement CALLS relationships...")
    relationships_created = graph_db.create_method_sql_relationships(final_project_name)
    logger.info("Created %s Method -> SqlStatement relationships", relationships_created)

# JavaAnalysisArtifacts 생성 (빈 리스트로, 실제 데이터는 Neo4j에 있음)
artifacts = JavaAnalysisArtifacts(
```

#### 3-2-2. 배치 모드 수정

**파일**: `csa/services/analysis/neo4j_writer.py`

**수정 위치**: `save_java_objects_to_neo4j()` 함수 내, Bean 의존성 해결 로직 다음

**수정 내용**:

```python
# Bean 의존성 해결 (Neo4j 기반)
# artifacts.beans가 Neo4j에 저장된 후 실행
if artifacts.beans:
    logger.info("")
    from csa.services.java_analysis.bean_dependency_resolver import (
        resolve_bean_dependencies_from_neo4j
    )
    resolve_bean_dependencies_from_neo4j(db, project_name, logger)

# Method -> SqlStatement CALLS 관계 생성 (추가)
# artifacts.sql_statements가 Neo4j에 저장된 후 실행
if artifacts.sql_statements:
    logger.info("")
    logger.info("Creating Method -> SqlStatement CALLS relationships...")
    relationships_created = db.create_method_sql_relationships(project_name)
    logger.info("Created %s Method -> SqlStatement relationships", relationships_created)

java_end_time = datetime.now()
```

**수정 파일 전체 경로**: `D:\workspaces\lang-parser-work\lang-parser-springboot\csa\services\analysis\neo4j_writer.py:611-617`

---

## 4. 코드 수정 상세

### 4-1. 스트리밍 모드 수정 상세

#### 4-1-1. 수정 전 (Before)

```python
    logger.info("Streaming parsing complete:")
    logger.info("  - Packages: %s", stats['packages'])
    logger.info("  - Classes: %s", stats['classes'])
    logger.info("  - Beans: %s", stats['beans'])
    logger.info("  - Endpoints: %s", stats['endpoints'])

    # JavaAnalysisArtifacts 생성 (빈 리스트로, 실제 데이터는 Neo4j에 있음)
    artifacts = JavaAnalysisArtifacts(
```

#### 4-1-2. 수정 후 (After)

```python
    logger.info("Streaming parsing complete:")
    logger.info("  - Packages: %s", stats['packages'])
    logger.info("  - Classes: %s", stats['classes'])
    logger.info("  - Beans: %s", stats['beans'])
    logger.info("  - Endpoints: %s", stats['endpoints'])

    # Method -> SqlStatement CALLS 관계 생성 (스트리밍 모드)
    if stats.get('sql_statements', 0) > 0:
        logger.info("")
        logger.info("Creating Method -> SqlStatement CALLS relationships...")
        relationships_created = graph_db.create_method_sql_relationships(final_project_name)
        logger.info("Created %s Method -> SqlStatement relationships", relationships_created)

    # JavaAnalysisArtifacts 생성 (빈 리스트로, 실제 데이터는 Neo4j에 있음)
    artifacts = JavaAnalysisArtifacts(
```

#### 4-1-3. 수정 로직 설명 (스트리밍 모드)

1. **실행 조건**: `stats['sql_statements'] > 0` (Neo4j에 SqlStatement가 1개 이상 저장된 경우)
2. **실행 시점**: 스트리밍 파싱 완료 직후, artifacts 생성 전
3. **수행 작업**:
   - `graph_db.create_method_sql_relationships(final_project_name)` 호출
   - Repository/Mapper 클래스의 메서드와 동일한 ID를 가진 SqlStatement를 매칭
   - Method -[:CALLS]-> SqlStatement 관계 생성
4. **결과 로깅**: 생성된 관계 개수를 INFO 레벨로 로그 출력

**파일 경로**: `csa/services/analysis/java_pipeline.py:101-106`

### 4-2. 배치 모드 수정 상세

#### 4-2-1. 수정 전 (Before)

```python
    # Bean 의존성 해결 (Neo4j 기반)
    # artifacts.beans가 Neo4j에 저장된 후 실행
    if artifacts.beans:
        logger.info("")
        from csa.services.java_analysis.bean_dependency_resolver import (
            resolve_bean_dependencies_from_neo4j
        )
        resolve_bean_dependencies_from_neo4j(db, project_name, logger)

    java_end_time = datetime.now()
    java_stats.start_time = java_start_time
    java_stats.end_time = java_end_time
    logger.info("Java object analysis completed in %s", format_duration((java_end_time - java_start_time).total_seconds()))
```

#### 4-2-2. 수정 후 (After)

```python
    # Bean 의존성 해결 (Neo4j 기반)
    # artifacts.beans가 Neo4j에 저장된 후 실행
    if artifacts.beans:
        logger.info("")
        from csa.services.java_analysis.bean_dependency_resolver import (
            resolve_bean_dependencies_from_neo4j
        )
        resolve_bean_dependencies_from_neo4j(db, project_name, logger)

    # Method -> SqlStatement CALLS 관계 생성
    # artifacts.sql_statements가 Neo4j에 저장된 후 실행
    if artifacts.sql_statements:
        logger.info("")
        logger.info("Creating Method -> SqlStatement CALLS relationships...")
        relationships_created = db.create_method_sql_relationships(project_name)
        logger.info("Created %s Method -> SqlStatement relationships", relationships_created)

    java_end_time = datetime.now()
    java_stats.start_time = java_start_time
    java_stats.end_time = java_end_time
    logger.info("Java object analysis completed in %s", format_duration((java_end_time - java_start_time).total_seconds()))
```

#### 4-2-3. 수정 로직 설명 (배치 모드)

1. **실행 조건**: `artifacts.sql_statements`가 존재하는 경우
2. **실행 시점**: SqlStatement 노드와 MyBatisMapper 노드가 Neo4j에 저장된 후
3. **수행 작업**:
   - `db.create_method_sql_relationships(project_name)` 호출
   - Repository/Mapper 클래스의 메서드와 동일한 ID를 가진 SqlStatement를 매칭
   - Method -[:CALLS]-> SqlStatement 관계 생성
4. **결과 로깅**: 생성된 관계 개수를 INFO 레벨로 로그 출력

---

## 5. 검증 방법

### 5-1. 재분석 실행

```bash
# 전체 재분석 (clean 모드)
python -m csa.cli.main analyze --all-objects --clean --project-name car-center-devlab
```

**예상 로그 출력**:
```
INFO: Creating Method -> SqlStatement CALLS relationships...
INFO: Created 45 Method -> SqlStatement relationships
```

### 5-2. Neo4j 관계 확인

#### (1) Method -> SqlStatement 관계 개수
```cypher
MATCH (m:Method)-[r:CALLS]->(s:SqlStatement)
RETURN count(r) as calls_count
```
**기대 결과**: 0보다 큰 값

#### (2) 전체 호출 체인 확인
```cypher
MATCH (c:Class {project_name: 'car-center-devlab'})
WHERE c.name ENDS WITH 'Mapper' OR c.name ENDS WITH 'Repository'
MATCH (c)-[:HAS_METHOD]->(m:Method)
MATCH (m)-[:CALLS]->(s:SqlStatement)
RETURN c.name as class_name,
       m.name as method_name,
       s.id as sql_id,
       s.sql_type as sql_type
LIMIT 20
```
**기대 결과**: Mapper/Repository 클래스의 메서드와 SQL 매핑 결과 반환

#### (3) 특정 Mapper 클래스 확인
```cypher
MATCH (c:Class {name: 'UserMapper', project_name: 'car-center-devlab'})
MATCH (c)-[:HAS_METHOD]->(m:Method)
OPTIONAL MATCH (m)-[:CALLS]->(s:SqlStatement)
RETURN c.name as class_name,
       m.name as method_name,
       s.id as sql_id,
       s.sql_type as sql_type,
       CASE WHEN s IS NULL THEN 'No SQL' ELSE 'Has SQL' END as status
```

#### (4) 관계 시각화
```cypher
// Class -> Method -> SqlStatement 경로 시각화
MATCH path = (c:Class)-[:HAS_METHOD]->(m:Method)-[:CALLS]->(s:SqlStatement)
WHERE c.project_name = 'car-center-devlab'
RETURN path
LIMIT 10
```

### 5-3. 시퀀스 다이어그램 생성 테스트

```bash
# Repository/Mapper 클래스의 시퀀스 다이어그램 생성
python -m csa.cli.main sequence --class-name UserMapper --project-name car-center-devlab

# 특정 메서드의 시퀀스 다이어그램 생성
python -m csa.cli.main sequence --class-name UserMapper --method-name selectUserById --project-name car-center-devlab
```

**기대 결과**: Method → SQL → Table 호출 체인이 다이어그램에 표시됨

### 5-4. CRUD 매트릭스 생성 테스트

```bash
# CRUD 매트릭스 생성
python -m csa.cli.main crud-matrix --project-name car-center-devlab --output-format excel
```

**기대 결과**:
- Method별 SQL 호출 정보가 정상 표시됨
- Table별 CRUD 작업 매핑이 정확함

---

## 6. Neo4j 관계 구조 상세

### 6-1. 전체 관계도

```
Project
  ↓ [:HAS_PACKAGE]
Package
  ↓ [:BELONGS_TO]
Class
  ↓ [:HAS_METHOD]
Method
  ↓ [:CALLS] (이번에 수정한 부분)
SqlStatement ←[:HAS_SQL_STATEMENT]─ MyBatisMapper (Interface/XML)
  ↓ (속성: tables)
Table
  ↓ [:HAS_COLUMN]
Column
```

### 6-2. Mapper 관련 노드 관계

#### MyBatis Interface Mapper (Java 클래스)
```
Class (type=interface, @Mapper)
  ↓ [:HAS_METHOD]
Method
  ↓ [:CALLS]
SqlStatement (sql_content from @Select/@Insert/@Update/@Delete)

동시에:
MyBatisMapper (type=interface, name=Class.name)
  ↓ [:HAS_SQL_STATEMENT]
SqlStatement (동일한 SqlStatement 노드)
```

#### MyBatis XML Mapper
```
MyBatisMapper (type=xml, name=namespace.SimpleName)
  ↓ [:HAS_SQL_STATEMENT]
SqlStatement (id=<select>/<insert>/<update>/<delete> 태그의 id)

동시에:
Class (Mapper Interface)
  ↓ [:HAS_METHOD]
Method (name=SqlStatement.id)
  ↓ [:CALLS]
SqlStatement (동일한 SqlStatement 노드)
```

### 6-3. 관계 생성 순서

#### analyze 명령어 실행 시:

1. **Package 노드 생성**
   - Package 정보 저장

2. **Class/Method/Field 노드 생성**
   - Java 클래스 파싱 결과 저장
   - Class -[:HAS_METHOD]-> Method 관계 생성

3. **MyBatisMapper 노드 생성**
   - Interface Mapper 추출 (from Classes)
   - XML Mapper 추출 (from XML files)

4. **SqlStatement 노드 생성**
   - MyBatis Mapper의 SQL 정보 추출
   - SqlStatement 노드 생성

5. **MyBatisMapper -[:HAS_SQL_STATEMENT]-> SqlStatement 관계 생성**
   - Mapper가 SQL을 "소유"하는 관계
   - `neo4j_writer.py:196-209`에서 생성

6. **Bean 의존성 관계 생성**
   - Bean -[:INJECTS]-> Bean 관계 생성
   - Constructor/Field/Setter Injection 추적

7. **Method -[:CALLS]-> SqlStatement 관계 생성** ← 이번에 추가
   - 메서드가 SQL을 "호출"하는 관계
   - `neo4j_writer.py:611-617`에서 생성 (수정 후)

---

## 7. 관련 파일 목록

### 7-1. 수정된 파일
- `csa/services/analysis/java_pipeline.py` (101-106행 추가) - 스트리밍 모드
- `csa/services/analysis/neo4j_writer.py` (611-617행 추가) - 배치 모드

### 7-2. 관련 파일
- `csa/services/graph_db/persistence_nodes.py` (214-231행)
  - `create_method_sql_relationships()` 메서드 정의
  - `_create_method_sql_relationships_tx()` 트랜잭션 함수 정의
- `csa/diagrams/sequence/repository.py` (103-121행)
  - 시퀀스 다이어그램 생성 시 Method -> SqlStatement 관계 조회

### 7-3. 기존 호출 위치
- `csa/cli/commands/db_calls.py` (51, 157, 287행)
- `csa/cli/commands/crud.py` (64, 200, 270, 352, 444행)

---

## 8. 주의사항

### 8-1. 관계 생성 조건

Method -[:CALLS]-> SqlStatement 관계는 다음 조건을 모두 만족해야 생성됩니다:

1. **클래스명 조건**:
   - `Class.name`이 `Repository` 또는 `Mapper`로 끝나야 함
   - 예: `UserMapper`, `UserRepository` (O)
   - 예: `UserService`, `UserController` (X)

2. **매핑 조건**:
   - `SqlStatement.mapper_name == Class.name`
   - `SqlStatement.id == Method.name`

3. **프로젝트 조건**:
   - `Class.project_name == SqlStatement.project_name == {지정한 project_name}`

### 8-2. 관계가 생성되지 않는 경우

#### Case 1: 클래스명이 Repository/Mapper로 끝나지 않음
```cypher
// 진단 쿼리
MATCH (c:Class {project_name: 'car-center-devlab'})
WHERE NOT (c.name ENDS WITH 'Repository' OR c.name ENDS WITH 'Mapper')
MATCH (c)-[:HAS_METHOD]->(m:Method)
RETURN c.name as class_name, count(m) as method_count
ORDER BY method_count DESC
```

#### Case 2: SqlStatement.mapper_name과 Class.name 불일치
```cypher
// 진단 쿼리
MATCH (s:SqlStatement {project_name: 'car-center-devlab'})
OPTIONAL MATCH (c:Class {name: s.mapper_name, project_name: 'car-center-devlab'})
WHERE c IS NULL
RETURN s.mapper_name as mapper_name, s.id as sql_id, 'Class Not Found' as issue
```

#### Case 3: SqlStatement.id와 Method.name 불일치
```cypher
// 진단 쿼리
MATCH (s:SqlStatement {project_name: 'car-center-devlab'})
MATCH (c:Class {name: s.mapper_name, project_name: 'car-center-devlab'})
OPTIONAL MATCH (c)-[:HAS_METHOD]->(m:Method {name: s.id})
WHERE m IS NULL
RETURN c.name as class_name, s.id as sql_id, 'Method Not Found' as issue
```

### 8-3. 성능 고려사항

- 프로젝트 규모가 큰 경우 관계 생성에 시간이 소요될 수 있음
- 예상 시간: 100개 SQL당 약 1-2초
- 로그에서 진행 상황 확인 가능:
  ```
  INFO: Creating Method -> SqlStatement CALLS relationships...
  INFO: Created 45 Method -> SqlStatement relationships
  ```

---

## 9. 향후 개선 사항

### 9-1. 배치 처리 최적화
현재는 MERGE를 사용하여 관계를 하나씩 생성하지만, UNWIND를 사용한 배치 처리로 성능 개선 가능:

```python
@staticmethod
def _create_method_sql_relationships_batch_tx(tx, project_name: str) -> int:
    relationship_query = """
    MATCH (c:Class {project_name: $project_name})
    WHERE c.name ENDS WITH 'Repository' OR c.name ENDS WITH 'Mapper'
    MATCH (c)-[:HAS_METHOD]->(m:Method)
    WITH c, m
    MATCH (s:SqlStatement {project_name: $project_name})
    WHERE s.mapper_name = c.name AND s.id = m.name
    WITH collect({method: m, sql: s}) as pairs
    UNWIND pairs as pair
    MERGE (pair.method)-[:CALLS]->(pair.sql)
    RETURN count(*) as relationships_created
    """
    result = tx.run(relationship_query, project_name=project_name)
    return result.single()["relationships_created"]
```

### 9-2. JPA Repository 지원
현재는 MyBatis Mapper만 지원하지만, JPA Repository의 메서드도 유사하게 처리 가능:

```python
# JPA Repository 메서드 -> JpaQuery 관계 생성
MATCH (c:Class {project_name: $project_name})
WHERE c.name ENDS WITH 'Repository'
MATCH (c)-[:HAS_METHOD]->(m:Method)
MATCH (q:JpaQuery {project_name: $project_name, repository_name: c.name})
WHERE q.method_name = m.name
MERGE (m)-[:EXECUTES]->(q)
```

### 9-3. 로깅 개선
관계 생성 실패 케이스를 별도로 로깅하여 디버깅 지원:

```python
# Method는 있지만 SQL이 없는 경우
logger.warning("Method %s.%s has no matching SQL statement", class_name, method_name)

# SQL은 있지만 Method가 없는 경우
logger.warning("SqlStatement %s (mapper=%s) has no matching method", sql_id, mapper_name)
```

---

## 10. 참고 자료

### 10-1. 관련 문서
- `CLAUDE.md` - 프로젝트 아키텍처 및 데이터 플로우
- `docs/db호출관계분석-3단계-1(250927).md` - DB 호출 관계 분석 설계 문서

### 10-2. 관련 Cypher 쿼리 모음
- `docs/관계확인 Cypher query(20251022).md` - 관계 검증용 Cypher 쿼리 모음

### 10-3. 테스트 프로젝트
- `target_src/car-center-devlab/` - 분석 대상 샘플 프로젝트

---

## 11. 변경 이력

| 날짜 | 버전 | 작성자 | 변경 내용 |
|------|------|--------|-----------|
| 2025-10-22 | 1.0 | Claude | 초안 작성 - Method -> SqlStatement CALLS 관계 자동 생성 기능 추가 (배치 모드) |
| 2025-10-22 | 1.1 | Claude | 스트리밍 모드 지원 추가 - java_pipeline.py 수정 |

---

## 12. 요약

### 문제
- `analyze` 명령어 실행 시 Method -> SqlStatement CALLS 관계가 생성되지 않음
- 시퀀스 다이어그램 및 DB 호출 관계 분석 기능 오작동

### 원인
- **배치 모드**: `save_java_objects_to_neo4j()` 함수에서 `create_method_sql_relationships()` 호출 누락
- **스트리밍 모드**: `_analyze_with_streaming()` 함수에서 `create_method_sql_relationships()` 호출 누락
- 두 모드 모두 analyze 명령어 실행 시 관계 생성 로직이 없었음

### 해결
- **스트리밍 모드**: `csa/services/analysis/java_pipeline.py:101-106`에 관계 생성 로직 추가
- **배치 모드**: `csa/services/analysis/neo4j_writer.py:611-617`에 관계 생성 로직 추가
- SqlStatement 저장 완료 후 자동으로 Method -[:CALLS]-> SqlStatement 관계 생성

### 효과
- `analyze` 명령어 1회 실행으로 모든 관계가 자동 생성됨 (스트리밍/배치 모두)
- 시퀀스 다이어그램, CRUD 매트릭스, DB 호출 관계 분석 기능 정상 작동
- 사용자가 수동으로 `db_calls`, `crud` 명령어를 실행할 필요 없음

### 중요 참고사항
- 기본값이 **스트리밍 모드**(`USE_STREAMING_PARSE=true`)이므로 대부분의 경우 `java_pipeline.py` 수정이 적용됨
- 배치 모드를 사용하는 경우(`USE_STREAMING_PARSE=false`) `neo4j_writer.py` 수정이 적용됨
