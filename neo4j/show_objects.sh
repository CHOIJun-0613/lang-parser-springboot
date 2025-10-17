#!/bin/bash
echo "=== 1. 데이터베이스 확인 ==="
cypher-shell -a bolt://localhost:7687 -u neo4j -p neo4j-temp "SHOW DATABASES;"

echo -e "\n=== 2. 사용자 확인 ==="
cypher-shell -a bolt://localhost:7687 -u neo4j -p neo4j-temp -d system "SHOW USERS;"

echo -e "\n=== 3. 노드 현황 ==="
cypher-shell -a bolt://localhost:7687 -u csauser -p csauser123 -d csadb01 \
  "MATCH (n) RETURN labels(n) as NodeType, count(n) as Count ORDER BY Count DESC LIMIT 10;"

echo -e "\n=== 4. 관계 현황 ==="
cypher-shell -a bolt://localhost:7687 -u csauser -p csauser123 -d csadb01 \
  "MATCH ()-[r]->() RETURN type(r) as RelationType, count(r) as Count ORDER BY Count DESC LIMIT 10;"

echo -e "\n=== 5. 전체 통계 ==="
cypher-shell -a bolt://localhost:7687 -u csauser -p csauser123 -d csadb01 \
  "MATCH (n) WITH count(n) as NodeCount MATCH ()-[r]->() RETURN NodeCount, count(r) as RelationshipCount;"
