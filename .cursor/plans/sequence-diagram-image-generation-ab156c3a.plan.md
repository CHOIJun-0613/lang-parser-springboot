<!-- ab156c3a-1f6d-417a-a565-87713ce35c4f a600c9e9-6084-49af-8f7d-b027134b469b -->
# CLI 옵션 통일 및 전체 분석 수정

## 수정 목표

1. **CLI 옵션 네이밍 통일**: 언더스코어를 하이픈으로 변경 (케밥 케이스)

   - `--db_object` → `--db-object`
   - `--java_object` → `--java-object`
   - `--all_objects` → `--all-objects`

2. **전체 분석 로직 수정**: 플래그 없음 또는 `--all-objects` 시 Java + DB 모두 분석

3. **`project_name` 처리**:

   - Java 객체: CLI 옵션 > 자동 감지 > 폴백
   - DB 객체: 항상 `None` (프로젝트 독립적)

## 파일 수정

### `csa/cli/main.py`

#### 1. CLI 옵션 정의 수정 (라인 123-128)

**수정 전**:

```python
@click.option('--db_object', is_flag=True, help='...')
@click.option('--java_object', is_flag=True, help='...')
@click.option('--all_objects', is_flag=True, help='...')
def analyze(java_source_folder, neo4j_uri, neo4j_user, neo4j_password, clean, class_name, update, db_object, java_object, all_objects, dry_run, project_name):
```

**수정 후**:

```python
@click.option('--db-object', 'db_object', is_flag=True, help='...')
@click.option('--java-object', 'java_object', is_flag=True, help='...')
@click.option('--all-objects', 'all_objects', is_flag=True, help='...')
def analyze(java_source_folder, neo4j_uri, neo4j_user, neo4j_password, clean, class_name, update, db_object, java_object, all_objects, dry_run, project_name):
```

#### 2. docstring 예제 업데이트 (라인 139-149)

```python
# Analyze only database objects
python -m csa.cli.main analyze --db-object

# Analyze only Java objects
python -m csa.cli.main analyze --java-object

# Analyze both database and Java objects
python -m csa.cli.main analyze --all-objects
```

#### 3. `--all_objects` 처리 로직 수정 (라인 154-158)

```python
# Handle --all-objects option
if all_objects:
    db_object = True
    java_object = True
    click.echo("--all-objects option detected: Analyzing both Java objects and database objects")
```

#### 4. 전체 분석 섹션에 DB 객체 분석 추가 (라인 742-880 이후)

현재 전체 분석 섹션(플래그 없음)은 Java 객체만 분석합니다. DB 객체 분석을 추가해야 합니다.

**추가할 로직**:

1. Java 객체 분석 완료 후
2. `DB_SCRIPT_FOLDER` 환경 변수 확인
3. DDL 파일 파싱 및 DB 객체 추가 (`project_name=None`)
```python
# After Java objects are added (around line 880)

# Also analyze DB objects if DB_SCRIPT_FOLDER is set
db_script_folder = os.getenv("DB_SCRIPT_FOLDER")
if db_script_folder and os.path.exists(db_script_folder):
    click.echo("\nAlso analyzing database objects from DDL scripts...")
    
    try:
        db_parser = DBParser()
        all_db_objects = db_parser.parse_ddl_directory(db_script_folder, None)
        
        if all_db_objects:
            for i, db_objects in enumerate(all_db_objects):
                click.echo(f"Processing DDL file {i+1}...")
                db.add_database(db_objects['database'], None)
                
                for table_obj in db_objects['tables']:
                    db.add_table(table_obj, db_objects['database'].name, None)
                
                for column_obj in db_objects['columns']:
                    table_name = getattr(column_obj, 'table_name', 'unknown')
                    db.add_column(column_obj, table_name, None)
                
                for index_obj, table_name in db_objects['indexes']:
                    db.add_index(index_obj, table_name, None)
                
                for constraint_obj, table_name in db_objects['constraints']:
                    db.add_constraint(constraint_obj, table_name, None)
            
            click.echo(f"Added {len(all_db_objects)} database schemas.")
    except Exception as e:
        click.echo(f"Warning: Could not analyze DB objects: {e}")
```


#### 5. 중복 코드 정리

라인 197-347의 `if java_object:` 블록과 라인 742-880의 전체 분석 블록에 중복 코드가 많습니다. 하지만 로직이 약간 다르므로 현재는 유지합니다.

## 테스트 시나리오

1. `python -m csa.cli.main analyze --java-object` → Java만
2. `python -m csa.cli.main analyze --db-object` → DB만
3. `python -m csa.cli.main analyze --all-objects` → Java + DB
4. `python -m csa.cli.main analyze` (플래그 없음) → Java + DB (DB_SCRIPT_FOLDER 설정 시)

## 예상 결과

- CLI 옵션이 일관된 케밥 케이스 패턴 사용
- 전체 분석 시 Java와 DB 객체 모두 분석
- DB 객체는 항상 `project_name=None`으로 저장

### To-dos

- [ ] CLI 옵션을 케밥 케이스로 변경 (--db-object, --java-object, --all-objects)
- [ ] docstring의 예제 명령어를 새 옵션 이름으로 업데이트
- [ ] 전체 분석 섹션에 DB 객체 분석 로직 추가
- [ ] 각 분석 시나리오 테스트 (java-object, db-object, all-objects, 플래그 없음)