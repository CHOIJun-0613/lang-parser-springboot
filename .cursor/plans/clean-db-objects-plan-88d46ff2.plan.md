<!-- 88d46ff2-d47f-4bef-a888-58a4381a20b6 1f6349c2-e349-413c-8c0c-99c856c3de15 -->
# 논리명 추출 실패 시 빈 문자열로 저장

## 수정 방침

- 논리명 추출 성공: 추출된 논리명 저장
- 논리명 추출 실패 (None 반환): 빈 문자열("") 저장
- 기존 방식(package.class.method) 사용 안 함

## 수정할 파일

`csa/services/java_parser.py`

## 변경 사항

### 1. parse_java_project() - 클래스 논리명 (2628번 라인)

```python
# 수정 전
logical_name=class_logical_name if class_logical_name else class_key,

# 수정 후
logical_name=class_logical_name if class_logical_name else "",
```

### 2. parse_java_project() - 메서드 논리명 (2751번 라인)

```python
# 수정 전
logical_name=method_logical_name if method_logical_name else f"{class_key}.{declaration.name}",

# 수정 후
logical_name=method_logical_name if method_logical_name else "",
```

### 3. parse_mybatis_xml_file() - Mapper 논리명 (1079번 라인)

```python
# 수정 전
logical_name=mapper_logical_name,

# 수정 후
logical_name=mapper_logical_name if mapper_logical_name else "",
```

### 4. parse_mybatis_xml_file() - SQL Statement 논리명 (1038번 라인)

```python
# 수정 전
"logical_name": sql_logical_name,

# 수정 후
"logical_name": sql_logical_name if sql_logical_name else "",
```

## 결과

논리명이 없는 Class, Method, MyBatisMapper, SqlStatement는 모두 `logical_name=""` 값으로 DB에 저장됨.