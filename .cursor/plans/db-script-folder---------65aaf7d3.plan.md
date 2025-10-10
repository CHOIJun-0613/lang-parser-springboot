<!-- 65aaf7d3-1137-4cdb-aa1b-b5a2cd2d3b1d 528f91b3-d801-49e5-9589-901fa263992d -->
# Neo4j Database 연결 수정

## 문제 분석

### 1. GraphDB 클래스의 문제

**현재 코드 (graph_db.py:13-15):**

```python
def __init__(self, uri, user, password):
    """Initializes the database driver."""
    self._driver: Driver = GraphDatabase.driver(uri, auth=(user, password))
```

**문제점:**

- `database` 매개변수를 받지 않음
- Driver 생성 시 데이터베이스 지정 안 함
- 세션 생성 시 기본 데이터베이스(`neo4j`) 사용

### 2. neo4j_connection_pool.py의 환경변수 로딩

**현재 코드 (160-166줄):**

```python
def initialize_pool_from_env() -> Neo4jConnectionPool:
    """환경 변수에서 설정을 읽어 Pool 초기화"""
    uri = os.getenv('NEO4J_URI')
    user = os.getenv('NEO4J_USER')
    password = os.getenv('NEO4J_PASSWORD')
    database = os.getenv('NEO4J_DATABASE', 'neo4j')
    pool_size = int(os.getenv('NEO4J_POOL_SIZE', '10'))
```

**문제점:**

- `load_dotenv()` 호출이 없음
- `.env` 파일의 환경변수를 읽지 못할 수 있음
- 하지만 `main.py`에서 이미 `load_dotenv()` 호출되므로 상관없음

## 수정 계획

### 1. GraphDB 클래스 수정 (csa/services/graph_db.py)

**수정 전:**

```python
def __init__(self, uri, user, password):
    """Initializes the database driver."""
    self._driver: Driver = GraphDatabase.driver(uri, auth=(user, password))
    self.logger = get_logger(__name__)
```

**수정 후:**

```python
def __init__(self, uri, user, password, database='neo4j'):
    """Initializes the database driver."""
    self._driver: Driver = GraphDatabase.driver(uri, auth=(user, password))
    self._database = database
    self.logger = get_logger(__name__)
```

### 2. GraphDB의 모든 세션 생성 부분 수정

**현재:**

```python
with self._driver.session() as session:
```

**수정 후:**

```python
with self._driver.session(database=self._database) as session:
```

이 패턴은 GraphDB 클래스의 모든 메서드에서 약 50여 곳에 적용되어야 합니다.

### 3. main.py에서 GraphDB 생성 시 database 전달

**analyze_project 함수 (2683줄):**

```python
# 수정 전
db = GraphDB(neo4j_uri, neo4j_user, neo4j_password)

# 수정 후
db = GraphDB(neo4j_uri, neo4j_user, neo4j_password, neo4j_database)
```

**기타 모든 GraphDB 생성 위치 수정:**

- 1889줄: `db = GraphDB(neo4j_uri, neo4j_user, neo4j_password)`
- 1970줄: `db = GraphDB(neo4j_uri, neo4j_user, neo4j_password)`
- 2050줄: `graph_db = GraphDB(neo4j_uri, neo4j_user, neo4j_password)`
- 2148줄: `graph_db = GraphDB(neo4j_uri, neo4j_user, neo4j_password)`
- 2281줄: `graph_db = GraphDB(neo4j_uri, neo4j_user, neo4j_password)`
- 2354줄: `graph_db = GraphDB(neo4j_uri, neo4j_user, neo4j_password)`
- 2451줄: `graph_db = GraphDB(neo4j_uri, neo4j_user, neo4j_password)`
- 2540줄: `graph_db = GraphDB(neo4j_uri, neo4j_user, neo4j_password)`

### 4. Connection Pool 사용 부분 (선택사항)

**765줄과 1747줄:**

```python
# 현재
db = GraphDB()  # Connection pool 사용

# 수정 필요 - database 정보 전달 방법 고려
```

## load_dotenv() 관련

**질문에 대한 답변:**

- `neo4j_connection_pool.py`에 `load_dotenv()`가 없지만 **상관없습니다**
- `main.py`의 최상단(22줄)에서 이미 `load_dotenv()` 호출됨
- Python 프로세스 전체에서 환경변수가 로드되므로 중복 호출 불필요
- 다만, 안전을 위해 추가해도 무방 (중복 호출은 문제없음)

## 우선순위

1. **높음**: GraphDB.__init__에 database 매개변수 추가
2. **높음**: 모든 session() 호출에 database 지정
3. **높음**: main.py의 모든 GraphDB 생성 시 database 전달
4. **낮음**: neo4j_connection_pool.py에 load_dotenv() 추가 (선택)

## 예상 작업량

- GraphDB 클래스: 약 50개 메서드의 session() 호출 수정
- main.py: 약 10개 위치의 GraphDB 생성 수정
- 예상 소요 시간: 30-40분

### To-dos

- [ ] GraphDB.__init__에 database 매개변수 추가
- [ ] 모든 session() 호출에 database=self._database 지정
- [ ] main.py의 모든 GraphDB 생성 시 database 전달
- [ ] NEO4J_DATABASE=csadb01로 설정 후 테스트