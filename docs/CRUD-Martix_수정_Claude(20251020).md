# CRUD Matrix 오류 수정 보고서

**작성일**: 2025-10-20
**수정자**: Claude Code
**작업 유형**: 버그 수정

## 문제 발생 상황

### 실행 명령어
```bash
python -m csa.cli.main crud-matrix --project-name car-center-devlab
```

### 오류 메시지
```
CRUD Matrix - Class to Table Operations
================================================================================
Package                             Class Name                     Method                    Schema     Table                Operations
---------------------------------------------------------------------------------------------------------------------------------------
Error getting CRUD matrix: 'operations'
2025-10-20 14:20:11.101 [E] : 작업 실패: 'operations'
```

## 문제 원인 분석

### 1. 데이터 구조 불일치
- **반환 데이터**: `csa/services/graph_db/analytics.py`의 `get_crud_matrix()` 메서드가 각 row마다 단일 `operation` 값을 반환
- **기대 데이터**: `csa/cli/commands/crud.py`는 각 row에 집계된 `operations` (복수형) 리스트를 기대

### 2. 집계 로직 누락
- 같은 class-method-table 조합에 대해 여러 CRUD 작업이 있을 경우 이를 집계하지 못함
- 예: `UserRepository.findById`가 `users` 테이블에 대해 여러 SQL을 실행하는 경우, 각 SQL의 operation을 별도 row로 반환
- 결과적으로 중복된 row가 발생하고, operations를 하나로 모으지 못함

### 3. KeyError 발생
```python
# crud.py:89
operations = ", ".join(row["operations"]) if row["operations"] else "None"
```
위 코드에서 `row["operations"]` 키를 찾지 못해 KeyError 발생

## 수정 내용

### 파일 위치
`csa/services/graph_db/analytics.py:10-89`

### 변경 전 로직
```python
def get_crud_matrix(self, project_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return the class-to-table CRUD matrix."""
    # Neo4j 쿼리 실행
    # ...
    matrix_rows: List[Dict[str, Any]] = []
    for row in raw_data:
        # 각 row마다 개별적으로 처리
        matrix_rows.append({
            "class_name": class_name,
            "method_name": method_name,
            "package_name": package_name,
            "table_name": table_name,
            "schema": schema,
            "operation": operation,  # 단수형, 단일 값
            "sql_id": row["sql_id"],
        })
    return matrix_rows
```

### 변경 후 로직
```python
def get_crud_matrix(self, project_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return the class-to-table CRUD matrix."""
    # Neo4j 쿼리 실행
    # ...

    # 중간 데이터를 저장할 dict: key = (class_name, method_name, table_name)
    aggregated_data: Dict[tuple, Dict[str, Any]] = {}

    for row in raw_data:
        class_name = row["class_name"]
        package_name = row["package_name"]
        method_name = row["method_name"]
        operation = row["operation"]

        try:
            tables_json = row["tables_json"]
            if tables_json and tables_json != "[]":
                tables = json.loads(tables_json)
                for table_info in tables:
                    if isinstance(table_info, dict) and "name" in table_info:
                        table_name = table_info["name"]

                        # 집계 키 생성
                        key = (class_name, method_name, table_name)

                        if key not in aggregated_data:
                            # 처음 발견된 조합인 경우, schema 조회
                            schema_query = """
                            MATCH (t:Table {name: $table_name})
                            RETURN t.schema AS schema
                            """
                            schema_result = session.run(schema_query, table_name=table_name)
                            schema_record = schema_result.single()
                            schema = schema_record["schema"] if schema_record else "unknown"

                            aggregated_data[key] = {
                                "class_name": class_name,
                                "method_name": method_name,
                                "package_name": package_name,
                                "table_name": table_name,
                                "schema": schema,
                                "operations": set(),  # set으로 중복 제거
                            }

                        # operation 추가
                        aggregated_data[key]["operations"].add(operation)

        except (json.JSONDecodeError, TypeError):
            continue

    # set을 list로 변환하여 반환
    matrix_rows = [
        {
            **data,
            "operations": sorted(list(data["operations"]))  # 정렬된 리스트로 변환
        }
        for data in aggregated_data.values()
    ]

    return matrix_rows
```

