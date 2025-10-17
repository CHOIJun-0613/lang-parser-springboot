# Python Dev Container (Debian 기반)
FROM mcr.microsoft.com/devcontainers/python:3.12

# timezone 설정
RUN ln -sf /usr/share/zoneinfo/Asia/Seoul /etc/localtime && echo "Asia/Seoul" > /etc/timezone

# ------------------------------------------------------------
# 기본 유틸 + Node.js/npm + OpenJDK 21 + graphviz
# ------------------------------------------------------------
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y \
    curl \
    ca-certificates \
    nodejs \
    npm \
    openjdk-21-jdk-headless \
    graphviz \
    gnupg \
    wget \
 && rm -rf /var/lib/apt/lists/*

# ------------------------------------------------------------
# Mermaid CLI (mmdc)
# ------------------------------------------------------------
RUN npm install -g @mermaid-js/mermaid-cli

# ------------------------------------------------------------
# PlantUML JAR: /opt/plantuml/plantuml.jar (워크스페이스로 복사 유틸 제공)
# ------------------------------------------------------------
RUN mkdir -p /opt/plantuml \
 && curl -L "https://github.com/plantuml/plantuml/releases/latest/download/plantuml.jar" \
    -o /opt/plantuml/plantuml.jar

# 워크스페이스에 없으면 JAR 복사하는 헬퍼
RUN printf '%s\n' \
'#!/usr/bin/env bash' \
'set -euo pipefail' \
'TARGET="/workspace/libs/plantuml.jar"' \
'if [ ! -f "$TARGET" ]; then' \
'  mkdir -p "$(dirname "$TARGET")"' \
'  cp -f /opt/plantuml/plantuml.jar "$TARGET"' \
'  echo "[ensure-plantuml] Copied plantuml.jar -> $TARGET"' \
'else' \
'  echo "[ensure-plantuml] plantuml.jar already exists at $TARGET (skip copy)"' \
'fi' \
> /usr/local/bin/ensure-plantuml-into-workspace \
 && chmod +x /usr/local/bin/ensure-plantuml-into-workspace

# ------------------------------------------------------------
# cypher-shell 설치 (Neo4j 공식 APT repo)
# ------------------------------------------------------------
RUN wget -O - https://debian.neo4j.com/neotechnology.gpg.key | gpg --dearmor | tee /usr/share/keyrings/neo4j.gpg >/dev/null && \
    echo "deb [signed-by=/usr/share/keyrings/neo4j.gpg] https://debian.neo4j.com stable 5" > /etc/apt/sources.list.d/neo4j.list && \
    apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y cypher-shell && \
    rm -rf /var/lib/apt/lists/*

# ------------------------------------------------------------
# ENV
# ------------------------------------------------------------
ENV JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64
ENV PATH="${JAVA_HOME}/bin:${PATH}"
ENV PLANTUML_JAR_PATH=/workspace/libs/plantuml.jar
ENV MMDC_PATH=/usr/local/bin/mmdc

# Python 가상환경 자동 활성화 설정
RUN echo 'if [ -f /workspace/.venv/bin/activate ]; then' >> /home/vscode/.bashrc \
 && echo '    source /workspace/.venv/bin/activate' >> /home/vscode/.bashrc \
 && echo '    echo "[venv] Python virtual environment activated"' >> /home/vscode/.bashrc \
 && echo 'fi' >> /home/vscode/.bashrc

WORKDIR /workspace