# Java Parser Addon R001 - 논리명 추출 규칙

## 개요

`java_parser_addon_r001.py`는 프로젝트별 논리명 추출 규칙을 실시간으로 해석하여 Java 객체 분석 시 적용하는 모듈입니다. 이 모듈을 통해 각 프로젝트마다 다른 논리명 추출 규칙을 안전하게 적용할 수 있습니다.

## 주요 기능

### 1. 프로젝트별 규칙 관리
- 각 프로젝트마다 다른 논리명 추출 규칙 적용 가능
- 프로젝트별 규칙 파일이 없으면 기본 규칙 파일 사용
- 규칙 파일 변경 시 실시간 반영

### 2. 파일 타입별 처리
- **Java 파일**: 클래스와 메서드의 논리명 추출
- **MyBatis XML 파일**: Mapper와 SQL 문의 논리명 추출
- 확장 가능한 구조로 새로운 파일 타입 추가 용이

### 3. 실시간 규칙 해석
- 마크다운 형식의 규칙 파일을 실시간으로 파싱
- 규칙 변경 시 코드 수정 없이 반영

## 파일 구조

```
csa/
├── rules/
│   ├── rule001_extraction_logical_name.md          # 기본 규칙
│   └── car_center_devlab_logical_name_rules.md   # 프로젝트별 규칙
├── services/
│   ├── java_parser_addon_r001.py                  # 논리명 추출 모듈
│   ├── java_parser.py                             # 기존 Java 파서 (통합됨)
│   └── graph_db.py                               # Neo4j 저장 로직 (업데이트됨)
└── models/
    └── graph_entities.py                          # 데이터 모델 (logical_name 필드 추가)
```

## 사용법

### 1. 기본 사용법

```python
from csa.services.graph_db import GraphDB
from csa.services.java_parser_addon_r001 import process_java_file_with_rule001

# Neo4j 연결
graph_db = GraphDB(
    uri="neo4j://127.0.0.1:7687",
    user="neo4j", 
    password="devpass123"
)

# Java 파일 처리
success = process_java_file_with_rule001(
    file_path="path/to/YourClass.java",
    project_name="your-project",
    graph_db=graph_db
)
```

### 2. 프로젝트별 커스텀 규칙 사용

```python
from csa.services.java_parser_addon_r001 import process_project_with_custom_rules

# 프로젝트별 규칙으로 파일 처리
success = process_project_with_custom_rules(
    project_name="car-center-devlab",
    file_path="path/to/UserController.java",
    file_type="java",
    graph_db=graph_db
)
```

### 3. 팩토리 패턴으로 추출기 생성

```python
from csa.services.java_parser_addon_r001 import LogicalNameExtractorFactory

# Java 파일용 추출기
java_extractor = LogicalNameExtractorFactory.create_extractor(
    project_name="car-center-devlab",
    file_type="java"
)

# MyBatis XML 파일용 추출기
mybatis_extractor = LogicalNameExtractorFactory.create_extractor(
    project_name="car-center-devlab", 
    file_type="mybatis_xml"
)
```

## 규칙 파일 형식

### 기본 규칙 파일 (`rule001_extraction_logical_name.md`)

```markdown
# Logical Name Extraction Rules for Classes and Methods

## 1. Class(클래스)의 logical name(논리명) 추출 규칙
- **논리명(logical name) 위치**: Class 선언 위치의 상단에 코멘트로 기술
- **형식**: `/**\n * {logical_name}\n */`

## 2. Method(메서드)의 논리명 추출 규칙  
- **논리명(logical name) 위치**: Method 선언 위치의 상단에 코멘트로 기술
- **형식**: `/**\n * {logical_name}\n */`
```

### 프로젝트별 규칙 파일 (`{project_name}_logical_name_rules.md`)

```markdown
# car-center-devlab 프로젝트 논리명 추출 규칙

## 1. Class(클래스)의 logical name(논리명) 추출 규칙
- **논리명(logical name) 위치**: Class 선언 위치의 상단에 코멘트로 기술
- **형식**: `/**\n * {logical_name}\n */`

## 2. Method(메서드)의 논리명 추출 규칙
- **논리명(logical name) 위치**: Method 선언 위치의 상단에 코멘트로 기술  
- **형식**: `/**\n * {logical_name}\n */`

## 3. MyBatis Mapper XML의 논리명 추출 규칙
- **논리명(logical name) 위치**: `<mapper>` 태그의 `namespace` 속성 위의 주석
- **형식**: `<!-- {logical_name} -->`

## 4. SQL 문의 논리명 추출 규칙
- **논리명(logical name) 위치**: 각 SQL 태그 위의 주석
- **형식**: `<!-- {logical_name} -->`
```

## Java 소스 코드 예시

### 클래스 논리명 추출

```java
/**
 * 사용자 관리 컨트롤러
 */
@RestController
public class UserController {
    // 논리명: "사용자 관리 컨트롤러"
}
```

### 메서드 논리명 추출

```java
/**
 * 비밀번호 변경
 */
@PutMapping("/password")
public ResponseEntity<ApiResponse<Void>> changePassword(
        @Valid @RequestBody UserDto.ChangePasswordRequest request) {
    // 논리명: "비밀번호 변경"
}
```

## MyBatis XML 예시

### Mapper 논리명 추출

```xml
<!-- 사용자 데이터 매퍼 -->
<mapper namespace="com.carcare.domain.user.mapper.UserMapper">
    <!-- 논리명: "사용자 데이터 매퍼" -->
</mapper>
```

### SQL 문 논리명 추출

```xml
<!-- 사용자 ID로 조회 -->
<select id="findUserById" parameterType="Long" resultType="User">
    <!-- 논리명: "사용자 ID로 조회" -->
    SELECT * FROM users WHERE user_id = #{userId}
</select>
```

## 기존 java_parser.py와의 통합

`java_parser.py`가 업데이트되어 논리명 추출 기능이 통합되었습니다:

```python
# 기존 함수 시그니처 변경
def parse_single_java_file(file_path: str, project_name: str, graph_db: GraphDB = None):
    # Rule001 논리명 추출이 자동으로 적용됨

def parse_java_project(directory: str, graph_db: GraphDB = None):
    # Rule001 논리명 추출이 자동으로 적용됨
```

## 데이터베이스 저장

추출된 논리명은 Neo4j 데이터베이스의 다음 노드에 저장됩니다:

- **Class 노드**: `logical_name` 속성
- **Method 노드**: `logical_name` 속성  
- **MyBatisMapper 노드**: `logical_name` 속성
- **SqlStatement 노드**: `logical_name` 속성

## 장점

1. **프로젝트별 규칙 분리**: 각 프로젝트마다 다른 규칙 적용 가능
2. **실시간 규칙 해석**: 규칙 파일 변경 시 즉시 반영
3. **확장성**: 새로운 파일 타입 추가 용이
4. **안전성**: 잘못된 파싱 방지
5. **유연성**: 공통 규칙과 프로젝트별 규칙 분리

## 테스트

```bash
# 테스트 실행
python tests/test_java_parser_addon_r001.py
```

## 주의사항

1. 프로젝트별 규칙 파일은 `csa/rules/` 디렉토리에 위치해야 합니다
2. 규칙 파일명은 `{project_name}_logical_name_rules.md` 형식이어야 합니다
3. Neo4j 데이터베이스 연결이 필요합니다
4. 기존 데이터에 논리명을 추가하려면 재분석이 필요합니다
