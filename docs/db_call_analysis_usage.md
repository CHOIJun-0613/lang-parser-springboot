# 데이터베이스 호출관계 분석 기능 사용법

## 개요

3단계에서 구현된 어플리케이션-데이터베이스 호출관계 시각화 기능의 사용법을 설명합니다.

## 새로운 CLI 명령어들

### 1. `db-call-chain` - 호출 체인 분석

Controller → Service → Repository → SQL → Table/Column 호출 체인을 분석합니다.

```bash
# 전체 프로젝트 호출 체인 분석
python -m src.cli.main db-call-chain --project-name myproject

# 특정 클래스부터 시작하는 호출 체인 분석
python -m src.cli.main db-call-chain --project-name myproject --start-class UserController

# 특정 메서드부터 시작하는 호출 체인 분석
python -m src.cli.main db-call-chain --project-name myproject --start-class UserController --start-method getUserById

# 결과를 파일로 저장
python -m src.cli.main db-call-chain --project-name myproject --output-file call_chain_analysis.json
```

### 2. `crud-analysis` - CRUD 매트릭스 분석

클래스와 테이블 간의 CRUD 작업 매트릭스를 생성합니다.

```bash
# CRUD 매트릭스 생성
python -m src.cli.main crud-analysis --project-name myproject

# 결과를 파일로 저장
python -m src.cli.main crud-analysis --project-name myproject --output-file crud_matrix.json
```

### 3. `db-call-diagram` - 호출 관계 다이어그램 생성

Mermaid 다이어그램으로 호출 관계를 시각화합니다.

```bash
# 전체 프로젝트 다이어그램 생성
python -m src.cli.main db-call-diagram --project-name myproject

# 특정 클래스부터 시작하는 다이어그램 생성
python -m src.cli.main db-call-diagram --project-name myproject --start-class UserController

# 특정 메서드부터 시작하는 다이어그램 생성
python -m src.cli.main db-call-diagram --project-name myproject --start-class UserController --start-method getUserById

# 다이어그램을 이미지로 변환 (mermaid-cli 필요)
python -m src.cli.main db-call-diagram --project-name myproject --output-image diagram.png --image-format png

# 결과를 파일로 저장
python -m src.cli.main db-call-diagram --project-name myproject --output-file call_chain_diagram.md
```

### 4. `table-impact` - 테이블 영향도 분석

특정 테이블 변경 시 영향받는 클래스/메서드를 분석합니다.

```bash
# 특정 테이블의 영향도 분석
python -m src.cli.main table-impact --project-name myproject --table-name users

# 결과를 파일로 저장
python -m src.cli.main table-impact --project-name myproject --table-name users --output-file table_impact_analysis.json
```

### 5. `db-statistics` - 데이터베이스 사용 통계

데이터베이스 사용 통계를 조회합니다.

```bash
# 데이터베이스 사용 통계 조회
python -m src.cli.main db-statistics --project-name myproject

# 결과를 파일로 저장
python -m src.cli.main db-statistics --project-name myproject --output-file db_statistics.json
```

## 주요 기능

### 1. 존재하지 않는 Table/Column 노드 식별

SQL에서 참조하는 테이블이나 컬럼이 실제 데이터베이스에 존재하지 않는 경우, 다음과 같이 표시됩니다:

- **❌ 테이블명** - 존재하지 않는 테이블
- **❌ 컬럼명** - 존재하지 않는 컬럼

다이어그램에서는 적색 점선으로 연결되어 시각적으로 구분됩니다.

### 2. 호출 체인 분석

- Controller → Service → Repository → SQL → Table/Column 전체 호출 체인 추적
- 각 단계별 상세 정보 제공
- 누락된 노드 자동 식별

### 3. CRUD 매트릭스

- 클래스별 테이블 접근 현황
- 테이블별 CRUD 작업 통계
- 가장 활발한 클래스/테이블 식별

### 4. 영향도 분석

- 특정 테이블 변경 시 영향받는 코드 위치
- 고복잡도 SQL 식별
- 영향받는 클래스/메서드 목록

### 5. 시각화

- Mermaid 다이어그램으로 호출 관계 시각화
- 존재하지 않는 노드는 적색 점선으로 표시
- 이미지 변환 지원 (PNG, SVG, PDF)

