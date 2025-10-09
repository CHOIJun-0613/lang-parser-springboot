# Java 소스 코드 분석기 (CSA - Code Static Analyzer)

## 📋 개요

이 프로젝트는 **Spring Boot 기반 Java 애플리케이션**을 정적 분석하여 코드 구조, 호출 관계, 데이터베이스 상호작용을 분석하고 시각화하는 도구입니다. 

### 주요 기능
- 🔍 **Java 소스 코드 파싱**: 클래스, 메서드, 필드, 어노테이션 등 추출
- 🗄️ **데이터베이스 호출 분석**: Controller → Service → Repository → SQL → Table 호출 체인 분석
- 📊 **CRUD 매트릭스 생성**: 테이블별 CRUD 작업 매핑
- 📈 **시퀀스 다이어그램 생성**: PlantUML/Mermaid 형식 지원
- 🎯 **Neo4j 그래프 데이터베이스**: 분석 결과 저장 및 관계 시각화
- ⚙️ **Spring Boot 특화 분석**: Bean, Endpoint, JPA, MyBatis 등 프레임워크 요소 분석

## 🏗️ 프로젝트 구조

```
lang-parser-springboot/
├── csa/                          # Code Static Analyzer 핵심 모듈
│   ├── cli/
│   │   └── main.py              # CLI 엔트리 포인트
│   ├── models/
│   │   └── graph_entities.py    # Neo4j 그래프 데이터 모델
│   ├── services/
│   │   ├── java_parser.py       # Java 소스 파싱 및 분석
│   │   ├── java_parser_addon_r001.py  # 논리명 추출 규칙 적용
│   │   ├── sql_parser.py        # SQL 문 분석
│   │   ├── db_parser.py         # DB 스키마 파싱
│   │   ├── db_call_analysis.py  # DB 호출 관계 분석
│   │   ├── graph_db.py          # Neo4j 데이터베이스 관리
│   │   ├── sequence_diagram_generator.py  # 시퀀스 다이어그램 생성 Facade
│   │   ├── plantuml_diagram_generator.py # PlantUML 다이어그램 생성
│   │   └── mermaid_diagram_generator.py  # Mermaid 다이어그램 생성
│   ├── rules/                   # 프로젝트별 논리명 추출 규칙
│   └── utils/
│       └── logger.py            # 로깅 유틸리티
├── commands/                    # 배치 실행 스크립트
├── docs/                        # 상세 문서
├── libs/                        # 외부 라이브러리 (PlantUML 등)
├── output/                      # 생성된 다이어그램 및 매트릭스
└── tests/                       # 테스트 코드
```

## 🚀 설치 및 설정

### 1. 환경 설정

```bash
# 저장소 클론
git clone <repository-url>
cd lang-parser-springboot

# 가상환경 생성 및 활성화
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# 의존성 설치
pip install -r requirements.txt
```

### 2. 환경 변수 설정

`env.example` 파일을 참고하여 `.env` 파일을 생성하세요:

```bash
# Neo4j 데이터베이스 설정
NEO4J_URI=neo4j://127.0.0.1:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=devpass123

# 분석할 프로젝트 경로
JAVA_SOURCE_FOLDER=D:\workspaces\your-project\src\main\java
DB_SCRIPT_FOLDER=D:\workspaces\your-project\src\main\resources\db

# 로그 레벨
LOG_LEVEL=INFO

# 출력 디렉토리
SEQUENCE_DIAGRAM_OUTPUT_DIR=./output/sequence-diagram
CRUD_MATRIX_OUTPUT_DIR=./output/crud-matrix
```

### 3. Neo4j 데이터베이스 설정

Neo4j 데이터베이스를 설치하고 실행한 후, 다음 스크립트로 스키마를 설정하세요:

```bash
# Neo4j 브라우저에서 실행
cat docs/db_schema_setup.sql
```

### 4. 외부 도구 설치 (선택사항)

#### PlantUML (이미지 생성용)
```bash
# libs 폴더에 plantuml.jar 다운로드
mkdir -p libs
curl -L https://github.com/plantuml/plantuml/releases/latest/download/plantuml.jar -o libs/plantuml.jar
```

