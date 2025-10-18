// Setter Injection 의존성 해결 Cypher 쿼리
// 목표: setter 메서드 파라미터를 통한 Bean 의존성 관계 생성
// 주의: parameters는 JSON 문자열이므로 Python에서 파싱 후 처리

// 1. Bean이 포함된 클래스의 setter Method 찾기
MATCH (sourceClass:Class)-[:HAS_METHOD]->(setter:Method {project_name: $project_name})
MATCH (sourceBean:Bean {class_name: sourceClass.name, project_name: $project_name})

// 2. setter 메서드인지 확인
//    - 메서드명이 'set'으로 시작
//    - @Autowired 어노테이션 존재
//    - 파라미터가 있음
WHERE setter.name STARTS WITH 'set'
  AND setter.parameters IS NOT NULL
  AND setter.annotations_json IS NOT NULL
  AND setter.annotations_json CONTAINS '"Autowired"'

// 3. setter 정보 반환 (Python에서 JSON 파싱 후 처리)
RETURN sourceBean.name as source_bean,
       sourceBean.class_name as source_class,
       setter.name as setter_name,
       setter.parameters as parameters_json,
       setter.annotations_json as annotations_json
ORDER BY source_bean, setter_name
