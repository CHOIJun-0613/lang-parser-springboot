# Java Code Analyzer

This project is a Python-based tool for analyzing Java source code and visualizing the class relationships as a graph in a Neo4j database.

## Features

- Parses Java projects to identify classes, properties, and method calls.
- Stores the code structure in a Neo4j graph database.
- Provides a CLI for triggering the analysis.
- **NEW**: Generates sequence diagrams showing method call relationships.
- **NEW**: Interactive class and method exploration tools.

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

## Sequence Diagram Generation

Java 코드 분석 후, 특정 클래스의 메서드 호출 관계를 시각화하는 sequence diagram을 생성할 수 있습니다.

**주의**: Sequence diagram 기능을 사용하기 전에 `.env` 파일에 Neo4j 접속 정보를 설정해야 합니다.

```bash
# .env 파일 예시
NEO4J_URI=neo4j://127.0.0.1:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
```

### 사용 가능한 클래스 목록 보기

```bash
python -m src.cli.main list-classes
```

### 특정 클래스의 메서드 목록 보기

```bash
python -m src.cli.main list-methods --class-name <class_name>
```

### Sequence Diagram 생성

특정 클래스의 모든 메서드에 대한 sequence diagram 생성:

```bash
python -m src.cli.main sequence --class-name <class_name>
```

특정 메서드에 대한 sequence diagram 생성:

```bash
python -m src.cli.main sequence --class-name <class_name> --method-name <method_name>
```

메서드 중심의 간단한 sequence diagram 생성 (직접 호출만 표시):

```bash
python -m src.cli.main sequence --class-name <class_name> --method-name <method_name> --method-focused
```

파일로 저장:

```bash
python -m src.cli.main sequence --class-name <class_name> --output-file diagram.md
```

외부 라이브러리 호출 포함:

```bash
python -m src.cli.main sequence --class-name <class_name> --include-external
```

호출 체인 깊이 제한:

```bash
python -m src.cli.main sequence --class-name <class_name> --max-depth 5
```

### 이미지로 변환

Mermaid 다이어그램을 이미지 파일로 변환:

```bash
# PNG 이미지로 변환
python -m src.cli.main sequence --class-name <class_name> --output-image diagram.png

# SVG 이미지로 변환 (벡터, 확대해도 깨지지 않음)
python -m src.cli.main sequence --class-name <class_name> --output-image diagram.svg --image-format svg

# PDF로 변환
python -m src.cli.main sequence --class-name <class_name> --output-image diagram.pdf --image-format pdf

# 고해상도 이미지 생성
python -m src.cli.main sequence --class-name <class_name> --output-image diagram.png --image-width 2000 --image-height 1500
```

**주의**: 이미지 변환을 위해서는 `mermaid-cli`가 설치되어 있어야 합니다:
```bash
npm install -g @mermaid-js/mermaid-cli
```

**옵션:**

- `--class-name <name>`: 분석할 클래스 이름 (필수)
- `--method-name <name>`: 특정 메서드 분석 (선택사항)
- `--max-depth <number>`: 호출 체인 최대 깊이 (기본값: 3)
- `--include-external`: 외부 라이브러리 호출 포함
- `--method-focused`: 메서드 중심 모드 (직접 호출만 표시, --method-name과 함께 사용)
- `--output-file <path>`: 다이어그램을 파일로 저장
- `--output-image <path>`: 이미지 파일로 변환 (PNG/SVG/PDF)
- `--image-format <format>`: 이미지 형식 (png, svg, pdf, 기본값: png)
- `--image-width <width>`: 이미지 너비 (기본값: 1200)
- `--image-height <height>`: 이미지 높이 (기본값: 800)

## Testing

프로젝트 테스트를 실행하려면 `pytest`를 사용하십시오.

```bash
pytest
```