# Class 노드 package / package_name 중복 속성 정리 메모

## 배경
- 기존 GraphDB 저장 로직(`csa/services/graph_db/project_nodes.py`)은 `MERGE (c:Class {name: $name, package: $package})` 패턴을 사용하면서 `c.package_name` 속성을 추가로 세팅함.
- Neo4j 상의 `Class` 노드에 `package`와 `package_name`이 동시에 존재하여, 분석 결과 조회 시 혼선이 발생하고 중복 데이터가 쌓임.
- 코드 레벨에서는 `package_name`을 표준으로 활용하고 있으나, Cypher 쿼리 일부가 `package` 속성을 계속 사용해 일관성이 깨짐.

## 조치 내용
1. `csa/services/graph_db/project_nodes.py`
   - Class 노드 MERGE 키를 `name + package_name`으로 일원화.
   - 패키지/프로젝트 관계 연결, import/superclass/method call 처리 과정의 모든 `MATCH/MERGE` 구문을 `package_name` 기준으로 변경.
   - Inner class 패키지 조회 시 `oc.package_name`을 반환하도록 수정.
2. `csa/models/graph_entities.py`
   - `Class` 모델에 `package` 프로퍼티(게터/세터)를 추가하여 기존 코드 호환성을 유지하면서 내부적으로 `package_name`만 사용.

## 남은 고려 사항
- 기존 Neo4j 데이터에 남아 있는 `package` 속성은 재분석을 통해 덮어쓰는 것이 가장 간단함. (현재 요청에 따라 별도 마이그레이션 스크립트는 실행하지 않음)
- 향후 다른 모듈이나 문서에서 `package` 속성을 직접 조회하는 코드가 있는지 진단 필요. 발견 시 `package_name` 사용으로 정리 권장.
