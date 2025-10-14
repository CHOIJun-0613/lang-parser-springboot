# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

CSA (Code Static Analyzer)는 Spring Boot 기반 Java 애플리케이션을 정적 분석하여 코드 구조, 호출 관계, 데이터베이스 상호작용을 분석하고 Neo4j 그래프 데이터베이스에 저장한 뒤 시퀀스 다이어그램과 CRUD 매트릭스를 생성하는 Python 기반 도구입니다.

## 핵심 아키텍처

### 모듈 구성

```
csa/
├── cli/                    # CLI 진입점 및 명령어 핸들러
│   ├── main.py            # Click 기반 CLI 엔트리포인트
│   └── commands/          # 각 명령어별 핸들러
├── models/                # Pydantic 도메인 모델
│   ├── graph_entities.py  # Neo4j 그래프 엔티티 (Project, Class, Method, Bean, Endpoint 등)
│   └── analysis.py        # 분석 관련 모델
├── services/              # 핵심 분석 서비스
│   ├── analysis/          # 분석 오케스트레이션
│   │   ├── java_pipeline.py    # Java 분석 파이프라인
│   │   ├── db_pipeline.py      # DB 분석 파이프라인
│   │   ├── neo4j_writer.py     # Neo4j 데이터 저장
│   │   └── handlers.py         # 파싱 결과 처리
│   ├── java_analysis/     # Java 파싱 세부 모듈
│   │   ├── project.py     # 프로젝트 구조 분석
│   │   ├── spring.py      # Spring Boot 어노테이션 분석
│   │   ├── mybatis.py     # MyBatis 매퍼 분석
│   │   ├── jpa.py         # JPA 엔티티 분석
│   │   ├── config.py      # 설정 파일 분석
│   │   ├── tests.py       # 테스트 코드 분석
│   │   └── utils.py       # 파싱 유틸리티
│   ├── java_parser.py     # Java 파싱 Facade
│   ├── java_parser_addon_r001.py  # 논리명 추출 규칙
│   ├── sql_parser.py      # SQL 문 분석
│   ├── db_parser.py       # DB DDL 스키마 파싱
│   ├── graph_db/          # Neo4j 데이터베이스 작업
│   │   ├── base.py        # 기본 연결 및 트랜잭션
│   │   ├── project_nodes.py     # Project 노드 CRUD
│   │   ├── application_nodes.py # Class/Method/Field 노드 CRUD
│   │   ├── persistence_nodes.py # JPA/MyBatis 노드 CRUD
│   │   ├── database_nodes.py    # Table/Column/Index 노드 CRUD
│   │   ├── analytics.py   # 분석 쿼리
│   │   └── maintenance.py # 유지보수 작업
│   └── db_call_analysis/  # DB 호출 관계 분석
│       ├── call_chain.py  # Controller→Service→Repository→SQL→Table 체인
│       ├── crud.py        # CRUD 매트릭스 생성
│       ├── diagrams.py    # 호출 체인 다이어그램
│       ├── impact.py      # 영향도 분석
│       └── reports.py     # 분석 리포트
├── parsers/               # 특화 파서
│   ├── java/              # Java 논리명 추출
│   │   └── logical_name.py
│   └── db/                # DB DDL 파싱
│       └── ddl_parser.py
├── diagrams/              # 다이어그램 생성
│   └── sequence/          # 시퀀스 다이어그램 생성기 (PlantUML/Mermaid)
├── dbwork/                # Neo4j 연결 풀 관리
├── utils/                 # 공용 유틸리티 (로거, 환경변수 헬퍼 등)
├── rules/                 # 논리명 추출 규칙 정의
└── vendor/                # 외부 벤더 통합
```

### 핵심 데이터 플로우

1. **Java 분석**: `java_pipeline.py` → `java_analysis/*` 모듈들 → `neo4j_writer.py` → Neo4j
2. **DB 분석**: `db_pipeline.py` → `db_parser.py` → `neo4j_writer.py` → Neo4j
3. **호출 체인 분석**: Neo4j 쿼리 → `db_call_analysis/call_chain.py` → 관계 그래프 생성
4. **다이어그램 생성**: Neo4j 데이터 → `diagrams/sequence/` → PlantUML/Mermaid 파일

### Neo4j 그래프 모델

- **프로젝트 노드**: `Project`
- **코드 노드**: `Class`, `Method`, `Field`, `Package`, `Annotation`
- **Spring Boot 노드**: `Bean`, `Endpoint`, `BeanDependency`
- **영속성 노드**: `MyBatisMapper`, `MyBatisSqlStatement`, `SqlStatement`, `JpaEntity`, `JpaRepository`, `JpaQuery`
- **데이터베이스 노드**: `Database`, `Table`, `Column`, `Index`, `Constraint`
- **관계**: `BELONGS_TO`, `HAS_METHOD`, `CALLS`, `USES_TABLE`, `INJECTS`, `MAPS_TO` 등

## 개발 환경 설정

### 초기 설정

