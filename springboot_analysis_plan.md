# SpringBoot 분석을 위한 수정 계획

## 1. 어노테이션 모델 추가

### Annotation 모델
```python
class Annotation(BaseModel):
    name: str  # @Component, @Service 등
    parameters: dict[str, Any] = {}  # 어노테이션 파라미터
    target_type: str  # "class", "method", "field"
```

### 기존 모델에 annotations 속성 추가
- Class, Method, Property에 `annotations: list[Annotation] = []` 추가

## 2. Bean 관련 모델 추가

### Bean 모델
```python
class Bean(BaseModel):
    name: str
    type: str  # "component", "service", "repository", "controller"
    scope: str  # "singleton", "prototype", "request", "session"
    class_name: str
    annotations: list[Annotation] = []
```

### Bean 의존성 모델
```python
class BeanDependency(BaseModel):
    source_bean: str
    target_bean: str
    injection_type: str  # "field", "constructor", "setter"
    field_name: str = ""
```

## 3. REST API 모델 추가

### Endpoint 모델
```python
class Endpoint(BaseModel):
    path: str
    method: str  # "GET", "POST", "PUT", "DELETE"
    controller_class: str
    handler_method: str
    parameters: list[dict] = []
    return_type: str = ""
```

## 4. JPA 엔티티 모델 추가

### Entity 모델
```python
class Entity(BaseModel):
    name: str
    table_name: str
    columns: list[dict] = []
    relationships: list[dict] = []
    annotations: list[Annotation] = []
```

## 5. 설정 파일 분석 기능

### Properties 파일 파서
- application.properties 파싱
- application.yml 파싱
- 설정 값과 Bean의 연관성 추적

## 6. 테스트 코드 분석

### Test 모델
```python
class Test(BaseModel):
    test_class: str
    test_method: str
    target_class: str
    annotations: list[Annotation] = []
```

## 7. 그래프 데이터베이스 스키마 확장

### 새로운 노드 타입
- Annotation
- Bean
- Endpoint
- Entity
- Test
- Configuration

### 새로운 관계 타입
- (Class)-[:HAS_ANNOTATION]->(Annotation)
- (Bean)-[:DEPENDS_ON]->(Bean)
- (Controller)-[:HAS_ENDPOINT]->(Endpoint)
- (Entity)-[:HAS_COLUMN]->(Column)
- (Test)-[:TESTS]->(Class)

## 8. Java 파서 확장

### 어노테이션 추출 로직
```python
def extract_annotations(node) -> list[Annotation]:
    annotations = []
    for annotation in node.annotations:
        ann = Annotation(
            name=annotation.name,
            parameters=extract_annotation_parameters(annotation),
            target_type=node_type
        )
        annotations.append(ann)
    return annotations
```

### SpringBoot 어노테이션 분류
- Component 어노테이션: @Component, @Service, @Repository, @Controller
- Configuration 어노테이션: @Configuration, @Bean
- Injection 어노테이션: @Autowired, @Resource, @Value
- Web 어노테이션: @RestController, @RequestMapping
- JPA 어노테이션: @Entity, @Table, @Id, @Column
- Test 어노테이션: @Test, @SpringBootTest

## 9. 분석 쿼리 예시

### Bean 의존성 분석
```cypher
MATCH (b1:Bean)-[:DEPENDS_ON]->(b2:Bean)
RETURN b1.name as source, b2.name as target

### API 엔드포인트 분석
```cypher
MATCH (c:Class)-[:HAS_ANNOTATION]->(a:Annotation {name: "RestController"})
MATCH (c)-[:HAS_ENDPOINT]->(e:Endpoint)
RETURN c.name as controller, e.path as endpoint, e.method as method

### JPA 엔티티 관계 분석
```cypher
MATCH (e:Entity)-[:HAS_RELATIONSHIP]->(e2:Entity)
RETURN e.name as source_entity, e2.name as target_entity
```

## 10. 구현 우선순위

1. **1단계**: 어노테이션 모델 및 추출 로직
2. **2단계**: Bean 모델 및 의존성 분석
3. **3단계**: REST API 엔드포인트 분석
4. **4단계**: JPA 엔티티 분석
5. **5단계**: 설정 파일 분석
6. **6단계**: 테스트 코드 분석
