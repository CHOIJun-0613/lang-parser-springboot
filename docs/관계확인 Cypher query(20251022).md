
  1. 기본 관계 확인

  1-1. 관계가 존재하는지 확인 (간단한 카운트)

  // Method -> SqlStatement CALLS 관계 개수
  MATCH (m:Method)-[r:CALLS]->(s:SqlStatement)
  RETURN count(r) as calls_count

  1-2. 전체 체인 확인 (Class -> Method -> SqlStatement)

  // 프로젝트 지정
  MATCH (c:Class {project_name: 'car-center-devlab'})
  MATCH (c)-[:HAS_METHOD]->(m:Method)
  MATCH (m)-[:CALLS]->(s:SqlStatement)
  RETURN c.name as class_name, 
         m.name as method_name,
         s.id as sql_id,
         s.sql_type as sql_type
  LIMIT 20

  1-3. 관계가 없는 경우도 확인 (OPTIONAL MATCH)

  // Method는 있지만 SQL 호출이 없는 경우도 포함
  MATCH (c:Class {project_name: 'car-center-devlab'})
  MATCH (c)-[:HAS_METHOD]->(m:Method)
  OPTIONAL MATCH (m)-[:CALLS]->(s:SqlStatement)
  RETURN c.name as class_name,
         m.name as method_name,
         s.id as sql_id,
         CASE WHEN s IS NULL THEN 'No SQL' ELSE 'Has SQL' END as has_sql
  LIMIT 20

  2. 특정 클래스/메서드 추적

  2-1. 특정 클래스의 SQL 호출 추적

  // 특정 클래스 (예: UserMapper)
  MATCH (c:Class {name: 'UserMapper', project_name: 'car-center-devlab'})
  MATCH (c)-[:HAS_METHOD]->(m:Method)
  MATCH (m)-[:CALLS]->(s:SqlStatement)
  RETURN c.name as class_name,
         c.package_name as package_name,
         m.name as method_name,
         s.id as sql_id,
         s.sql_type as sql_type,
         s.tables as tables

  2-2. 특정 메서드가 호출하는 SQL 확인

  // 특정 메서드가 호출하는 모든 SQL
  MATCH (c:Class)-[:HAS_METHOD]->(m:Method {name: 'selectUserById'})
  MATCH (m)-[:CALLS]->(s:SqlStatement)
  RETURN c.name as class_name,
         m.name as method_name,
         s.id as sql_id,
         s.sql_type as sql_type,
         s.sql_content as sql_content

  3. MyBatisMapper 포함 전체 관계 확인

  3-1. Mapper 클래스와 SQL 관계 확인

  // Class(Mapper) -> Method -> SqlStatement와
  // MyBatisMapper -> SqlStatement 관계를 함께 확인
  MATCH (c:Class)
  WHERE c.name ENDS WITH 'Mapper'
  MATCH (c)-[:HAS_METHOD]->(m:Method)
  OPTIONAL MATCH (m)-[:CALLS]->(s:SqlStatement)
  OPTIONAL MATCH (mapper:MyBatisMapper {name: c.name})-[:HAS_SQL_STATEMENT]->(s2:SqlStatement)
  RETURN c.name as class_name,
         m.name as method_name,
         s.id as sql_from_method,
         s2.id as sql_from_mapper
  LIMIT 20

  3-2. 양방향 관계 확인 (Method -> SQL, Mapper -> SQL)

  // Method -[:CALLS]-> SqlStatement
  // MyBatisMapper -[:HAS_SQL_STATEMENT]-> SqlStatement
  MATCH (s:SqlStatement {project_name: 'car-center-devlab'})
  OPTIONAL MATCH (m:Method)-[:CALLS]->(s)
  OPTIONAL MATCH (c:Class)-[:HAS_METHOD]->(m)
  OPTIONAL MATCH (mapper:MyBatisMapper)-[:HAS_SQL_STATEMENT]->(s)
  RETURN s.id as sql_id,
         s.mapper_name as sql_mapper_name,
         c.name as calling_class,
         m.name as calling_method,
         mapper.name as mybatis_mapper
  LIMIT 20

  4. 통계 쿼리

  4-1. 클래스별 SQL 호출 통계

  // 각 클래스가 호출하는 SQL 개수
  MATCH (c:Class {project_name: 'car-center-devlab'})
  MATCH (c)-[:HAS_METHOD]->(m:Method)
  MATCH (m)-[:CALLS]->(s:SqlStatement)
  RETURN c.name as class_name,
         count(DISTINCT m) as method_count,
         count(DISTINCT s) as sql_count
  ORDER BY sql_count DESC

  4-2. SQL 타입별 분포

  // SELECT, INSERT, UPDATE, DELETE 별 개수
  MATCH (c:Class {project_name: 'car-center-devlab'})
  MATCH (c)-[:HAS_METHOD]->(m:Method)
  MATCH (m)-[:CALLS]->(s:SqlStatement)
  RETURN s.sql_type as sql_type,
         count(s) as count
  ORDER BY count DESC

  5. 호출 체인 시각화 (경로 확인)

  5-1. 전체 경로 확인 (Path)

  // Class -> Method -> SqlStatement 경로를 Path로 반환
  MATCH path = (c:Class)-[:HAS_METHOD]->(m:Method)-[:CALLS]->(s:SqlStatement)
  WHERE c.project_name = 'car-center-devlab'
  RETURN path
  LIMIT 10

  5-2. Table까지 포함한 확장 쿼리

  // SqlStatement.tables 속성을 파싱하여 Table 정보 확인
  MATCH (c:Class {project_name: 'car-center-devlab'})
  MATCH (c)-[:HAS_METHOD]->(m:Method)
  MATCH (m)-[:CALLS]->(s:SqlStatement)
  RETURN c.name as class_name,
         m.name as method_name,
         s.id as sql_id,
         s.sql_type as sql_type,
         s.tables as accessed_tables
  LIMIT 20

  6. 관계가 없는 경우 진단

  6-1. Method는 있지만 CALLS 관계가 없는 경우

  // SQL을 호출하지 않는 메서드 찾기
  MATCH (c:Class)-[:HAS_METHOD]->(m:Method)
  WHERE NOT (m)-[:CALLS]->(:SqlStatement)
    AND (c.name ENDS WITH 'Mapper' OR c.name ENDS WITH 'Repository')
  RETURN c.name as class_name,
         m.name as method_name,
         'No SQL Call' as status
  LIMIT 20

  6-2. SqlStatement는 있지만 Method에서 호출하지 않는 경우

  // 어떤 Method에서도 호출되지 않는 SQL
  MATCH (s:SqlStatement {project_name: 'car-center-devlab'})
  WHERE NOT (:Method)-[:CALLS]->(s)
  RETURN s.id as sql_id,
         s.mapper_name as mapper_name,
         s.sql_type as sql_type,
         'Not Called by Method' as status
  LIMIT 20

  7. 특정 프로젝트 전체 호출 그래프

  // 프로젝트의 모든 Class -> Method -> SqlStatement 관계를 그래프로 시각화
  MATCH (c:Class {project_name: 'car-center-devlab'})
  WHERE c.name ENDS WITH 'Mapper' OR c.name ENDS WITH 'Repository'
  MATCH (c)-[:HAS_METHOD]->(m:Method)
  OPTIONAL MATCH (m)-[:CALLS]->(s:SqlStatement)
  OPTIONAL MATCH (mapper:MyBatisMapper {name: c.name})-[:HAS_SQL_STATEMENT]->(s)
  RETURN c, m, s, mapper