```bash
# 가상 환경 생성 및 활성화
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# 의존성 설치
pip install -r requirements.txt

# 환경 변수 설정 (.env 파일 생성)
cp env.example .env
```

### 필수 환경 변수

```
NEO4J_URI=neo4j://127.0.0.1:7687
NEO4J_DATABASE=csadb01
NEO4J_USER=csauser
NEO4J_PASSWORD=csauser123
JAVA_SOURCE_FOLDER=target_src/car-center-devlab
DB_SCRIPT_FOLDER=target_src/car-center-devlab/src/main/resources/db/prod
LOG_LEVEL=INFO
SEQUENCE_DIAGRAM_OUTPUT_DIR=./output/sequence-diagram
CRUD_MATRIX_OUTPUT_DIR=./output/crud-matrix
```

## 주요 명령어

### 분석 명령어

```bash
# 전체 재분석 (Java + DB, 기존 데이터 삭제)
python -m csa.cli.main analyze --all-objects --clean --project-name <프로젝트명>

# Java 소스만 재분석
python -m csa.cli.main analyze --java-object --clean --project-name <프로젝트명>

# DB 스키마만 재분석
python -m csa.cli.main analyze --db-object --clean --project-name <프로젝트명>

# 특정 클래스만 분석
python -m csa.cli.main analyze --class-name UserController --project-name <프로젝트명>

# 업데이트 모드 (기존 데이터 유지)
python -m csa.cli.main analyze --all-objects --update --project-name <프로젝트명>

# 드라이런 (Neo4j 연결 없이 파싱만 수행)
python -m csa.cli.main analyze --java-object --dry-run
```

### 시퀀스 다이어그램 생성

```bash
# Mermaid 형식 (기본)
python -m csa.cli.main sequence --class-name UserController

# 특정 메서드만 분석
python -m csa.cli.main sequence --class-name UserController --method-name getUser

# PlantUML 형식
python -m csa.cli.main sequence --class-name UserController --format plantuml

# 이미지로 변환 (PNG/SVG/PDF)
python -m csa.cli.main sequence --class-name UserController --image-format png

# 호출 깊이 제한
python -m csa.cli.main sequence --class-name UserController --max-depth 5
```

### DB 호출 관계 분석

```bash
# 전체 프로젝트 호출 체인 분석
python -m csa.cli.main db_call_chain --project-name myproject

# 특정 클래스부터 시작하는 호출 체인
python -m csa.cli.main db_call_chain --project-name myproject --start-class UserController

# CRUD 매트릭스 생성
python -m csa.cli.main crud-matrix --project-name myproject --output-format excel

# DB 호출 체인 다이어그램 생성
python -m csa.cli.main db_call_diagram --project-name myproject --output-image diagram.png
```

### 배치 스크립트 (Windows)

```bash
commands\1-1.전체재분석.bat           # 전체 재분석
commands\1-2.자바재분석.bat           # Java만 재분석
commands\1-3.DB재분석.bat             # DB만 재분석
commands\2-1.시퀀스-PlantUML-SVG.bat  # 시퀀스 다이어그램 생성
commands\2-2.CRUD-Matrix.bat          # CRUD 매트릭스 생성
```

### 테스트

```bash
# 전체 테스트
pytest

# 단위 테스트만
pytest tests/unit

# 통합 테스트만
pytest tests/integration

# 특정 테스트 파일
pytest tests/unit/test_java_parser.py

# 테스트 이름 패턴 매칭
pytest tests/integration -k end_to_end
```

## 코딩 가이드라인

### 스타일 및 네이밍

- **PEP 8 준수**: 4칸 들여쓰기, `snake_case` 함수/모듈, `PascalCase` 클래스
- **타입 힌트 사용**: 모든 함수 시그니처에 타입 힌트 추가
- **Pydantic 모델 활용**: 데이터 검증 및 직렬화에 Pydantic 사용
- **로깅**: `csa.utils.logger.get_logger(__name__)` 사용
- **환경 변수**: `.env` 파일과 헬퍼 함수를 통해 주입, 하드코딩 금지

### 코드 구조

- **함수 모듈화**: 하나의 함수는 100줄 이내 유지
- **파일 크기**: 하나의 파일은 1000줄 이내 유지 (초과 시 분리)
- **의존성 주입**: 전역 변수 대신 헬퍼를 통해 의존성 주입
- **에러 핸들링**: 명확한 예외 처리 및 로깅

### 주석 및 문서화

- **Docstring**: 모든 public 함수/클래스에 한국어 docstring 작성
- **인라인 주석**: 복잡한 로직에는 한국어 주석 추가
- **타입 힌트**: 코드의 자기 문서화를 위해 타입 힌트 필수

### 테스트 가이드

- **가상 환경 활성화**: Python 프로그램 실행 시 반드시 `.venv\Scripts\activate` 또는 `runvenv.bat` 실행
- **임시 테스트**: `./tests` 폴더에 생성
- **Neo4j 테스트 연결**:
  - URI: `neo4j://127.0.0.1:7687`
  - Database: `csadb01`
  - User: `csauser`
  - Password: `csauser123`

## 주요 분석 대상

