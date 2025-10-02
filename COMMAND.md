# CLI 명령어 가이드

이 문서는 `src/cli/main.py`를 통해 사용할 수 있는 명령어와 옵션을 설명합니다.

## 기본 사용법

```bash
python -m src.cli.main [COMMAND] [OPTIONS]
```

---

## 1. `analyze`

Java 프로젝트 및/또는 데이터베이스 DDL 스크립트를 분석하여 Neo4j 데이터베이스에 정보를 저장합니다.

### 실행 예시

```bash
# DB 객체만 분석
python -m src.cli.main analyze --db_object

# Java 객체만 분석
python -m src.cli.main analyze --java_object

# DB와 Java 객체 모두 분석
python -m src.cli.main analyze --all_objects

# 특정 클래스만 분석 (기존 데이터 삭제 후 재분석)
python -m src.cli.main analyze --class-name MyClassName

# 모든 클래스를 개별적으로 업데이트 (전체 삭제 없음)
python -m src.cli.main analyze --update

# DB 연결 없이 파싱만 테스트 (Dry Run)
python -m src.cli.main analyze --java_object --dry-run
```

### 옵션

| 옵션 | 설명 | 기본값/필수 |
| --- | --- | --- |
| `--java-source-folder` | 분석할 Java 소스 프로젝트 폴더의 경로입니다. | `.env` 파일의 `JAVA_SOURCE_FOLDER` 값 |
| `--neo4j-uri` | Neo4j 데이터베이스의 URI입니다. | `bolt://localhost:7687` |
| `--neo4j-user` | Neo4j 사용자 이름입니다. | `neo4j` |
| `--neo4j-password` | Neo4j 비밀번호입니다. | `.env` 파일의 `NEO4J_PASSWORD` 값 |
| `--clean` | 분석을 시작하기 전에 데이터베이스를 초기화합니다. | Flag |
| `--class-name` | 특정 클래스만 분석합니다. (해당 클래스의 기존 데이터는 삭제됩니다) | |
| `--update` | 데이터베이스를 비우지 않고 모든 클래스를 개별적으로 업데이트합니다. | Flag |
| `--db_object` | DDL 스크립트로부터 데이터베이스 객체를 분석합니다. (`DB_SCRIPT_FOLDER` 환경 변수 필요) | Flag |
| `--java_object` | 소스 코드로부터 Java 객체를 분석합니다. (`JAVA_SOURCE_FOLDER` 환경 변수 필요) | Flag |
| `--all_objects` | Java 객체와 데이터베이스 객체를 모두 분석합니다. (`--java_object --db_object`와 동일) | Flag |
| `--dry-run` | 데이터베이스에 연결하지 않고 파싱만 수행하여 결과를 미리 봅니다. | Flag |

---

## 2. `query`

미리 정의된 또는 사용자 정의 Cypher 쿼리를 데이터베이스에 실행하여 결과를 확인합니다.

### 실행 예시

```bash
# 기본 클래스 정보 조회
python -m src.cli.main query --basic

# 상속 관계 조회
python -m src.cli.main query --inheritance

# 사용자 정의 쿼리 실행
python -m src.cli.main query --query "MATCH (n:Class) RETURN n.name"
```

### 옵션

| 옵션 | 설명 | 기본값/필수 |
| --- | --- | --- |
| `--neo4j-uri` | Neo4j 데이터베이스의 URI입니다. | `bolt://localhost:7687` |
| `--neo4j-user` | Neo4j 사용자 이름입니다. | `neo4j` |
| `--neo4j-password`| Neo4j 비밀번호입니다. | `.env` 파일의 `NEO4J_PASSWORD` 값 |
| `--query` | 실행할 사용자 정의 Cypher 쿼리 문자열입니다. | |
| `--basic` | 모든 클래스의 기본 정보를 조회합니다. | Flag |
| `--detailed` | 클래스의 메서드 및 속성을 포함한 상세 정보를 조회합니다. | Flag |
| `--inheritance` | 클래스 간의 상속 및 구현 관계를 조회합니다. | Flag |
| `--package` | 패키지 기준으로 클래스 정보를 조회합니다. | Flag |

---

## 3. `sequence`

특정 클래스 및 메서드의 호출 관계를 분석하여 시퀀스 다이어그램(Mermaid 형식)을 생성합니다.

### 실행 예시

```bash
# 특정 클래스의 시퀀스 다이어그램 생성
python -m src.cli.main sequence --class-name MyController

# 특정 메서드에 초점을 맞춘 시퀀스 다이어그램 생성
python -m src.cli.main sequence --class-name MyService --method-name myMethod

# PNG 이미지 파일로 저장
python -m src.cli.main sequence --class-name MyController --output-image diagram.png
```

### 옵션

