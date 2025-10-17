// ==============================================================================
// Step 2: Field Injection Bean 의존성 해결 Cypher 쿼리
// ==============================================================================
//
// 목표: Field에 @Autowired/@Inject/@Resource 어노테이션이 있는 경우,
//       Field type과 Bean class_name을 매칭하여 DEPENDS_ON 관계 생성
//
// 파라미터:
//   - $project_name: 프로젝트명 (예: "car-center-devlab")
//
// ==============================================================================

// 1. Bean이 포함된 클래스의 Field 찾기
MATCH (sourceClass:Class)-[:HAS_FIELD]->(field:Field {project_name: $project_name})
MATCH (sourceBean:Bean {class_name: sourceClass.name, project_name: $project_name})

// 2. Field에 injection 어노테이션이 있는지 확인
WHERE field.annotations_json IS NOT NULL
  AND (field.annotations_json CONTAINS '"Autowired"'
       OR field.annotations_json CONTAINS '"Inject"'
       OR field.annotations_json CONTAINS '"Resource"')

// 3. Field type과 일치하는 Bean 찾기 (class_name으로 매칭)
MATCH (targetBean:Bean {project_name: $project_name})
WHERE targetBean.class_name = field.type

// 4. DEPENDS_ON 관계 생성 (중복 방지를 위해 MERGE 사용)
MERGE (sourceBean)-[r:DEPENDS_ON]->(targetBean)
SET r.injection_type = 'field',
    r.field_name = field.name,
    r.field_type = field.type,
    r.created_by = 'neo4j_resolver'

// 5. 생성된 의존성 정보 반환
RETURN sourceBean.name as source_bean,
       sourceBean.class_name as source_class,
       field.name as field_name,
       field.type as field_type,
       targetBean.name as target_bean,
       targetBean.class_name as target_class
