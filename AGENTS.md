# CSA 프로젝트 에이전트 가이드

## 1. 프로젝트 한눈에 보기
- **목표**: Spring Boot 기반 Java 애플리케이션을 정적 분석하여 코드 구조, DB 연계, 호출 관계, 시퀀스 다이어그램을 자동으로 생성한다.
- **주요 산출물**: Neo4j 그래프 데이터, CRUD 매트릭스, DB 호출/영향도 리포트, Mermaid·PlantUML 시퀀스 다이어그램, 분석 요약 통계.
- **실행 진입점**: `python -m csa.cli.main <command>` 형태의 CLI.
- **분석 제외 디렉터리**: `.`으로 시작하는 폴더, `commands`, `logs`, `neo4j`, `src`, `target_src`.

## 2. 핵심 모듈 지도
- `csa/cli/main.py`: Click 기반 CLI 그룹. analyze / sequence / crud / db-analysis 명령을 등록한다.
- `csa/services/analysis/`
  - `handlers.py`: Java·DB 파이프라인 실행 및 Neo4j 초기화·정리·저장을 총괄한다.
  - `java_pipeline.py`: 배치와 스트리밍 파서를 전환하며 Java 분석 산출물을 수집한다.
  - `db_pipeline.py`: DDL 디렉터리를 순회해 Database/Table/Column/Constraint/Index 정보를 추출한다.
  - `neo4j_writer.py`: 프로젝트 노드부터 Bean, Endpoint, Mapper, SQL까지 Neo4j에 적재하고 통계를 계산한다.
  - `options.py`, `summary.py`: CLI 옵션 검증과 실행 요약, 시간/수량 통계를 담당한다.
- `csa/services/java_analysis/`
  - `project.py`: Lombok 보조, 내부 클래스 추출, 메소드/필드/어노테이션 분석 등 전체 트리를 파싱한다.
  - `spring.py`, `mybatis.py`, `jpa.py`, `config.py`, `tests.py`, `utils.py`: 프레임워크별 어노테이션 파싱과 SQL 추적, 테스트 감지.
  - `bean_dependency_resolver.py`: Neo4j 데이터를 기반으로 Bean 의존관계를 재구성한다.
- `csa/services/db_call_analysis/`: Neo4j에 저장된 Method↔SQL 관계로 CRUD 매트릭스, 영향도 분석, 호출 체인 다이어그램을 생성한다.
- `csa/services/graph_db/`: GraphDB 파사드. 프로젝트/애플리케이션/DB/분석/유지보수 믹스를 조합해 Neo4j CRUD와 통계 쿼리를 제공한다.
- `csa/models/`: `analysis.py`의 Pydantic 통계 모델과 `graph_entities.py`의 Neo4j 노드 모델을 정의한다.
- `csa/utils/logger.py`: 명령별 로그 파일을 생성하고 7일 이전 로그를 정리한다.
- `tests/`: 단위·통합·계약 테스트와 Spring 샘플 프로젝트를 포함한다.

## 3. 분석 파이프라인 흐름
1. **옵션 처리**: `validate_analyze_options()`로 실행 모드 결정, DB 스크립트 경로 확인.
2. **Neo4j 준비**: `GraphDB` 연결. `--clean` 옵션에 따라 Java/DB 노드를 초기화한다.
3. **DB 분석(선택)**: `DBParser.parse_ddl_directory()`가 DDL을 구조화하고, 테이블·컬럼·인덱스·제약 정보를 Neo4j에 저장한다.
4. **Java 분석**
   - *배치 모드*: `parse_java_project_full()`이 패키지, 클래스, Bean, 엔드포인트, Mapper, JPA 엔티티 등을 수집한다.
   - *스트리밍 모드*: `parse_java_project_streaming()`이 파일 단위로 Neo4j를 갱신해 메모리 사용량을 줄인다.
5. **Neo4j 저장**: `save_java_objects_to_neo4j()`가 프로젝트 노드를 만들고 각종 Spring/JPA/MyBatis 객체와 SQL 문을 기록한다.
6. **후처리**: `resolve_bean_dependencies_from_neo4j()`가 Bean 의존성을 보강하고, `print_analysis_summary()`가 실행 통계를 출력한다.

