# .devcontainer/Dockerfile
FROM mcr.microsoft.com/devcontainers/python:3.12

# Node.js + Java (PlantUML, Mermaid CLI용)
RUN apt-get update && apt-get install -y \
    curl \
    openjdk-21-jre-headless \
    npm \
 && rm -rf /var/lib/apt/lists/*

# Mermaid CLI 설치
RUN npm install -g @mermaid-js/mermaid-cli

# PlantUML JAR 다운로드 (lang-java-springboot/libs 폴더에 저장)
RUN mkdir -p /workspace/lang-java-springboot/libs \
 && curl -L https://github.com/plantuml/plantuml/releases/latest/download/plantuml.jar \
    -o /workspace/lang-java-springboot/libs/plantuml.jar

# 환경 변수 설정
ENV PLANTUML_JAR_PATH=/workspace/lang-java-springboot/libs/plantuml.jar
ENV MMDC_PATH=/usr/local/bin/mmdc

WORKDIR /workspace
