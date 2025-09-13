# Java Code Analyzer

This project is a Python-based tool for analyzing Java source code and visualizing the class relationships as a graph in a Neo4j database.

## Features

- Parses Java projects to identify classes, properties, and method calls.
- Stores the code structure in a Neo4j graph database.
- Provides a CLI for triggering the analysis.

## Project Structure

- `src/`: Contains the main source code.
    - `cli/`: Command-line interface 정의.
    - `models/`: 그래프 엔티티(예: 클래스, 메서드)를 위한 데이터 모델.
    - `services/`: Java 파싱(`java_parser.py`) 및 Neo4j 상호작용(`graph_db.py`)을 위한 핵심 로직.
- `tests/`: 단위, 통합 및 계약 테스트.
    - `sample_java_project/`: 테스트에 사용되는 샘플 Java 파일.
- `specs/`: 프로젝트 사양 및 문서.

## Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd <repository_directory>
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Usage

Java 프로젝트를 분석하려면 `analyze` 명령어를 사용하세요. Java 소스 폴더와 Neo4j 연결 세부 정보를 지정할 수 있습니다. Neo4j 자격 증명은 환경 변수(`NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`)로 설정하거나 옵션으로 전달하는 것이 좋습니다.

```bash
python -m src.cli.main analyze --java-source-folder /path/to/your/java/project --neo4j-password <your_password>
```

**옵션:**

- `--java-source-folder <path>`: Java 소스 프로젝트 폴더 경로. (`JAVA_SOURCE_FOLDER` 환경 변수를 통해서도 설정 가능).
- `--neo4j-uri <uri>`: Neo4j URI (기본값: `bolt://localhost:7687`). (`NEO4J_URI` 환경 변수를 통해서도 설정 가능).
- `--neo4j-user <username>`: Neo4j 사용자 이름 (기본값: `neo4j`). (`NEO4J_USER` 환경 변수를 통해서도 설정 가능).
- `--neo4j-password <password>`: Neo4j 비밀번호. (`NEO4J_PASSWORD` 환경 변수를 통해서도 설정 가능).
- `--clean`: 분석 전에 데이터베이스를 초기화합니다.

**데이터베이스 초기화 예시:**

```bash
python -m src.cli.main analyze --java-source-folder /path/to/your/java/project --clean
```

더 자세한 지침 및 예시는 [Quickstart Guide](./specs/001-java-class-properyties/quickstart.md)를 참조하십시오.

## Testing

프로젝트 테스트를 실행하려면 `pytest`를 사용하십시오.

```bash
pytest
```