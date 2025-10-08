<!-- b1081611-8017-4305-b743-61650bf8f5fc 9dbb3a15-3dc8-482c-ba0b-1cdc1fdc68fe -->
# Fix Schema None Display in CRUD Matrix

## 문제 상황

SqlStatement 노드의 tables에는 테이블이 있지만, 같은 name의 Table 노드가 없을 수 있습니다.

Table 노드가 존재하지 않으면 schema를 조회할 수 없습니다.

## 현재 동작

- Table 노드가 없을 경우: `schema = 'unknown'`으로 설정 (graph_db.py에서 유지)
- 출력 시: `'unknown'`을 `'None'`으로 변환하여 표시

## 수정 범위

모든 CRUD matrix 출력 형식에서 schema 값이 'unknown'인 경우 'None'으로 표시:

1. Markdown (*.md)
2. Excel (*.xlsx)
3. SVG (*.svg)
4. PNG (*.png)

## 구현 계획

### CLI main.py - 출력 포맷 수정

**파일**: `csa/cli/main.py`

**핵심 로직**: `schema = 'unknown'`을 `'None'`으로 변환하여 표시

#### A. 콘솔 출력 (Line ~1477)

```python
# 수정:
schema = row['schema'] if row['schema'] != 'unknown' else 'None'
```

#### B. Markdown 출력 (Line ~1500)

```python
# 수정:
schema = row['schema'] if row['schema'] != 'unknown' else 'None'
```

#### C. Excel 출력 (Line ~126)

```python
# 수정:
'Schema': row['schema'] if row['schema'] != 'unknown' else 'None',
```

#### D. Image 출력 - 변경 불필요

현재 코드는 이미 'unknown'을 None으로 처리하여 테이블명만 표시

### 테스트 시나리오

1. **Table 노드가 존재하는 경우**

   - 기대값: `schema = 'public'` (실제 schema 값)

2. **Table 노드가 없는 경우**

   - DB 저장값: `schema = 'unknown'`
   - 출력값: `schema = 'None'`

3. **Table 노드는 있지만 schema가 null인 경우**

   - DB 저장값: `schema = 'unknown'`
   - 출력값: `schema = 'None'`

## 변경 파일

`csa/cli/main.py` - 출력 관련 코드 (콘솔, Markdown, Excel)

### To-dos

- [ ] crud_matrix 명령어에 --output-format 옵션 추가
- [ ] Excel 파일 생성 헬퍼 함수 구현
- [ ] SVG/PNG 이미지 생성 헬퍼 함수 구현
- [ ] crud_matrix 함수에 추가 형식 파일 생성 로직 통합
- [ ] 모든 출력 형식 테스트 (markdown, excel, svg, png)