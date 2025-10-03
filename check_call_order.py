from neo4j import GraphDatabase
import json

driver = GraphDatabase.driver('neo4j://127.0.0.1:7687', auth=('neo4j', 'devpass123'))

with driver.session() as session:
    # UserController.getUserList에서의 호출 순서 확인
    result = session.run('''
        MATCH (c:Class {name: 'UserController', project_name: 'car-center-devlab'})-[:HAS_METHOD]->(m:Method {name: 'getUserList'})
        MATCH path = (m)-[:CALLS*0..5]->(callee:Method)
        UNWIND range(0, size(nodes(path))-1) as i
        WITH m.name as top_level_method, nodes(path)[i] AS source_method, nodes(path)[i+1] AS target_method, (i + 1) as depth
        MATCH (source_class:Class)-[:HAS_METHOD]->(source_method)
        MATCH (target_class:Class)-[:HAS_METHOD]->(target_method)
        WHERE source_class.project_name IS NOT NULL AND target_class.project_name IS NOT NULL
        RETURN DISTINCT top_level_method, source_class.name AS source_class, source_method.name AS source_method, target_class.name AS target_class, target_method.name AS target_method, depth
        ORDER BY depth, source_method.name
    ''')
    
    print("=== UserController.getUserList 호출 순서 ===")
    for record in result:
        print(f'Depth: {record["depth"]}, {record["source_class"]}.{record["source_method"]} -> {record["target_class"]}.{record["target_method"]}')

driver.close()
