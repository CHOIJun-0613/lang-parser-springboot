// Community는 기본 DB 이름을 compose에서 csadb01로 지정하여 사용
// 사용자 관리 명령은 system DB에서 실행
DROP USER csauser IF EXISTS;

CREATE USER csauser
  SET PASSWORD '${NEO4J_PASSWORD}'
  CHANGE NOT REQUIRED
  SET HOME DATABASE csadb01;

// (보안 권장) 기본 neo4j 계정 조치
// ALTER USER neo4j SET STATUS SUSPENDED;
// 또는
ALTER USER neo4j SET PASSWORD 'neo4j123' CHANGE REQUIRED;