#### Mermaid CLI (이미지 생성용)
```bash
npm install -g @mermaid-js/mermaid-cli
```

## 💻 사용법

### CLI 명령어 개요

CSA는 다양한 분석 및 시각화 기능을 제공하는 CLI 도구입니다. 모든 명령어는 `python -m csa.cli.main <command>` 형태로 실행합니다.

#### 🔧 주요 명령어 목록

| 명령어 | 기능 | 주요 옵션 |
|--------|------|-----------|
| `analyze` | Java/DB 소스 분석 | `--all-objects`, `--java-object`, `--db-object`, `--clean` |
| `query` | Neo4j 데이터베이스 쿼리 실행 | `--basic`, `--detailed`, `--inheritance`, `--package` |
| `sequence` | 시퀀스 다이어그램 생성 | `--class-name`, `--method-name`, `--format` |
| `list_classes` | 데이터베이스의 클래스 목록 조회 | - |
| `list_methods` | 특정 클래스의 메서드 목록 조회 | `--class-name` |
| `crud-matrix` | CRUD 매트릭스 생성 | `--project-name`, `--output-format` |
| `db_analysis` | DB 호출 관계 분석 | `--project-name` |
| `table_summary` | 테이블별 CRUD 요약 | `--project-name` |
| `db_call_chain` | DB 호출 체인 분석 | `--project-name`, `--start-class`, `--start-method` |
| `crud_analysis` | CRUD 분석 결과 생성 | `--project-name`, `--output-excel` |
| `db_call_diagram` | DB 호출 체인 다이어그램 생성 | `--project-name`, `--output-image` |

### 📊 명령어별 상세 옵션

#### 1. `analyze` - 소스 코드 분석
```bash
# 전체 분석 (Java + DB)
python -m csa.cli.main analyze --all-objects --clean

# Java 소스만 분석
python -m csa.cli.main analyze --java-object --clean

# DB 스키마만 분석
python -m csa.cli.main analyze --db-object --clean

# 특정 클래스만 분석
python -m csa.cli.main analyze --class-name UserController --clean

# 업데이트 모드 (기존 데이터 유지)
python -m csa.cli.main analyze --all-objects --update

# 드라이런 (DB 연결 없이 파싱만)
python -m csa.cli.main analyze --java-object --dry-run
```

**주요 옵션:**
- `--java-source-folder`: Java 소스 폴더 경로
- `--clean`: 분석 전 데이터베이스 초기화
- `--class-name`: 특정 클래스만 분석
- `--update`: 기존 데이터 유지하며 업데이트
- `--db-object`: DB 객체 분석
- `--java-object`: Java 객체 분석
- `--all-objects`: Java + DB 모두 분석
- `--dry-run`: DB 연결 없이 파싱만 수행
- `--project-name`: 프로젝트 이름 지정

#### 2. `query` - 데이터베이스 쿼리
```bash
# 기본 클래스 쿼리
python -m csa.cli.main query --basic

# 상세 클래스 쿼리 (메서드, 속성 포함)
python -m csa.cli.main query --detailed

# 상속 관계 쿼리
python -m csa.cli.main query --inheritance

# 패키지별 클래스 쿼리
python -m csa.cli.main query --package

# 커스텀 쿼리 실행
python -m csa.cli.main query --query "MATCH (c:Class) RETURN c.name LIMIT 10"
```

#### 3. `sequence` - 시퀀스 다이어그램 생성
```bash
# 특정 클래스의 시퀀스 다이어그램 (기본: Mermaid)
python -m csa.cli.main sequence --class-name UserController

# 특정 메서드의 시퀀스 다이어그램 (기본: Mermaid)
python -m csa.cli.main sequence --class-name UserController --method-name getUser

# PlantUML 형식으로 생성
python -m csa.cli.main sequence --class-name UserController --format plantuml

# 이미지로 변환 (PNG)
python -m csa.cli.main sequence --class-name UserController --image-format png

# 출력 디렉토리 지정
python -m csa.cli.main sequence --class-name UserController --output-dir ./diagrams
```

