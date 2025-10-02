# Java 소스 코드 분석기

## 1. 개요

이 프로젝트는 지정된 경로의 Java 소스 코드를 분석하여 그 구조와 관계를 시각화하고 데이터베이스에 저장하는 도구입니다. 코드를 파싱하여 클래스, 메서드, 속성 등의 구성 요소를 추출하고, 이들 간의 호출 관계 및 데이터베이스 상호작용을 분석하여 Neo4j 그래프 데이터베이스에 저장합니다.

## 2. 프로젝트 구조

```
src/
├── cli/
│   └── main.py           # CLI(Command Line Interface) 엔트리 포인트
├── models/
│   └── graph_entities.py # Graph DB에 저장될 데이터 모델 (Node, Relationship) 정의
├── services/
│   ├── java_parser.py    # Java 소스 코드를 파싱하여 AST(Abstract Syntax Tree) 생성 및 분석
│   ├── sql_parser.py     # 코드 내 SQL 문을 파싱하고 분석
│   ├── db_call_analysis.py # Java 코드와 DB 호출 관계 분석
│   ├── graph_db.py       # Neo4j 데이터베이스 연결 및 데이터 CRUD 관리
│   └── sequence_diagram_generator.py # 분석 데이터를 기반으로 시퀀스 다이어그램 생성
└── utils/
    └── logger.py         # 로깅 유틸리티
```

## 3. 주요 모듈 설명

### `cli/main.py`

-   애플리케이션의 메인 시작점입니다.
-   `argparse`를 사용하여 커맨드 라인 인자(분석할 프로젝트 경로 등)를 처리하고, 전체 분석 프로세스를 조율합니다.

### `models/graph_entities.py`

-   Neo4j 그래프 데이터베이스에 저장될 노드(Node)와 관계(Relationship)의 데이터 구조를 Pydantic 모델로 정의합니다.
-   예: `Project`, `File`, `Class`, `Method`, `Call` 등.

### `services/java_parser.py`

-   `javalang` 라이브러리를 사용하여 Java 소스 파일을 파싱합니다.
-   클래스, 인터페이스, 메서드, 필드, 어노테이션 등의 정보를 추출하여 그래프 엔티티로 변환합니다.

### `services/sql_parser.py`

-   `sqlparse` 라이브러리를 사용하여 코드에서 추출된 SQL 쿼리문을 분석합니다.
-   쿼리 유형(SELECT, INSERT 등), 대상 테이블, 컬럼 등의 정보를 식별합니다.

### `services/db_call_analysis.py`

-   `java_parser`와 `sql_parser`의 분석 결과를 종합합니다.
-   Java 메서드와 관련된 데이터베이스 테이블 간의 관계(e.g., CRUD)를 분석하고, 이를 그래프 DB에 저장할 수 있도록 가공합니다.

### `services/graph_db.py`

-   Neo4j 데이터베이스와의 모든 상호작용을 담당합니다.
-   노드 및 관계의 생성, 조회, 업데이트, 삭제(CRUD) 로직을 포함합니다.

### `utils/logger.py`

-   프로젝트 전반에서 사용될 로거를 설정하고 관리하는 유틸리티입니다.

## 4. 실행 방법

커맨드 라인에서 `src/cli/main.py`를 실행하여 분석을 시작할 수 있습니다. 분석할 Java 프로젝트의 경로를 인자로 전달해야 합니다.

```bash
python -m src.cli.main --project_path <분석할 프로젝트 경로>
```