| 옵션 | 설명 | 기본값/필수 |
| --- | --- | --- |
| `--class-name` | 분석할 클래스의 이름입니다. | **필수** |
| `--method-name` | 분석을 시작할 특정 메서드의 이름입니다. (선택 사항) | |
| `--max-depth` | 추적할 호출 체인의 최대 깊이입니다. | `10` |
| `--include-external`| 외부 라이브러리 호출을 다이어그램에 포함합니다. | Flag |
| `--method-focused`| 지정된 메서드와 그 직접적인 호출만 표시하는 다이어그램을 생성합니다. | Flag |
| `--output-file` | 다이어그램을 저장할 `.md` 파일 경로입니다. | |
| `--output-image` | 다이어그램을 이미지(PNG/SVG/PDF)로 저장할 파일 경로입니다. (`mermaid-cli` 필요) | |
| `--image-format` | 생성할 이미지의 형식입니다. | `png` |
| `--image-width` | 이미지의 너비(px)입니다. | `1200` |
| `--image-height` | 이미지의 높이(px)입니다. | `800` |
| ... (공통 Neo4j 옵션) | | |

---

## 4. `list-classes` / `list-methods`

데이터베이스에 저장된 모든 클래스 또는 특정 클래스의 메서드 목록을 출력합니다.

### 실행 예시

```bash
# 모든 클래스 목록 보기
python -m src.cli.main list-classes

# 특정 클래스의 모든 메서드 목록 보기
python -m src.cli.main list-methods --class-name MyService
```

### 옵션 (`list-methods`)

| 옵션 | 설명 | 기본값/필수 |
| --- | --- | --- |
| `--class-name` | 메서드를 조회할 클래스의 이름입니다. | **필수** |
| ... (공통 Neo4j 옵션) | | |

---

## 5. `crud-matrix` / `crud-analysis` / `crud_visualization`

클래스와 데이터베이스 테이블 간의 CRUD(Create, Read, Update, Delete) 관계를 분석하고 매트릭스 형태로 보여주거나 시각화 다이어그램을 생성합니다.

### 실행 예시

```bash
# CRUD 매트릭스 보기
python -m src.cli.main crud-matrix

# CRUD 분석 (SQL 호출 클래스만)
python -m src.cli.main crud-analysis --project-name my-project

# CRUD 관계 시각화 다이어그램 생성
python -m src.cli.main crud-visualization --project-name my-project --output-image crud.png
```

### 옵션

| 옵션 | 설명 | 기본값/필수 |
| --- | --- | --- |
| `--project-name` | 분석할 프로젝트의 이름입니다. | **필수** (`crud-analysis` 등) |
| `--output-file` | 분석 결과를 저장할 JSON 파일 경로입니다. | |
| `--output-excel` | CRUD 매트릭스를 Excel 파일로 저장합니다. (`crud-analysis` 전용) | |
| `--create-relationships` | 분석 전 `Method-SqlStatement` 관계를 먼저 생성합니다. (`crud-analysis` 전용) | Flag |
| ... (공통 Neo4j 옵션) | | |

---

## 6. `db-analysis` / `db-statistics`

데이터베이스 사용량, SQL 통계, 테이블 사용 현황 등 다양한 DB 관련 통계를 분석합니다.

### 실행 예시

```bash
# DB 호출 관계 분석 보기
python -m src.cli.main db-analysis --project-name my-project

# DB 사용 통계 보기
python -m src.cli.main db-statistics --project-name my-project
```

### 옵션

| 옵션 | 설명 | 기본값/필수 |
| --- | --- | --- |
| `--project-name` | 분석할 프로젝트의 이름입니다. | **필수** 또는 선택 |
| ... (공통 Neo4j 옵션) | | |

---

## 7. `db-call-chain` / `db-call-diagram`

메서드 호출부터 시작하여 최종적인 DB 테이블 및 컬럼 접근까지의 전체 호출 체인을 추적하고 분석하거나, 이를 다이어그램으로 시각화합니다.

### 실행 예시

```bash
# 특정 클래스에서 시작하는 DB 호출 체인 분석
python -m src.cli.main db-call-chain --project-name my-project --start-class MyService

# DB 호출 체인 다이어그램 생성
python -m src.cli.main db-call-diagram --project-name my-project --output-image db-calls.png
```

### 옵션

| 옵션 | 설명 | 기본값/필수 |
| --- | --- | --- |
| `--project-name` | 분석할 프로젝트의 이름입니다. | **필수** |
| `--start-class` | 분석을 시작할 클래스 이름입니다. | |
| `--start-method` | 분석을 시작할 메서드 이름입니다. | |
| ... (공통 Neo4j 및 출력 옵션) | | |

---

## 8. `table-summary` / `table-impact`

특정 테이블에 대한 CRUD 요약 정보를 보거나, 테이블 변경 시 영향을 받는 애플리케이션 코드를 분석합니다.

### 실행 예시

```bash
# 테이블별 CRUD 요약 보기
python -m src.cli.main table-summary --project-name my-project

# 특정 테이블 변경 시 영향도 분석
python -m src.cli.main table-impact --project-name my-project --table-name ORDERS
```

### 옵션

| 옵션 | 설명 | 기본값/필수 |
| --- | --- | --- |
| `--project-name` | 분석할 프로젝트의 이름입니다. | **필수** |
| `--table-name` | 영향도를 분석할 테이블 이름입니다. (`table-impact` 전용) | **필수** |
| ... (공통 Neo4j 및 출력 옵션) | | |
