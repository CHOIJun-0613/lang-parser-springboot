<!-- 8cc68926-d0f6-4075-81e3-87d39480f394 0a471e14-9e44-44a3-81bb-21665101e5e3 -->
# Mermaid Participant 표시 형식 수정

## 수정사항

### 1. Participant 따옴표 제거

**현재**:
```mermaid
participant UserService as "UserService<br/>(com.carcare.domain.user.service)"
```

**변경**:
```mermaid
participant UserService as UserService<br/>(com.carcare.domain.user.service)
```

### 2. SQL Participant 표시 변경

**현재**:
```mermaid
participant SQL as "SQL<br/>(UserMapper.xml : com.carcare.domain.user.mapper.UserMapper)"
```

**변경**:
```mermaid
participant SQL as UserMapper.xml<br/>(com.carcare.domain.user.mapper.UserMapper)
```

## 구현

### `_generate_mermaid_diagram()` 수정
- 모든 participant alias에서 따옴표(`"`) 제거
- SQL participant의 경우: `SQL`을 `mapper_file.xml`로 표시

## 주요 수정 파일
- `src/services/sequence_diagram_generator.py`
  - Participant 선언 시 따옴표 제거
  - SQL participant를 mapper 파일명으로 변경


### To-dos

- [ ] Participant alias에서 따옴표 제거
- [ ] SQL participant를 mapper 파일명으로 변경
- [ ] 수정 후 테스트하여 형식 확인