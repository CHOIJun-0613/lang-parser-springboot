# 스트리밍 파이프라인 설계 문서

## 현재 구조의 문제점

### 메모리 사용 패턴
```
parse_java_project_full():
1. 모든 Java 파일 순회 (Line 375-707)
   → classes 딕셔너리에 누적 (~800MB)
2. classes_list = list(classes.values()) (Line 709)
   → 전체 클래스를 리스트로 변환
3. extract_beans_from_classes(classes_list) (Line 710)
   → 모든 클래스를 스캔하여 Bean 추출
4. extract_endpoints, mappers 등... (Line 716-722)
   → 모든 클래스를 또 스캔
5. Neo4j에 배치 저장 (neo4j_writer.py)
6. Bean 의존성 해결 (Neo4j 쿼리) ✅
```

**메모리 사용량**: ~800MB (136개 클래스 기준)

## 스트리밍 구조 설계

### 목표
- 메모리 사용량: 800MB → 10-20MB (97% 감소)
- 한 번에 1개 파일만 메모리에 로드
- 파싱 후 즉시 Neo4j 저장 및 메모리 해제

### 파이프라인 흐름

```
parse_java_project_streaming():

for each java_file:
  1. 파일 파싱 (parse_single_java_file)
     메모리: ~1MB

  2. Package 즉시 저장 (Neo4j)
     메모리에서 제거

  3. Class 즉시 저장 (Neo4j)

  4. Bean/Endpoint/Mapper 추출 및 즉시 저장
     add_single_class_objects_streaming()

  5. 경량 메타데이터만 보관
     - JPA Repository: {class_name, package_name}
     - MyBatis Mapper: {mapper_name, xml_path}
     메모리: ~1KB per item

  6. 클래스 객체 제거 (GC 대상)
     del class_node

모든 파일 처리 완료 후:

7. JPA Queries 추출 및 저장
   - Neo4j에서 JPA Repository 조회
   - 메서드에서 쿼리 추출

8. SQL Statements 추출 및 저장
   - Neo4j에서 MyBatis Mapper 조회
   - XML에서 SQL 추출

9. Bean 의존성 해결 (Neo4j 쿼리) ✅
   resolve_bean_dependencies_from_neo4j()

10. 통계 반환
    (클래스 리스트 대신 통계만)
```

### 메모리 사용량 추정

| 항목 | 현재 | 스트리밍 |
|------|------|----------|
| 클래스 객체 | ~800MB | ~1MB (한 번에 1개) |
| JPA Repo 메타 | 포함 | ~15KB (15개 × 1KB) |
| MyBatis Mapper 메타 | 포함 | ~31KB (31개 × 1KB) |
| Parser 오버헤드 | ~50MB | ~10MB |
| **총합** | **~850MB** | **~10-20MB** |

## 구현 계획

### 1단계: add_single_class_objects 수정

**파일**: `/workspace/csa/services/analysis/neo4j_writer.py`

```python
def add_single_class_objects_streaming(
    db: GraphDB,
    class_node,
    package_name: str,
    project_name: str,
    logger,
) -> dict:
    """
    파일별 즉시 저장 (스트리밍 방식)

    Returns:
        dict: 경량 메타데이터
        {
            'beans_count': 1,
            'endpoints_count': 3,
            'mybatis_mapper': {...} if exists,
            'jpa_repository': {...} if exists,
        }
    """
    classes_list = [class_node]

    # Bean 추출 및 저장
    beans = extract_beans_from_classes(classes_list)
    if beans:
        for bean in beans:
            db.add_bean(bean, project_name)

    # Endpoint 추출 및 저장
    endpoints = extract_endpoints_from_classes(classes_list)
    if endpoints:
        for endpoint in endpoints:
            db.add_endpoint(endpoint, project_name)

    # JPA Entity 추출 및 저장
    jpa_entities = extract_jpa_entities_from_classes(classes_list)
    if jpa_entities:
        for entity in jpa_entities:
            db.add_jpa_entity(entity, project_name)

    # Test 추출 및 저장
    test_classes = extract_test_classes_from_classes(classes_list)
    if test_classes:
        for test_class in test_classes:
            db.add_test_class(test_class, project_name)

    # 경량 메타데이터 반환
    metadata = {
        'beans_count': len(beans),
        'endpoints_count': len(endpoints),
        'jpa_entities_count': len(jpa_entities),
        'test_classes_count': len(test_classes),
    }

    # JPA Repository 메타데이터
    jpa_repos = extract_jpa_repositories_from_classes(classes_list)
    if jpa_repos:
        for repo in jpa_repos:
            db.add_jpa_repository(repo, project_name)
        metadata['jpa_repository'] = {
            'class_name': class_node.name,
            'package_name': package_name
        }

    # MyBatis Mapper 메타데이터
    mybatis_mappers = extract_mybatis_mappers_from_classes(classes_list)
    if mybatis_mappers:
        for mapper in mybatis_mappers:
            db.add_mybatis_mapper(mapper, project_name)
        metadata['mybatis_mapper'] = {
            'mapper_name': mybatis_mappers[0].mapper_name,
            'class_name': class_node.name
        }

    return metadata
```

### 2단계: parse_java_project_streaming 작성

**파일**: `/workspace/csa/services/java_analysis/project.py`