**주요 옵션:**
- `--class-name`: 분석할 클래스명 (필수)
- `--method-name`: 특정 메서드만 분석
- `--max-depth`: 호출 체인 최대 깊이 (기본값: 10)
- `--include-external`: 외부 라이브러리 호출 포함
- `--format`: 다이어그램 형식 (기본값: mermaid, 선택: plantuml)
- `--image-format`: 이미지 형식 (none, png, svg, pdf)
- `--image-width`: 이미지 너비 (기본값: 1200)
- `--image-height`: 이미지 높이 (기본값: 800)

#### 4. `crud-matrix` - CRUD 매트릭스 생성
```bash
# 기본 CRUD 매트릭스 생성
python -m csa.cli.main crud-matrix

# 특정 프로젝트의 CRUD 매트릭스
python -m csa.cli.main crud-matrix --project-name myproject

# Excel 형식으로 출력
python -m csa.cli.main crud-matrix --output-format excel

# SVG 이미지로 출력
python -m csa.cli.main crud-matrix --output-format svg
```

#### 5. `db_call_chain` - DB 호출 체인 분석
```bash
# 전체 프로젝트 호출 체인 분석
python -m csa.cli.main db_call_chain --project-name myproject

# 특정 클래스부터 시작하는 호출 체인
python -m csa.cli.main db_call_chain --project-name myproject --start-class UserController

# 특정 메서드부터 시작하는 호출 체인
python -m csa.cli.main db_call_chain --project-name myproject --start-class UserController --start-method getUser

# 결과를 파일로 저장
python -m csa.cli.main db_call_chain --project-name myproject --output-file call_chain.json
```

#### 6. `db_call_diagram` - DB 호출 체인 다이어그램 생성
```bash
# 기본 호출 체인 다이어그램 생성
python -m csa.cli.main db_call_diagram --project-name myproject

# 특정 클래스부터 시작하는 다이어그램
python -m csa.cli.main db_call_diagram --project-name myproject --start-class UserController

# 이미지로 출력
python -m csa.cli.main db_call_diagram --project-name myproject --output-image diagram.png --image-format png
```

### 🔧 공통 옵션

모든 명령어에서 사용 가능한 공통 옵션:

