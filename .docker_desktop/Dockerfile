# Python Dev Container (Debian 기반)
FROM mcr.microsoft.com/devcontainers/python:3.12

# timezone 설정
RUN ln -sf /usr/share/zoneinfo/Asia/Seoul /etc/localtime && echo "Asia/Seoul" > /etc/timezone

# --- 1. 스크립트 파일 복사 (가독성 및 유지보수성 향상) ---
# postCreateCommand에서 사용할 스크립트를 미리 복사합니다.
COPY .docker_desktop/scripts/ensure-plantuml-into-workspace /usr/local/bin/ensure-plantuml-into-workspace
RUN chmod +x /usr/local/bin/ensure-plantuml-into-workspace

# --- 2. 패키지 설치 (레이어 캐싱 및 용량 최적화) ---
# apt, npm, curl 등 여러 단계의 설치 과정을 하나의 RUN 블록으로 통합합니다.
RUN apt-get update \
    # Neo4j GPG 키 및 저장소 추가
    && apt-get install -y --no-install-recommends gnupg wget ca-certificates \
    && wget -O - https://debian.neo4j.com/neotechnology.gpg.key | gpg --dearmor > /usr/share/keyrings/neo4j.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/neo4j.gpg] https://debian.neo4j.com stable 5" > /etc/apt/sources.list.d/neo4j.list \
    # 필요한 패키지 설치
    && apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl \
        nodejs \
        npm \
        openjdk-21-jdk-headless \
        graphviz \
        cypher-shell \
    # npm 글로벌 패키지 설치
    && npm install -g @mermaid-js/mermaid-cli \
    # PlantUML JAR 다운로드
    && mkdir -p /opt/plantuml \
    && curl -L "https://github.com/plantuml/plantuml/releases/latest/download/plantuml.jar" -o /opt/plantuml/plantuml.jar \
    # 불필요한 캐시 및 파일 정리 (이미지 용량 최적화)
    && npm cache clean --force \
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ------------------------------------------------------------
# ENV
# ------------------------------------------------------------
ENV JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64
ENV PATH="${JAVA_HOME}/bin:${PATH}"
ENV PLANTUML_JAR_PATH=/working/csaadm/libs/plantuml.jar
ENV MMDC_PATH=/usr/local/bin/mmdc

# Python 가상환경 자동 활성화 설정
RUN echo 'if [ -f /working/csaadm/.venv/bin/activate ]; then' >> /home/vscode/.bashrc \
 && echo '    source /working/csaadm/.venv/bin/activate' >> /home/vscode/.bashrc \
 && echo '    echo "[venv] Python virtual environment activated"' >> /home/vscode/.bashrc \
 && echo 'fi' >> /home/vscode/.bashrc

WORKDIR /working/csaadm