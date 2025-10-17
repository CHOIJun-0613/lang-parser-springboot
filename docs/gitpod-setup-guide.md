# Gitpod 환경 설정 가이드

> 작성일: 2025-10-17
> 프로젝트: lang-parser-springboot
> 환경 ID: 0199ec15-59d3-7e92-8e22-8cb6c7ba4df7

## 목차

1. [Dev Container 설정](#dev-container-설정)
2. [Neo4j 설정](#neo4j-설정)
3. [Gitpod CLI 설치 (Windows)](#gitpod-cli-설치-windows)
4. [SSH 접속](#ssh-접속)
5. [포트 포워딩](#포트-포워딩)
6. [Neo4j 확인 쿼리](#neo4j-확인-쿼리)
7. [문제 해결](#문제-해결)

---

## Dev Container 설정

### 자동 설정 항목

Dev Container 빌드 시 자동으로 실행되는 작업:

1. Python 가상환경 생성 (`/workspace/.venv`)
2. Python 패키지 설치 (`requirements.txt`)
3. Claude Code CLI 설치
4. Codex CLI 설치
5. 가상환경 자동 활성화

### 설정 파일

#### `.devcontainer/devcontainer.json`

```json
{
  "name": "CSA Dev Container",
  "dockerComposeFile": "docker-compose.yml",
  "service": "app",
  "workspaceFolder": "/workspace",
  "postCreateCommand": "bash -c 'set -e && echo \"[setup] Starting dev environment setup...\" && /usr/local/bin/ensure-plantuml-into-workspace && echo \"[setup] Creating Python virtual environment...\" && python -m venv /workspace/.venv && echo \"[setup] Installing Python packages...\" && /workspace/.venv/bin/pip install --upgrade pip && /workspace/.venv/bin/pip install -r /workspace/requirements.txt && echo \"[setup] Installing Claude Code CLI...\" && sudo npm install -g @anthropic-ai/claude-code && echo \"[setup] Installing Codex CLI...\" && sudo npm install -g @openai/codex && echo \"[setup] Dev environment setup complete!\"'",
  "forwardPorts": [13000, 7474, 7687],
  "customizations": {
    "vscode": {
      "extensions": [
        "ms-python.python",
        "ms-azuretools.vscode-docker",
        "neo4j.neo4j-extension"
      ]
    }
  },
  "remoteUser": "vscode"
}
```

#### `.devcontainer/Dockerfile`

가상환경 자동 활성화 설정:

```dockerfile
# Python 가상환경 자동 활성화 설정
RUN echo 'if [ -f /workspace/.venv/bin/activate ]; then' >> /home/vscode/.bashrc \
 && echo '    source /workspace/.venv/bin/activate' >> /home/vscode/.bashrc \
 && echo '    echo "[venv] Python virtual environment activated"' >> /home/vscode/.bashrc \
 && echo 'fi' >> /home/vscode/.bashrc
```

### Dev Container 재빌드

```bash
# Gitpod CLI 사용
gitpod environment devcontainer rebuild 0199ec15-59d3-7e92-8e22-8cb6c7ba4df7

# 로그 확인
gitpod environment devcontainer logs 0199ec15-59d3-7e92-8e22-8cb6c7ba4df7
```

---

## Neo4j 설정

### 연결 정보

```
URI: bolt://localhost:7687
Database: csadb01
Users:
  - neo4j / neo4j-temp (관리자)
  - csauser / csauser123 (애플리케이션 사용자)
```

### 설정 파일

#### `neo4j/conf/neo4j.conf`

```ini
# Neo4j Configuration File
# Neo4j 5.x Community Edition

# Network Settings
server.default_listen_address=0.0.0.0
server.bolt.enabled=true
server.bolt.listen_address=0.0.0.0:7687
server.http.enabled=true
server.http.listen_address=0.0.0.0:7474

# Database Settings
initial.dbms.default_database=csadb01

# Memory Settings
server.memory.heap.initial_size=512m
server.memory.heap.max_size=1g

# Security Settings
dbms.security.procedures.unrestricted=apoc.*
```

#### `neo4j/init.system.cypher`

```cypher
// Community Edition 호환 사용자 생성
DROP USER csauser IF EXISTS;

CREATE USER csauser
  SET PASSWORD 'csauser123'
  CHANGE NOT REQUIRED;
```

### Neo4j 접속 방법

#### cypher-shell (터미널)

```bash
# neo4j 사용자
cypher-shell -a bolt://localhost:7687 -u neo4j -p neo4j-temp

# csauser
cypher-shell -a bolt://localhost:7687 -u csauser -p csauser123 -d csadb01
```

#### VSCode Neo4j Extension

```
URL: bolt://localhost:7687
Username: csauser
Password: csauser123
Database: csadb01
```

---

## Gitpod CLI 설치 (Windows)

### PowerShell 스크립트 설치

```powershell
# 관리자 권한 PowerShell
irm https://gitpod.io/install.ps1 | iex
```

### 수동 설치

```powershell
# 1. 다운로드 디렉토리 생성
New-Item -ItemType Directory -Force -Path "$env:LOCALAPPDATA\gitpod"

# 2. 최신 버전 다운로드
$ProgressPreference = 'SilentlyContinue'
Invoke-WebRequest -Uri "https://github.com/gitpod-io/gitpod/releases/latest/download/gitpod-windows-amd64.exe" -OutFile "$env:LOCALAPPDATA\gitpod\gitpod.exe"

# 3. PATH에 추가
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$env:LOCALAPPDATA\gitpod*") {
    [Environment]::SetEnvironmentVariable("Path", "$userPath;$env:LOCALAPPDATA\gitpod", "User")
}

# 4. 현재 세션에 PATH 적용
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
```

### 로그인

```powershell
# Gitpod 로그인
gitpod login

# 로그인 확인
gitpod context list
```

---

## SSH 접속

### 기본 접속

```powershell
# Windows PowerShell
gitpod environment ssh 0199ec15-59d3-7e92-8e22-8cb6c7ba4df7
```

### SSH Config 설정

`C:\Users\<사용자명>\.ssh\config`:

```ssh-config
# Gitpod SSH Configuration

Host gitpod-lang-parser
    HostName 0199ec15-59d3-7e92-8e22-8cb6c7ba4df7.gitpod.environment
    User gitpod_devcontainer
    ProxyCommand gitpod environment ssh %h --proxy-connect --user %r
    StrictHostKeyChecking no
    UserKnownHostsFile NUL
    LogLevel ERROR

Host *.gitpod.environment
    User gitpod_devcontainer
    ProxyCommand gitpod environment ssh %h --proxy-connect --user %r
    StrictHostKeyChecking no
    UserKnownHostsFile NUL
    LogLevel ERROR
```

접속:

```powershell
ssh gitpod-lang-parser
```

---

## 포트 포워딩

### 포트 목록 확인

```bash
gitpod environment port list
```

**출력 예시:**
```
PORT  NAME               URL
1455  Codex 인증포트      https://1455--0199ec15-59d3-7e92-8e22-8cb6c7ba4df7.us-east-1-01.gitpod.dev
7474  Neo4J Browser Port https://7474--0199ec15-59d3-7e92-8e22-8cb6c7ba4df7.us-east-1-01.gitpod.dev
7687  Neo4J Open Port    https://7687--0199ec15-59d3-7e92-8e22-8cb6c7ba4df7.us-east-1-01.gitpod.dev
```

### 로컬 포트 포워딩

```powershell
# 단일 포트
gitpod environment ssh 0199ec15-59d3-7e92-8e22-8cb6c7ba4df7 -- -L 1455:localhost:1455

# 여러 포트
gitpod environment ssh 0199ec15-59d3-7e92-8e22-8cb6c7ba4df7 -- -L 1455:localhost:1455 -L 7474:localhost:7474 -L 7687:localhost:7687

# 백그라운드 (명령 실행 없이)
gitpod environment ssh 0199ec15-59d3-7e92-8e22-8cb6c7ba4df7 -- -L 1455:localhost:1455 -N
```

### Gitpod URL 직접 사용 (권장)

포트 포워딩 없이 Gitpod URL 직접 사용:

```
https://1455--0199ec15-59d3-7e92-8e22-8cb6c7ba4df7.us-east-1-01.gitpod.dev
https://7474--0199ec15-59d3-7e92-8e22-8cb6c7ba4df7.us-east-1-01.gitpod.dev
https://7687--0199ec15-59d3-7e92-8e22-8cb6c7ba4df7.us-east-1-01.gitpod.dev
```

---

## Neo4j 확인 쿼리

### 1. 데이터베이스 확인

```cypher
SHOW DATABASES;
```

**확인 포인트:**
- `name`: "csadb01"
- `default`: TRUE
- `currentStatus`: "online"

### 2. 사용자 확인

```cypher
-- system 데이터베이스에서 실행
SHOW USERS;
```

**실행 예제:**
```bash
cypher-shell -a bolt://localhost:7687 -u neo4j -p neo4j-temp -d system "SHOW USERS;"
```

### 3. 노드 현황 조회

```cypher
-- 노드 타입별 개수
MATCH (n)
RETURN labels(n) as NodeType, count(n) as Count
ORDER BY Count DESC;
```

**실행 예제:**
```bash
cypher-shell -a bolt://localhost:7687 -u csauser -p csauser123 -d csadb01 \
  "MATCH (n) RETURN labels(n) as NodeType, count(n) as Count ORDER BY Count DESC;"
```

### 4. 관계 현황 조회

```cypher
-- 관계 타입별 개수
MATCH ()-[r]->()
RETURN type(r) as RelationType, count(r) as Count
ORDER BY Count DESC
LIMIT 20;
```

**실행 예제:**
```bash
cypher-shell -a bolt://localhost:7687 -u csauser -p csauser123 -d csadb01 \
  "MATCH ()-[r]->() RETURN type(r) as RelationType, count(r) as Count ORDER BY Count DESC LIMIT 20;"
```

### 5. 전체 통계

```cypher
-- 노드와 관계 전체 개수
MATCH (n)
WITH count(n) as NodeCount
MATCH ()-[r]->()
RETURN NodeCount, count(r) as RelationshipCount;
```

### 6. 빠른 확인 스크립트

```bash
#!/bin/bash
echo "=== 1. 데이터베이스 확인 ==="
cypher-shell -a bolt://localhost:7687 -u neo4j -p neo4j-temp "SHOW DATABASES;"

echo -e "\n=== 2. 사용자 확인 ==="
cypher-shell -a bolt://localhost:7687 -u neo4j -p neo4j-temp -d system "SHOW USERS;"

echo -e "\n=== 3. 노드 현황 ==="
cypher-shell -a bolt://localhost:7687 -u csauser -p csauser123 -d csadb01 \
  "MATCH (n) RETURN labels(n) as NodeType, count(n) as Count ORDER BY Count DESC LIMIT 10;"

echo -e "\n=== 4. 관계 현황 ==="
cypher-shell -a bolt://localhost:7687 -u csauser -p csauser123 -d csadb01 \
  "MATCH ()-[r]->() RETURN type(r) as RelationType, count(r) as Count ORDER BY Count DESC LIMIT 10;"

echo -e "\n=== 5. 전체 통계 ==="
cypher-shell -a bolt://localhost:7687 -u csauser -p csauser123 -d csadb01 \
  "MATCH (n) WITH count(n) as NodeCount MATCH ()-[r]->() RETURN NodeCount, count(r) as RelationshipCount;"
```

---

## 문제 해결

### Neo4j 컨테이너 unhealthy

**증상:**
```
Container lang-parser-springboot_devcontainer-neo4j-1 Error
dependency failed to start: container is unhealthy
```

**해결 방법:**

1. **Neo4j 데이터 초기화:**
   ```bash
   rm -rf /workspace/neo4j/data/*
   ```

2. **healthcheck 수정:**
   - cypher-shell 대신 HTTP 기반 healthcheck 사용
   - `.devcontainer/docker-compose.yml`:
     ```yaml
     healthcheck:
       test: ["CMD-SHELL", "wget --no-verbose --tries=1 --spider http://localhost:7474 || exit 1"]
       interval: 10s
       timeout: 10s
       retries: 30
       start_period: 40s
     ```

3. **Dev Container 재빌드:**
   ```bash
   gitpod environment devcontainer rebuild 0199ec15-59d3-7e92-8e22-8cb6c7ba4df7
   ```

### SSH 포트 포워딩 권한 오류

**증상:**
```
Error: cannot push key to environment: permission_denied: SSH key update permission denied
```

**해결 방법:**

Gitpod 환경 **내부**가 아닌 **로컬 PC의 PowerShell**에서 실행:

```powershell
# Windows PowerShell (로컬 PC)
gitpod environment ssh 0199ec15-59d3-7e92-8e22-8cb6c7ba4df7 -- -L 1455:localhost:1455
```

### SSH Config 오류

**증상:**
```
C:\Users\06433/.ssh/config line 1: no argument after keyword
```

**해결 방법:**

SSH Config 파일 수정:

```ssh-config
# 올바른 형식
Host gitpod-lang-parser
    HostName 0199ec15-59d3-7e92-8e22-8cb6c7ba4df7.gitpod.environment
    User gitpod_devcontainer
    ProxyCommand gitpod environment ssh %h --proxy-connect --user %r
    StrictHostKeyChecking no
```

---

## 주요 명령어 요약

### Gitpod 환경 관리

```bash
# 환경 목록
gitpod environment list

# 환경 시작
gitpod environment start <environment-id>

# 환경 중지
gitpod environment stop <environment-id>

# Dev Container 재빌드
gitpod environment devcontainer rebuild <environment-id>

# 로그 확인
gitpod environment devcontainer logs <environment-id>
```

### SSH 접속

```bash
# 기본 접속
gitpod environment ssh <environment-id>

# 포트 포워딩
gitpod environment ssh <environment-id> -- -L <local-port>:localhost:<remote-port>
```

### 포트 관리

```bash
# 포트 목록
gitpod environment port list

# 포트 공개
gitpod environment port open <port-number>

# 포트 닫기
gitpod environment port close <port-number>
```

### Neo4j

```bash
# 접속
cypher-shell -a bolt://localhost:7687 -u csauser -p csauser123 -d csadb01

# 데이터베이스 확인
cypher-shell -a bolt://localhost:7687 -u neo4j -p neo4j-temp "SHOW DATABASES;"

# 사용자 확인
cypher-shell -a bolt://localhost:7687 -u neo4j -p neo4j-temp -d system "SHOW USERS;"
```

---

## 참고 자료

- **Gitpod 공식 문서**: https://www.gitpod.io/docs
- **Gitpod CLI 문서**: https://www.gitpod.io/docs/references/gitpod-cli
- **Neo4j 공식 문서**: https://neo4j.com/docs/
- **프로젝트 README**: /workspace/README.md
- **CLAUDE.md**: /workspace/CLAUDE.md

---

## 환경 정보

```
프로젝트: lang-parser-springboot
환경 ID: 0199ec15-59d3-7e92-8e22-8cb6c7ba4df7
리포지토리: https://github.com/CHOIJun-0613/lang-parser-springboot.git
브랜치: main
리전: us-east-1-01.gitpod.dev
```

---

**작성일**: 2025-10-17  
**최종 업데이트**: 2025-10-17