### 주요 변경 사항

1. **집계 딕셔너리 도입**
   - `aggregated_data: Dict[tuple, Dict[str, Any]] = {}`
   - Key: `(class_name, method_name, table_name)` 조합
   - Value: 해당 조합의 모든 정보와 operations set

2. **operations를 set으로 수집**
   - 중복된 operation을 자동으로 제거
   - 예: 같은 메서드에서 SELECT를 여러 번 실행해도 'R'은 한 번만 기록

3. **최종 반환 시 list로 변환**
   - set을 정렬된 list로 변환: `sorted(list(data["operations"]))`
   - CLI 코드에서 기대하는 형식으로 반환

4. **Schema 조회 최적화**
   - 각 class-method-table 조합당 한 번만 schema 조회
   - 불필요한 중복 쿼리 제거

## 테스트 결과

### 실행 성공
```bash
python -m csa.cli.main crud-matrix --project-name car-center-devlab
```

### 출력 결과 (일부)
```
CRUD Matrix - Class to Table Operations
================================================================================
Package                             Class Name                     Method                    Schema     Table                Operations
---------------------------------------------------------------------------------------------------------------------------------------
com.carcare.domain.notification.repository NotificationRepository         countUnreadByUserId       public     notifications        R
com.carcare.domain.notification.repository NotificationRepository         deleteById                public     notifications        D
com.carcare.domain.notification.repository NotificationRepository         deleteOldNotifications    public     notifications        D
com.carcare.domain.notification.repository NotificationRepository         findById                  public     notifications        R
...
com.carcare.domain.payment.repository PaymentRepository              countBySearchCriteria     public     payments             R
com.carcare.domain.payment.repository PaymentRepository              countBySearchCriteria     public     reservations         R
com.carcare.domain.payment.repository PaymentRepository              save                      public     payments             C
com.carcare.domain.payment.repository PaymentRepository              update                    public     payments             U
...
```

### 통계
- **Total**: 211 class-table relationships
- **출력 형식**: Markdown, Excel 파일 정상 생성
- **Operations 표시**: C (Create), R (Read), U (Update), D (Delete) 정상 표시

### 파일 생성 확인
```
CRUD matrix (Markdown) saved to: ./output/crud-matrix/CRUD_car-center-devlab_20251020-HHMMSS.md
CRUD matrix (Excel) saved to: ./output/crud-matrix/CRUD_car-center-devlab_20251020-HHMMSS.xlsx
```

## 영향 범위

### 수정된 파일
- `csa/services/graph_db/analytics.py`

### 영향받는 기능
- `crud-matrix` 명령어
- `crud-analysis` 명령어
- CRUD 매트릭스를 사용하는 모든 기능

### 하위 호환성
- ✅ 기존 CLI 인터페이스 유지
- ✅ 반환 데이터 구조 개선 (operations 필드 추가)
- ✅ 기존 호출 코드 수정 불필요

## 추가 개선 사항

### 성능 최적화
- Schema 조회를 집계 시점에 수행하여 중복 쿼리 감소
- 같은 테이블에 대해 한 번만 schema 조회

### 데이터 품질 향상
- 중복 row 제거로 출력 간결화
- operations 집계로 각 메서드가 수행하는 모든 CRUD 작업 한눈에 파악 가능

### 예시
**변경 전**:
```
UserRepository  findById  users  R
UserRepository  findById  users  R  (중복)
```

**변경 후**:
```
UserRepository  findById  users  R
```

## 출력 형식 개선 (2차 수정)

### 개선 요구사항

1. **Excel 파일**: 데이터 상단에 Title, 작성일시, 통계 추가
2. **Markdown 파일**: 통계 위치를 데이터 하단에서 상단으로 이동

### Excel 파일 개선

**파일 위치**: `csa/cli/core/storage.py:82-148`

