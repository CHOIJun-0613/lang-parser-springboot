# .devcontainer/Dockerfile
FROM mcr.microsoft.com/devcontainers/python:3.12

# ------------------------------------------------------------
# System deps: curl, ca-certs, Node.js + npm, JDK 21 (headless), optional utils
#   - Debian 기반 devcontainer 이미지이므로 openjdk-21-* 패키지 사용
#   - Mermaid CLI는 Node.js 필요
#   - graphviz는 PlantUML 일부 다이어그램에서 유용
# ------------------------------------------------------------
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y \
    curl \
    ca-certificates \
    nodejs \
    npm \
    openjdk-21-jdk-headless \
    graphviz \
    && rm -rf /var/lib/apt/lists/*

# ------------------------------------------------------------
# Mermaid CLI (mmdc) - 전역 설치
# ------------------------------------------------------------
RUN npm install -g @mermaid-js/mermaid-cli

# ------------------------------------------------------------
# PlantUML JAR - 이미지 내부 보관 위치(/opt/plantuml)
#   - 실제 워크스페이스 마운트 시 /workspace 아래는 오버레이되므로
#     /opt에 저장해두고, post-create 시 워크스페이스로 복사하는 스크립트 제공
# ------------------------------------------------------------
RUN mkdir -p /opt/plantuml \
 && curl -L "https://github.com/plantuml/plantuml/releases/latest/download/plantuml.jar" \
    -o /opt/plantuml/plantuml.jar

# ------------------------------------------------------------
# Helper: 워크스페이스에 JAR가 없으면 자동 복사하는 스크립트
#   - devcontainer.json의 postCreateCommand에서 호출하면 됨:
#     if [ ! -f ../.env ]; then cp ../.env.example ../.env; fi && \
#     /usr/local/bin/ensure-plantuml-into-workspace && \
#     pip install -r requirements.txt
# ------------------------------------------------------------
RUN printf '%s\n' \
'#!/usr/bin/env bash' \
'set -euo pipefail' \
'TARGET="/workspace/lang-java-springboot/libs/plantuml.jar"' \
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
# ENV: Java / PlantUML / Mermaid CLI 경로
#   - JAVA_HOME은 Debian OpenJDK 21 기본 경로
#   - PLANTUML_JAR_PATH는 프로젝트 내부 경로(요청 경로)로 설정
#   - MMDC_PATH는 Mermaid CLI 바이너리 경로
# ------------------------------------------------------------
ENV JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64
ENV PATH="${JAVA_HOME}/bin:${PATH}"
ENV PLANTUML_JAR_PATH=/workspace/lang-java-springboot/libs/plantuml.jar
ENV MMDC_PATH=/usr/local/bin/mmdc

# 작업 디렉토리
WORKDIR /workspace