- `--neo4j-uri`: Neo4j 데이터베이스 URI (기본값: bolt://localhost:7687)
- `--neo4j-user`: Neo4j 사용자명 (기본값: neo4j)
- `--neo4j-password`: Neo4j 비밀번호 (환경변수에서 자동 읽기)

### 기본 명령어

```bash
# 가상환경 활성화
.venv\Scripts\activate

# 전체 분석 (Java + DB)
python -m csa.cli.main analyze --all-objects --clean

# Java 소스만 분석
python -m csa.cli.main analyze --java-object --clean

# DB 스키마만 분석
python -m csa.cli.main analyze --db-object --clean
```

### 배치 스크립트 사용

```bash
# 전체 재분석
commands\1-1.전체재분석.bat

# Java 재분석
commands\1-2.자바재분석.bat

# DB 재분석
commands\1-3.DB재분석.bat

# 시퀀스 다이어그램 생성 (PlantUML SVG)
commands\2-1.시퀀스-PlantUML-SVG.bat

# CRUD 매트릭스 생성
commands\2-2.CRUD-Matrix.bat
```

### 고급 기능

#### 1. 데이터베이스 호출 관계 분석

```bash
# 전체 프로젝트 호출 체인 분석
python -m csa.cli.main db-call-chain --project-name myproject

# 특정 클래스부터 시작하는 호출 체인
python -m csa.cli.main db-call-chain --project-name myproject --start-class UserController

# 특정 메서드부터 시작하는 호출 체인
python -m csa.cli.main db-call-chain --project-name myproject --start-class UserController --start-method getUser
```

#### 2. 시퀀스 다이어그램 생성

```bash
# Mermaid 형식으로 생성
python -m csa.cli.main sequence --format mermaid --output-dir ./output/sequence-diagram

# PlantUML 형식으로 생성
python -m csa.cli.main sequence --format plantuml --output-dir ./output/sequence-diagram
```

#### 3. CRUD 매트릭스 생성

```bash
# CRUD 매트릭스 생성
python -m csa.cli.main crud-matrix --output-dir ./output/crud-matrix
```

## 🔧 주요 모듈 설명

### `csa/cli/main.py`
- 애플리케이션의 메인 엔트리 포인트
- Click 기반 CLI 인터페이스 제공
- 전체 분석 프로세스 조율

### `csa/models/graph_entities.py`
- Neo4j 그래프 데이터베이스용 Pydantic 모델 정의
- Project, Class, Method, Field, Annotation, Bean, Endpoint 등
- Spring Boot 특화 모델들 포함

### `csa/services/java_parser.py`
- javalang 라이브러리를 사용한 Java 소스 파싱
- Spring Boot 어노테이션 분석 (@Component, @Service, @RestController 등)
- JPA 엔티티, MyBatis 매퍼 분석

### `csa/services/db_call_analysis.py`
- Controller → Service → Repository → SQL → Table 호출 체인 분석
- CRUD 매트릭스 생성
- 영향도 분석 및 시각화

### `csa/services/graph_db.py`
- Neo4j 데이터베이스 CRUD 작업 관리
- 노드 및 관계 생성, 조회, 업데이트, 삭제

### `csa/services/sequence_diagram_generator.py`
- PlantUML/Mermaid 시퀀스 다이어그램 생성 Facade
- 호출 관계를 시각적 다이어그램으로 변환

## 📚 상세 문서

- [DB 호출 관계 분석 사용법](docs/db_call_analysis_usage.md)
- [Java Parser Addon R001 사용법](docs/java_parser_addon_r001_usage.md)
- [Spring Boot 분석 계획](docs/springboot_analysis_plan.md)
- [DB 스키마 설정](docs/db_schema_setup.sql)

## 🧪 테스트

```bash
# 전체 테스트 실행
pytest

# 특정 테스트 실행
pytest tests/unit/test_java_parser.py
pytest tests/integration/test_end_to_end.py
```

## 📊 출력 결과

### 1. Neo4j 그래프 데이터베이스
- 분석된 모든 코드 요소와 관계가 그래프로 저장
- Neo4j 브라우저에서 시각적 탐색 가능

### 2. 시퀀스 다이어그램
- `output/sequence-diagram/` 폴더에 생성
- PlantUML (.puml) 또는 Mermaid (.md) 형식

### 3. CRUD 매트릭스
- `output/crud-matrix/` 폴더에 Excel 파일로 생성
- 테이블별 CRUD 작업 매핑

## 🔍 분석 대상 요소

### Java 코드 분석
- **클래스**: 일반 클래스, 인터페이스, 추상 클래스
- **메서드**: 접근 제어자, 매개변수, 반환 타입
- **필드**: 변수 타입, 어노테이션
- **어노테이션**: Spring Boot, JPA, MyBatis 등 프레임워크 어노테이션

### Spring Boot 특화 분석
- **Bean**: @Component, @Service, @Repository 등
- **Endpoint**: @RestController, @RequestMapping 등
- **JPA**: @Entity, @Table, @Column, @OneToMany 등
- **MyBatis**: @Mapper, XML 매퍼 파일

### 데이터베이스 분석
- **테이블**: 컬럼, 인덱스, 제약조건
- **SQL 문**: SELECT, INSERT, UPDATE, DELETE
- **호출 관계**: Java 코드와 DB 테이블 간의 관계

## 🤝 기여하기

1. 이 저장소를 포크하세요
2. 새로운 기능 브랜치를 생성하세요 (`git checkout -b feature/amazing-feature`)
3. 변경사항을 커밋하세요 (`git commit -m 'Add some amazing feature'`)
4. 브랜치에 푸시하세요 (`git push origin feature/amazing-feature`)
5. Pull Request를 생성하세요

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 🆘 문제 해결

### 일반적인 문제

1. **Neo4j 연결 오류**: Neo4j가 실행 중인지 확인하고 연결 정보를 확인하세요
2. **Java 파싱 오류**: javalang 라이브러리 버전을 확인하세요
3. **PlantUML 이미지 생성 실패**: plantuml.jar 파일이 libs 폴더에 있는지 확인하세요

### 로그 확인

```bash
# 로그 레벨을 DEBUG로 설정하여 상세 로그 확인
LOG_LEVEL=DEBUG python -m csa.cli.main analyze --all-objects
```

---

**문의사항이나 버그 리포트는 이슈 트래커를 통해 제출해 주세요.**