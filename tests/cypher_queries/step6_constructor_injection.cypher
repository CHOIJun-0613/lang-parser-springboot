// Constructor Injection 의존성 해결 Cypher 쿼리
// 목표: 생성자 파라미터를 통한 Bean 의존성 관계 생성
// 주의: parameters는 JSON 문자열이므로 Python에서 파싱 후 처리

// 1. Bean이 포함된 클래스의 생성자 Method 찾기
MATCH (sourceClass:Class)-[:HAS_METHOD]->(constructor:Method {project_name: $project_name})
MATCH (sourceBean:Bean {class_name: sourceClass.name, project_name: $project_name})

// 2. 생성자인지 확인 (메서드명 = 클래스명)
WHERE constructor.name = sourceClass.name
  AND constructor.parameters IS NOT NULL

// 3. 생성자 정보 반환 (Python에서 JSON 파싱 후 처리)
RETURN sourceBean.name as source_bean,
       sourceBean.class_name as source_class,
       constructor.name as constructor_name,
       constructor.parameters as parameters_json
ORDER BY source_bean