### Java 코드 분석

- **클래스**: 일반 클래스, 인터페이스, 추상 클래스, Enum
- **메서드**: 시그니처, 접근 제어자, 메서드 호출 체인
- **필드**: 타입, 어노테이션, 초기값
- **어노테이션**: Spring Boot, JPA, MyBatis, 테스트 프레임워크
- **패키지**: 구조 및 논리적 그룹핑

### Spring Boot 특화 분석

- **Bean**: `@Component`, `@Service`, `@Repository`, `@Controller`, `@Configuration`
- **의존성 주입**: `@Autowired`, `@Inject`, 생성자 주입
- **Endpoint**: `@RestController`, `@RequestMapping`, HTTP 메서드
- **JPA**: `@Entity`, `@Table`, `@Column`, 관계 어노테이션
- **MyBatis**: `@Mapper`, XML 매퍼, SQL 문
- **설정**: `application.yml`, `application.properties`

### 데이터베이스 분석

- **DDL 파싱**: `CREATE TABLE`, `ALTER TABLE`, `CREATE INDEX`
- **테이블**: 컬럼, 제약조건, 인덱스
- **SQL 문**: SELECT, INSERT, UPDATE, DELETE (MyBatis/JPA Native Query)
- **호출 관계**: Controller → Service → Repository → SQL → Table

## 논리명 추출 규칙

프로젝트는 `java_parser_addon_r001.py` 및 `csa/parsers/java/logical_name.py`를 통해 Java 코드의 논리명을 추출합니다. 규칙 정의는 `csa/rules/` 디렉토리에 저장됩니다.

- **패키지 논리명**: 패키지명 → 한글 논리명 매핑
- **클래스 논리명**: 주석, JavaDoc, 어노테이션에서 추출
- **메서드 논리명**: 주석, 메서드명 패턴 분석
- **필드 논리명**: 주석, 변수명 분석

## 주의사항

### 개발 원칙

- **구조 변경 금지**: 임의로 애플리케이션 구조를 변경하지 말 것
- **확인 절차**: 수정 전 영향도 분석 후 사용자에게 확인
- **한국어 소통**: 모든 답변 및 주석은 한국어로 작성
- **수정 내역 공유**: 수정 후 이유와 내용을 명확히 설명

### 보안

- **민감 정보 커밋 금지**: `.env` 파일, 자격 증명, API 키 등
- **env.example 사용**: 기본값만 `env.example`에 남기기
- **Neo4j 스키마 변경**: `docs/` 디렉토리에 SQL 스크립트로 버전 관리

### Neo4j 연결

- **연결 풀 사용**: `csa.dbwork.connection_pool.get_connection_pool()` 사용
- **트랜잭션 관리**: 작업 후 반드시 커밋/롤백
- **연결 종료**: 프로그램 종료 시 `pool.close_all()` 호출

## 출력 결과

### Neo4j 그래프 데이터베이스

- 모든 코드 요소와 관계를 그래프로 저장
- Neo4j 브라우저에서 시각적 탐색 가능 (http://localhost:7474)
- Cypher 쿼리를 통한 복잡한 관계 분석

### 시퀀스 다이어그램

- **위치**: `output/sequence-diagram/<프로젝트명>/`
- **형식**: PlantUML (`.puml`), Mermaid (`.md`)
- **이미지**: PNG, SVG, PDF (선택적)

### CRUD 매트릭스

- **위치**: `output/crud-matrix/`
- **형식**: Excel (`.xlsx`), Markdown (`.md`)
- **내용**: 테이블별 CRUD 작업 매핑

## 문제 해결

### 일반적인 문제

1. **Neo4j 연결 오류**: Neo4j 서비스 실행 상태 및 `.env` 설정 확인
2. **Java 파싱 오류**: `javalang` 버전 확인 (>= 0.13.0)
3. **PlantUML 이미지 생성 실패**: `libs/plantuml.jar` 존재 여부 확인
4. **Mermaid 이미지 생성 실패**: `mmdc` 설치 및 `MMDC_PATH` 환경 변수 확인

### 디버깅

```bash
# DEBUG 레벨 로그 활성화
LOG_LEVEL=DEBUG python -m csa.cli.main analyze --all-objects

# 로그 파일 확인
tail -f logs/csa.log
```

### 데이터베이스 초기화

```bash
# Neo4j 브라우저에서 모든 노드 삭제
MATCH (n) DETACH DELETE n

# 전체 재분석
python -m csa.cli.main analyze --all-objects --clean --project-name myproject
```

## 확장 가능성

새로운 기능 추가 시 다음 패턴을 따르세요:

- **새 파서**: `csa/parsers/` 아래 추가
- **새 분석 서비스**: `csa/services/` 아래 기능별로 추가
- **새 CLI 명령어**: `csa/cli/commands/` 아래 추가 후 `main.py`에 등록
- **새 Neo4j 노드**: `csa/models/graph_entities.py`에 Pydantic 모델 추가
- **새 그래프 작업**: `csa/services/graph_db/` 아래 적절한 모듈에 추가
