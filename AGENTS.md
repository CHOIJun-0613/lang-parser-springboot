# Repository Guidelines

## 프로젝트 구조 및 모듈 구성
- `csa/cli/main.py`가 CLI 진입점을 제공하고, `csa/services/`는 Java·SQL 분석, Neo4j 갱신, 다이어그램 생성을 담당하는 서비스 모듈을 담고 있습니다.
- Java 분석 서비스는 `csa/services/analysis/`(분석 오케스트레이션)와 `csa/services/java_analysis/`(파싱 세부 모듈)로 기능별 분리되어 있으니, 새로운 기능도 해당 구조를 따라 배치하세요. 주요 하위 모듈은 `project.py`, `utils.py`, `spring.py`, `mybatis.py`, `jpa.py`, `config.py`, `tests.py`입니다.
- 도메인 모델은 `csa/models/`, 공용 헬퍼는 `csa/utils/`, 규칙 정의는 `csa/rules/`에 위치하니 새로운 기능도 동일한 패턴으로 배치하세요.
- neo4j Object의 모델 정보는 ./csa/models/graph_entities.py를 참조할 것
- 테스트는 `tests/unit`, `tests/integration`, `tests/contract`로 구분되어 있으며, 파서용 샘플 프로젝트는 `tests/sample_*` 아래에 있습니다. 배치 스크립트는 `commands/`, 참고 문서는 `docs/`, 생성물은 `.gitignore` 처리된 `output/`에 저장합니다.

## 빌드·테스트·개발 명령
- 초기 설정은 `python -m venv .venv`로 가상 환경을 만들고 활성화한 뒤 `pip install -r requirements.txt`를 실행합니다.
- `env.example`을 복사해 `.env`를 만들고 `NEO4J_*`, `JAVA_SOURCE_FOLDER`, 출력 경로를 채운 후 분석기를 실행합니다.
- 전체 재분석은 `python -m csa.cli.main analyze --all-objects --clean --project-name <alias>`로 수행하고, 시퀀스 다이어그램은 `python -m csa.cli.main sequence --class-name <Class> --format plantuml`로 다시 생성할 수 있습니다.
- 테스트는 `pytest`로 수행하며, 집중 테스트 시 `pytest tests/unit` 또는 `pytest tests/integration -k end_to_end`처럼 범위를 줄입니다.

## 코딩 스타일 및 네이밍
- PEP 8(4칸 들여쓰기, snake_case 함수·모듈, PascalCase 클래스)을 지키고, 기존과 어울리는 간결한 독스트링을 유지합니다. 공용 유틸을 수정할 때는 기존의 한·영 혼용 노트를 존중하세요.
- 명시적 타입 힌트와 pydantic 모델을 적극 활용하고, 전역 대신 헬퍼를 통해 의존성을 주입합니다. 로깅은 `csa.utils.logger.get_logger()`를 재사용합니다.
- 환경 변수는 `.env`와 헬퍼를 통해 주입하며, 서비스나 CLI 계층에 경로나 자격 증명을 하드코딩하지 않습니다.

## 테스트 가이드
- python  프로그램을 실행할 때는 반드시 가상환경에서 실행시킬 것
  > 명령어; .venv\Scripts\activate 또든 runvenv.bat
- debug나 임시 test 소스를 생성할 때는 ./test 폴더에 생성하고 테스트할 것
- neo4j 접속해서 쿼리를 수행할 경우 아래 정보를 사용할 것
  > NEO4J_URI=neo4j://127.0.0.1:7687
  > NEO4J_DATABASE=csadb01
  > NEO4J_USER=csauser
  > NEO4J_PASSWORD=csauser123

## 환경 및 보안 유의 사항
- 비밀 값은 절대 커밋하지 말고 `env.example`에 기본값만 남기며, 민감한 값은 승인된 채널로 공유합니다.
- Neo4j 스키마 변경은 `docs/`의 SQL 파일로 버전 관리하고, 적용한 스크립트를 PR 설명에 언급해 추적성을 확보합니다.

## 행동 지침
- 모든 답변은 한국어로 공손하게 할 것
- 임의로 어플리케이션 구조를 변경하지 말 것
- 항상 면저 생각하고, 영향도를 판단한 후, 수정 반영 여부를 내게 확인하고 수정할 것
- 수정 후 수정 이유와 수정 사항을 텍스트로 보여줄 것

## 함수 모듈화 지침
- 함수는 개발과 유지보수의 효율성을 위해 모듈화할 것
- 하나의 함수는 가능한 한 100줄 이내로 유지할 것

## 소스코드 파일 작성 지침
- 하나의 소스코드는 가능한 한 1000줄 이내로 유지할 것
- 하나의 소스코드 파일이 1000줄을 초과하면 다른 코드 파일로 분리하고 분리된 파일의 함수를 import해서 사용할 것 
