  ## SqlStatement의 ai_description을 빈 문자열로 초기화하는 Cypher 쿼리

  1. 특정 프로젝트의 모든 SqlStatement 초기화

  MATCH (s:SqlStatement)
  WHERE s.project_name = 'car-center-devlab'
  SET s.ai_description = ''
  RETURN count(s) as updated_count

  2. 모든 프로젝트의 SqlStatement 초기화

  MATCH (s:SqlStatement)
  SET s.ai_description = ''
  RETURN count(s) as updated_count

  3. ai_description이 있는 것만 초기화 (확인용)

  MATCH (s:SqlStatement)
  WHERE s.project_name = 'car-center-devlab'
    AND s.ai_description IS NOT NULL
    AND s.ai_description <> ''
  SET s.ai_description = ''
  RETURN count(s) as updated_count

  4. Python으로 실행하는 방법

  python -c "
  from csa.services.graph_db import GraphDB
  import os

  uri = os.getenv('NEO4J_URI', 'neo4j://127.0.0.1:7687')
  user = os.getenv('NEO4J_USER', 'csauser')
  password = os.getenv('NEO4J_PASSWORD', 'csauser123')
  database = os.getenv('NEO4J_DATABASE', 'csadb01')

  db = GraphDB(uri, user, password, database)

  query = '''
  MATCH (s:SqlStatement)
  WHERE s.project_name = $project_name
  SET s.ai_description = ''
  RETURN count(s) as updated_count
  '''

  with db.driver.session(database=db.database) as session:
      result = session.run(query, project_name='car-center-devlab')
      count = result.single()['updated_count']
      print(f'Updated {count} SqlStatement nodes')

  db.close()
  "