```python
def parse_java_project_streaming(
    directory: str,
    graph_db: GraphDB,
    project_name: str,
    logger
) -> dict:
    """
    스트리밍 방식 Java 프로젝트 파싱

    파일을 하나씩 파싱하고 즉시 Neo4j에 저장한 후 메모리에서 제거합니다.

    Returns:
        dict: 분석 통계
    """
    packages_saved = set()
    stats = {
        'total_files': 0,
        'processed_files': 0,
        'packages': 0,
        'classes': 0,
        'beans': 0,
        'endpoints': 0,
        'jpa_entities': 0,
        'jpa_repositories': 0,
        'test_classes': 0,
        'mybatis_mappers': 0,
    }

    mybatis_mapper_names = []  # XML 파싱용

    # 1. 파일별 스트리밍 처리
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".java"):
                stats['total_files'] += 1
                file_path = os.path.join(root, file)

                try:
                    # 파일 파싱
                    package_node, class_node, package_name = parse_single_java_file(
                        file_path, project_name, graph_db
                    )

                    if not class_node:
                        continue

                    # Package 즉시 저장
                    if package_name and package_name not in packages_saved:
                        graph_db.add_package(package_node, project_name)
                        packages_saved.add(package_name)
                        stats['packages'] += 1

                    # Class 즉시 저장
                    graph_db.add_class(class_node, package_name, project_name)
                    stats['classes'] += 1

                    # Bean/Endpoint 등 즉시 저장
                    from csa.services.analysis.neo4j_writer import add_single_class_objects_streaming
                    metadata = add_single_class_objects_streaming(
                        graph_db, class_node, package_name, project_name, logger
                    )

                    # 통계 업데이트
                    stats['beans'] += metadata.get('beans_count', 0)
                    stats['endpoints'] += metadata.get('endpoints_count', 0)
                    stats['jpa_entities'] += metadata.get('jpa_entities_count', 0)
                    stats['test_classes'] += metadata.get('test_classes_count', 0)

                    if 'jpa_repository' in metadata:
                        stats['jpa_repositories'] += 1

                    if 'mybatis_mapper' in metadata:
                        stats['mybatis_mappers'] += 1
                        mybatis_mapper_names.append(metadata['mybatis_mapper']['mapper_name'])

                    # 메모리 해제
                    del class_node
                    del package_node

                    stats['processed_files'] += 1

                except Exception as e:
                    logger.error(f"Error processing {file_path}: {e}")
                    continue

    # 2. MyBatis XML 파싱 및 저장
    xml_mappers = extract_mybatis_xml_mappers(directory, project_name, graph_db)
    for mapper in xml_mappers:
        graph_db.add_mybatis_mapper(mapper, project_name)
        stats['mybatis_mappers'] += 1
        mybatis_mapper_names.append(mapper.mapper_name)

    # 3. SQL Statements 추출 및 저장
    # (MyBatis mapper에서 추출)
    # TODO: Neo4j에서 Mapper 조회하여 SQL 추출

    # 4. JPA Queries 추출 및 저장
    # (JPA repository에서 추출)
    # TODO: Neo4j에서 Repository 조회하여 Query 추출

    # 5. Config 파일 처리
    config_files = extract_config_files(directory)
    for config in config_files:
        graph_db.add_config_file(config, project_name)

    # 6. Bean 의존성 해결 (Neo4j 쿼리)
    if stats['beans'] > 0:
        from csa.services.java_analysis.bean_dependency_resolver import (
            resolve_bean_dependencies_from_neo4j
        )
        resolve_bean_dependencies_from_neo4j(graph_db, project_name, logger)

    return stats
```

### 3단계: java_pipeline.py 통합

**파일**: `/workspace/csa/services/analysis/java_pipeline.py`

환경 변수 또는 파라미터로 스트리밍 모드 활성화:

```python
use_streaming = os.getenv("USE_STREAMING_PARSE", "true").lower() == "true"

if use_streaming:
    stats = parse_java_project_streaming(directory, db, project_name, logger)
    # artifacts 대신 stats 사용
else:
    # 기존 방식
    artifacts = parse_java_project_full(directory)
    # ...
```

## 테스트 계획

### 1. 기능 테스트
- [ ] 스트리밍 파싱 동작 확인
- [ ] Neo4j에 데이터 정상 저장 확인
- [ ] Bean 의존성 정상 해결 확인

### 2. 메모리 테스트
```python
import tracemalloc

tracemalloc.start()

# 기존 방식
snapshot1 = tracemalloc.take_snapshot()

# 스트리밍 방식
snapshot2 = tracemalloc.take_snapshot()

# 비교
```

### 3. 결과 비교
- Neo4j에 저장된 노드/관계 개수 비교
- Bean 의존성 개수 비교
- 처리 시간 비교

## 예상 효과

| 항목 | 기존 | 스트리밍 | 개선율 |
|------|------|----------|--------|
| 메모리 | ~850MB | ~10-20MB | **97%** |
| 처리 시간 | 1분 32초 | 1분 40초 | -8% (허용) |
| 확장성 | ~1000 클래스 | ~10000 클래스 | **10배** |

## 주의사항

1. **JPA Queries 추출**
   - 현재는 메모리의 repositories에서 추출
   - 스트리밍: Neo4j에서 Repository 노드 조회 필요

2. **SQL Statements 추출**
   - 현재는 메모리의 mappers에서 추출
   - 스트리밍: Neo4j에서 Mapper 노드 조회 또는 파일별 즉시 처리

3. **하위 호환성**
   - 기존 방식도 유지 (환경 변수로 전환)
   - 점진적 마이그레이션 가능

## 구현 순서

1. ✅ 설계 문서 작성 (현재)
2. add_single_class_objects_streaming 함수 작성
3. parse_java_project_streaming 함수 작성
4. java_pipeline.py 통합
5. 테스트 실행 및 검증
6. 메모리 사용량 측정 및 비교