## 4. 주요 CLI 명령
- `analyze`: Java/DB 전체 혹은 부분 분석. `--java-object`, `--db-object`, `--all-objects`, `--class-name`, `--update`, `--dry-run`, `--concurrent`, `--workers` 옵션 지원.
- `db-analysis`, `db-statistics`, `db-call-chain`, `db-call-diagram`: Method↔SQL 관계를 기반으로 통계, 호출 체인, 다이어그램을 생성한다.
- `crud matrix` 계열: 테이블/클래스 기준 CRUD 매트릭스와 교차표를 출력한다.
- `sequence`: PlantUML/Mermaid 시퀀스 다이어그램을 생성하고 필요 시 이미지로 변환한다.

## 5. 데이터 모델 및 스토리지
- **Pydantic 통계 모델**: `JavaAnalysisStats`, `DatabaseAnalysisStats`, `AnalysisResult`가 분석 결과를 정형화한다.
- **Neo4j 노드 모델**: `graph_entities.py`에서 `Project`, `Package`, `Class`, `Method`, `Field`, `Bean`, `Endpoint`, `SqlStatement` 등을 정의한다.
- **GraphDB 믹스인**
  - `ProjectMixin`: 프로젝트·패키지·클래스 노드 생성 및 병렬 삽입 지원.
  - `PersistenceMixin`: Bean, Endpoint, Mapper, JPA 엔티티, SQL 문을 저장한다.
  - `DatabaseMixin`: Database/Table/Column/Index/Constraint 노드를 관리한다.
  - `AnalyticsMixin`: SQL 통계, 테이블 사용량, 복잡도 분석 쿼리를 제공한다.
  - `MaintenanceMixin`: 노드 정리와 관계 재구성 API를 제공한다.

## 6. 협업 및 구현 지침
- **코딩 규칙**: PEP 8, 타입 힌트, 함수 100줄 이하, 한국어 주석 선호, 파일 1000줄 이하 유지.
- **환경 변수**: `.env`(`NEO4J_*`, `JAVA_SOURCE_FOLDER`, `DB_SCRIPT_FOLDER`, 출력 경로 등)로 주입.
- **로깅**: `set_command_context()`로 명령명을 지정하면 `logs/{command}-YYYYMMDD.log`가 생성된다.
- **테스트**: `pytest` 활용. `tests/unit`, `tests/integration`, `tests/contract`로 분리되어 있으며 샘플 Spring 프로젝트(`tests/sample_*`) 제공.
- **보안**: 비밀번호 등 민감 정보는 커밋 금지, `env.example`에는 기본값만 기재.

## 7. 작업 절차 체크리스트
1. `.venv`를 활성화하고 `pip install -r requirements.txt`로 의존성을 설치한다.  
2. `.env`에 Neo4j 접속 정보와 `JAVA_SOURCE_FOLDER`, 출력 디렉터리를 설정한다.  
3. 분석 시 `python -m csa.cli.main analyze --all-objects --clean --project-name <별칭>` 실행을 권장한다.  
4. Neo4j Browser와 CRUD 매트릭스, 시퀀스 다이어그램 결과를 검증한다.  
5. 추가 보고가 필요하면 `db-call-chain`, `db-statistics` 명령으로 문서 또는 이미지를 생성한다.

## 8. 주의 및 베스트 프랙티스
- 스트리밍 모드(`USE_STREAMING_PARSE=true`)는 대규모 프로젝트에 유리하지만 Neo4j 연결이 필수다.
- CRUD 매트릭스는 SQL 파싱 결과(테이블 JSON)가 정확해야 하므로 MyBatis/JPA 매핑 오류를 먼저 해결한다.
- 기존 Neo4j 데이터를 보존하려면 `--clean`을 생략하거나 다른 프로젝트명을 사용한다.
- 로그와 산출물은 `.gitignore` 처리되어 있으므로 공유용 파일은 별도로 복사해 관리한다.
