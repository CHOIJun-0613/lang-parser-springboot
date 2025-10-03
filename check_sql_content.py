from neo4j import GraphDatabase
import json

driver = GraphDatabase.driver('neo4j://127.0.0.1:7687', auth=('neo4j', 'devpass123'))

with driver.session() as session:
    # findUsersWithPaging SQL 내용 확인
    result = session.run('''
        MATCH (mapper:MyBatisMapper {project_name: 'car-center-devlab'})-[:HAS_SQL_STATEMENT]->(sql:SqlStatement {id: 'findUsersWithPaging'})
        RETURN sql.id, sql.sql_content, sql.tables, sql.sql_type
    ''')
    
    print("=== findUsersWithPaging SQL 내용 ===")
    for record in result:
        print(f'SQL ID: {record["sql.id"]}')
        print(f'SQL Content: {record["sql.sql_content"]}')
        print(f'Tables: {record["sql.tables"]}')
        print(f'SQL Type: {record["sql.sql_type"]}')
        print('---')
    
    # countUsers SQL 내용 확인
    result2 = session.run('''
        MATCH (mapper:MyBatisMapper {project_name: 'car-center-devlab'})-[:HAS_SQL_STATEMENT]->(sql:SqlStatement {id: 'countUsers'})
        RETURN sql.id, sql.sql_content, sql.tables, sql.sql_type
    ''')
    
    print("=== countUsers SQL 내용 ===")
    for record in result2:
        print(f'SQL ID: {record["sql.id"]}')
        print(f'SQL Content: {record["sql.sql_content"]}')
        print(f'Tables: {record["sql.tables"]}')
        print(f'SQL Type: {record["sql.sql_type"]}')
        print('---')

driver.close()