## 사용 예시

### 1. 전체 프로젝트 분석

```bash
# 1. Java 객체 분석
python -m src.cli.main analyze --java_object --java-source-folder ./src/main/java

# 2. DB 객체 분석
python -m src.cli.main analyze --db_object --db-script-folder ./sql

# 3. 호출 체인 분석
python -m src.cli.main db-call-chain --project-name myproject

# 4. CRUD 매트릭스 생성
python -m src.cli.main crud-analysis --project-name myproject

# 5. 호출 관계 다이어그램 생성
python -m src.cli.main db-call-diagram --project-name myproject --output-image db_call_chain.png
```

### 2. 특정 테이블 영향도 분석

```bash
# users 테이블 변경 시 영향도 분석
python -m src.cli.main table-impact --project-name myproject --table-name users

# 결과를 파일로 저장
python -m src.cli.main table-impact --project-name myproject --table-name users --output-file users_impact.json
```

### 3. 특정 클래스 호출 체인 분석

```bash
# UserController 클래스의 호출 체인 분석
python -m src.cli.main db-call-chain --project-name myproject --start-class UserController

# getUserById 메서드의 호출 체인 분석
python -m src.cli.main db-call-chain --project-name myproject --start-class UserController --start-method getUserById
```

## 출력 파일 형식

### JSON 형식 (분석 결과)

```json
{
  "project_name": "myproject",
  "call_chain": [
    {
      "source_class": "UserController",
      "source_method": "getUserById",
      "target_class": "UserService",
      "target_method": "findById",
      "sql_type": "SELECT",
      "table_name": "users",
      "column_name": "id"
    }
  ],
  "missing_nodes": {
    "missing_tables": ["non_existent_table"],
    "missing_columns": ["non_existent_column"]
  },
  "analysis_summary": {
    "total_calls": 10,
    "unique_classes": 5,
    "unique_methods": 8,
    "unique_sql_statements": 6,
    "unique_tables": 3,
    "unique_columns": 12,
    "missing_tables_count": 1,
    "missing_columns_count": 2
  }
}
```

### Mermaid 다이어그램 형식

```mermaid
graph TD
    UserController["🏢 UserController"]:::class
    UserService["🏢 UserService"]:::class
    Table_users["📊 users"]:::table
    Column_id["📋 id"]:::column
    MissingTable_non_existent["❌ non_existent_table"]:::missingTable
    
    UserController --> UserService
    UserService --> Table_users
    Table_users --> Column_id
    UserService -.-> MissingTable_non_existent
    
    classDef class fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef table fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef column fill:#e8f5e8,stroke:#1b5e20,stroke-width:2px
    classDef missingTable fill:#ffebee,stroke:#c62828,stroke-width:2px,stroke-dasharray: 5 5
    classDef missingColumn fill:#fff3e0,stroke:#ef6c00,stroke-width:2px,stroke-dasharray: 5 5
```

## 주의사항

1. **Neo4j 연결**: 모든 명령어는 Neo4j 데이터베이스에 연결되어야 합니다.
2. **프로젝트 이름**: `--project-name` 옵션은 필수입니다.
3. **mermaid-cli**: 이미지 변환을 위해서는 `npm install -g @mermaid-js/mermaid-cli` 설치가 필요합니다.
4. **데이터 준비**: 분석 전에 `analyze` 명령어로 Java 객체와 DB 객체를 먼저 분석해야 합니다.

## 문제 해결

### 1. "No call chain found" 오류

- Java 객체와 DB 객체가 모두 분석되었는지 확인
- 프로젝트 이름이 올바른지 확인
- Neo4j 데이터베이스에 데이터가 있는지 확인

### 2. "Missing tables/columns" 경고

- SQL에서 참조하는 테이블/컬럼이 실제 DB 스키마에 존재하지 않음
- DB 스키마 파일을 확인하고 누락된 테이블/컬럼을 추가하거나 SQL을 수정

### 3. 다이어그램 생성 오류

- mermaid-cli가 설치되어 있는지 확인
- 출력 파일 경로가 올바른지 확인
- 이미지 형식이 지원되는지 확인 (png, svg, pdf)
