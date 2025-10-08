<!-- 9fbf82e8-109a-4e59-aceb-396486589a10 60992150-4455-492c-b5bc-4c4d7dc80848 -->
# crud-visualization CLI 옵션 수정

## 실제 코드 분석 결과

**generate_crud_visualization_diagram 함수:**

- Mermaid 다이어그램 문자열 반환 (markdown 형식)
- 내부에서 `generate_crud_matrix()` 호출
- `generate_crud_matrix()` 반환: `{'class_matrix': [...], 'table_matrix': [...]}`

**현재 문제:**

- Excel/이미지 저장을 위해서는 `generate_crud_matrix()` 데이터 필요

## 수정 내용

### 1. 옵션 변경 (2054-2060행)

- **제거**: `--output-file`, `--output-image`
- **변경**: `--image-format` → `--output-format` (excel/svg/png, 기본값 excel)

### 2. 함수 시그니처 (2060행)

```python
def crud_visualization(neo4j_uri, neo4j_user, project_name, output_format, image_width, image_height, auto_create_relationships)
```

### 3. 로직 수정 (2077-2120행)

1. `generate_crud_matrix()` 호출
2. output_format 분기:

   - excel: `_save_crud_matrix_as_excel()` 
   - svg/png: `_save_crud_matrix_as_image()`

3. 출력: `./output/crud-matrix/CRUD_visualization_{project}_{timestamp}.{ext}`

### 참고 코드

- crud_matrix (1540-1597행)
- _save_crud_matrix_as_excel (112행)
- _save_crud_matrix_as_image (166행)

### To-dos

- [ ] crud-visualization 옵션 변경
- [ ] 함수 로직 수정