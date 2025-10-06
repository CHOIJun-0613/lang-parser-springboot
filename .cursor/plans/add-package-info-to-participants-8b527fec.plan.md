<!-- 8b527fec-1f5c-4aa5-86b4-34011f0a8cb0 bf01539f-91a6-4028-b855-397a7f6f1e38 -->
# SQL Statement Participant 표기 방식 변경

## 목표
SQL statement participant를 mapper file name과 namespace를 사용하여 더 명확하게 표시

## 현재 상태
```plantuml
participant SQL as "SQL statement" << UserMapper >>
```

## 목표 상태
```plantuml
participant UserMapper.xml << com.carcare.domain.user.mapper.UserMapper >>
```

## 필요 정보

### MyBatisMapper 노드 속성
- `namespace`: 매퍼의 네임스페이스 (예: `com.carcare.domain.user.mapper.UserMapper`)
- `file_path`: 매퍼 파일 경로 (예: `D:\path\to\UserMapper.xml` 또는 `UserMapper.java`)
- `name`: 매퍼 이름 (예: `UserMapper`)

### 추출해야 할 정보
1. **Mapper file name**: `file_path`의 마지막 `/` 또는 `\` 뒤의 문자열 (파일명.확장자)
2. **Mapper namespace**: `namespace` 속성 값

## 구현 방안

### 1. `_fetch_call_chain()` 쿼리 수정
**위치**: 148-219줄

현재 쿼리는 `sql.mapper_name`만 반환하고 있으나, MyBatisMapper 노드의 `namespace`와 `file_path`도 필요합니다.

#### 수정할 UNION 절들:

**UNION 2** (178-186줄): Method → SQL 호출
```cypher
MATCH (mapper_node:MyBatisMapper {name: source_class.name, project_name: $project_name})
MATCH (mapper_node)-[:HAS_SQL_STATEMENT]->(sql:SqlStatement ...)
RETURN ... , sql.mapper_name as mapper_name, mapper_node.namespace as mapper_namespace, mapper_node.file_path as mapper_file_path
```

**UNION 3** (190-195줄): 직접 SQL 호출
```cypher
MATCH (mapper_node:MyBatisMapper {name: $class_name, project_name: $project_name})
MATCH (mapper_node)-[:HAS_SQL_STATEMENT]->(sql:SqlStatement ...)
RETURN ... , sql.mapper_name as mapper_name, mapper_node.namespace as mapper_namespace, mapper_node.file_path as mapper_file_path
```

**UNION 4** (199-208줄): SQL → Table 호출
```cypher
MATCH (mapper_node:MyBatisMapper {name: source_class.name, project_name: $project_name})
MATCH (mapper_node)-[:HAS_SQL_STATEMENT]->(sql:SqlStatement ...)
RETURN ... , sql.mapper_name as mapper_name, mapper_node.namespace as mapper_namespace, mapper_node.file_path as mapper_file_path
```

**UNION 5** (212-218줄): 직접 SQL → Table 호출
```cypher
MATCH (mapper_node:MyBatisMapper {name: $class_name, project_name: $project_name})
MATCH (mapper_node)-[:HAS_SQL_STATEMENT]->(sql:SqlStatement ...)
RETURN ... , sql.mapper_name as mapper_name, mapper_node.namespace as mapper_namespace, mapper_node.file_path as mapper_file_path
```

**UNION 1** (164-174줄): Method → Method 호출 (SQL 아님)
```cypher
RETURN ... , "" as mapper_name, "" as mapper_namespace, "" as mapper_file_path
```

### 2. Mapper 정보 수집 로직 수정
**위치**: 304-322줄

```python
# SQL participant의 mapper 정보 수집
sql_mapper_info = {}

for call in all_calls:
    mapper_name = call.get('mapper_name', '')
    mapper_namespace = call.get('mapper_namespace', '')
    mapper_file_path = call.get('mapper_file_path', '')
    
    # SQL과 관련된 호출에서 mapper 정보 수집
    if (target_class == 'SQL' or source_class == 'SQL') and mapper_file_path:
        # 파일명 추출: 마지막 / 또는 \ 뒤의 문자열
        import os
        file_name = os.path.basename(mapper_file_path)
        
        sql_mapper_info['SQL'] = {
            'file_name': file_name,
            'namespace': mapper_namespace
        }
```

### 3. SQL Participant 렌더링 수정
**위치**: 369-375줄

**Before**:
```python
elif p == 'SQL':
    mapper_name = sql_mapper_names.get('SQL', '')
    if mapper_name:
        diagram_lines.append(f"participant {p} as \"SQL statement\" << {mapper_name} >>")
    else:
        diagram_lines.append(f"participant {p} as \"SQL statement\"")
```

**After**:
```python
elif p == 'SQL':
    mapper_info = sql_mapper_info.get('SQL', {})
    file_name = mapper_info.get('file_name', '')
    namespace = mapper_info.get('namespace', '')
    
    if file_name and namespace:
        diagram_lines.append(f"participant {file_name} << {namespace} >>")
    elif file_name:
        diagram_lines.append(f"participant {file_name}")
    else:
        diagram_lines.append(f"participant SQL as \"SQL statement\"")
```

### 4. Participant 변수명 변경 고려사항

현재 코드는 SQL participant를 항상 `'SQL'`이라는 키로 관리하고 있습니다:
- `table_participants = {p['target_class'] for p in all_calls if p['source_class'] == 'SQL'}`
- `if p == 'SQL':`

파일명으로 변경하면 participant 이름이 동적으로 바뀌므로, 로직을 조정해야 합니다.

**옵션 1**: participant 이름을 'SQL'에서 file_name으로 변경
**옵션 2**: participant alias만 변경하고 내부적으로는 'SQL' 유지

**권장**: 옵션 2 - 내부 로직은 그대로 유지하고 표시만 변경

## 예상 결과

### Before:
```plantuml
participant SQL as "SQL statement" << UserMapper >>
UserMapper -> SQL : findUsersWithPaging
SQL -> users : 🔍 SELECT
```

### After:
```plantuml
participant UserMapper.xml << com.carcare.domain.user.mapper.UserMapper >>
UserMapper -> UserMapper.xml : findUsersWithPaging
UserMapper.xml -> users : 🔍 SELECT
```

## 주의사항
- 여러 mapper가 사용되는 경우: 첫 번째 mapper 정보 사용
- Mapper 정보가 없는 경우: 기존 방식대로 "SQL statement" 표시
- file_path가 null인 경우 처리

### To-dos

- [ ] 모든 UNION 절에 mapper_namespace와 mapper_file_path 추가
- [ ] Mapper 정보 수집 로직을 file_name과 namespace 포함하도록 수정
- [ ] SQL participant 렌더링을 file_name과 namespace 사용하도록 수정