**주요 변경사항**:
```python
# 데이터를 startrow=4부터 작성하여 상단 3행에 헤더 정보 추가
df.to_excel(writer, sheet_name="CRUD Matrix", index=False, startrow=4)

# Title 추가 (A1) - 크고 굵은 글씨
worksheet["A1"] = f"CRUD Matrix [Project : {project_name}]"
worksheet["A1"].font = Font(bold=True, size=14)

# 작성일시 추가 (A2)
worksheet["A2"] = f"Generated at: {generated_at}"
worksheet["A2"].font = Font(size=11)

# 통계 추가 (A3)
worksheet["A3"] = f"Total: {total_count} class-table relationships"
worksheet["A3"].font = Font(size=11)

# 헤더 행 스타일 적용 (5행)
for cell in worksheet[5]:
    cell.font = Font(bold=True, color="FFFFFF")
    cell.fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
```

**결과 예시**:
```
Row 1: CRUD Matrix [Project : car-center-devlab]       (크고 굵은 글씨)
Row 2: Generated at: 2025-10-20 14:43:43
Row 3: Total: 253 class-table relationships
Row 4: (빈 줄)
Row 5: Package | Class Name | Method | Schema | Table | Operations  (헤더)
Row 6~: (데이터)
```

### Markdown 파일 개선

**파일 위치**: `csa/cli/commands/crud.py:103-123`

**주요 변경사항**:
```python
lines = [
    f"# CRUD Matrix [Project : {project_name}]",
    "",
    f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    "",
    f"**Total:** {len(matrix)} class-table relationships.",  # 상단으로 이동
    "",
    "| Package | Class Name | Method | Schema | Table | Operations |",
    "|---------|------------|--------|--------|-------|------------|",
]
# 하단의 Total 통계 줄 제거
```

**결과 예시**:
```markdown
# CRUD Matrix [Project : car-center-devlab]

Generated at: 2025-10-20 14:43:43

**Total:** 253 class-table relationships.

| Package | Class Name | Method | Schema | Table | Operations |
|---------|------------|--------|--------|-------|------------|
| com.carcare.domain... | NotificationRepository | countUnreadByUserId | public | notifications | R |
...
```

### 수정된 파일 목록

1. `csa/cli/core/storage.py` - Excel 파일 생성 로직
2. `csa/cli/commands/crud.py` - Markdown 파일 생성 로직

### 검증 결과

**테스트 실행**:
```bash
python -m csa.cli.main crud-matrix --project-name car-center-devlab
```

**생성된 파일**:
- `CRUD_car-center-devlab_20251020-144343.xlsx` (12,652 bytes)
- `CRUD_car-center-devlab_20251020-144343.md` (28,888 bytes)

**Excel 파일 검증**:
```python
Row 1: ['CRUD Matrix [Project : car-center-devlab]', '', '']
Row 2: ['Generated at: 2025-10-20 14:43:43', '', '']
Row 3: ['Total: 253 class-table relationships', '', '']
Row 4: ['', '', '']
Row 5: ['Package', 'Class Name', 'Method']
Row 6~: [데이터 행들...]
```

**Markdown 파일 검증**:
```markdown
# CRUD Matrix [Project : car-center-devlab]

Generated at: 2025-10-20 14:43:43

**Total:** 253 class-table relationships.

| Package | Class Name | Method | Schema | Table | Operations |
|---------|------------|--------|--------|-------|------------|
...
```

## 결론

### 1차 수정 (버그 수정)
`get_crud_matrix()` 메서드의 집계 로직 추가로:
- ✅ KeyError 'operations' 오류 해결
- ✅ 중복 데이터 제거
- ✅ operations 집계 기능 추가
- ✅ 성능 개선 (중복 쿼리 감소)

### 2차 수정 (출력 형식 개선)
Excel 및 Markdown 파일 형식 개선으로:
- ✅ Excel: Title, 작성일시, 통계 정보가 데이터 상단에 표시
- ✅ Markdown: 통계 정보가 작성일시 바로 아래에 위치
- ✅ 가독성 향상 및 사용자 편의성 개선
- ✅ 일관된 파일 구조 제공

이제 `crud-matrix` 명령어가 정상적으로 작동하며, 모든 Repository의 CRUD 작업을 정확하고 보기 좋은 형식으로 표시합니다.
