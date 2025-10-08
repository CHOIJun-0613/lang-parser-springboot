"""
Java Parser Addon R001 사용 예시
프로젝트별 논리명 추출 규칙을 사용한 Java 객체 분석 예시
"""

import os
from csa.services.graph_db import GraphDB
from csa.services.java_parser_addon_r001 import (
    LogicalNameExtractorFactory,
    process_java_file_with_rule001,
    process_mybatis_xml_with_rule001,
    process_project_with_custom_rules,
    get_file_type
)

def example_usage():
    """사용 예시"""
    
    # Neo4j 연결 설정
    graph_db = GraphDB(
        uri="neo4j://127.0.0.1:7687",
        user="neo4j",
        password="devpass123"
    )
    
    project_name = "car-center-devlab"
    
    print("=== Java Parser Addon R001 사용 예시 ===")
    
    # 1. 프로젝트별 논리명 추출기 생성
    print("\n1. 프로젝트별 논리명 추출기 생성")
    java_extractor = LogicalNameExtractorFactory.create_extractor(project_name, 'java')
    print(f"Java 추출기 생성 완료: {project_name}")
    
    mybatis_extractor = LogicalNameExtractorFactory.create_extractor(project_name, 'mybatis_xml')
    print(f"MyBatis XML 추출기 생성 완료: {project_name}")
    
    # 2. 단일 Java 파일 처리
    print("\n2. 단일 Java 파일 처리")
    java_file_path = "tests/sample_java_project/Main.java"
    if os.path.exists(java_file_path):
        success = process_java_file_with_rule001(java_file_path, project_name, graph_db)
        print(f"Java 파일 처리 결과: {'성공' if success else '실패'}")
    
    # 3. 단일 MyBatis XML 파일 처리
    print("\n3. 단일 MyBatis XML 파일 처리")
    xml_file_path = "tests/sample_mybatis_project/UserMapper.xml"
    if os.path.exists(xml_file_path):
        success = process_mybatis_xml_with_rule001(xml_file_path, project_name, graph_db)
        print(f"MyBatis XML 파일 처리 결과: {'성공' if success else '실패'}")
    
    # 4. 파일 타입 자동 감지
    print("\n4. 파일 타입 자동 감지")
    test_files = [
        "tests/sample_java_project/Main.java",
        "tests/sample_mybatis_project/UserMapper.xml",
        "tests/sample_java_project/Parent.java"
    ]
    
    for file_path in test_files:
        if os.path.exists(file_path):
            file_type = get_file_type(file_path)
            print(f"파일: {file_path} -> 타입: {file_type}")
    
    # 5. 프로젝트별 커스텀 규칙으로 파일 처리
    print("\n5. 프로젝트별 커스텀 규칙으로 파일 처리")
    for file_path in test_files:
        if os.path.exists(file_path):
            file_type = get_file_type(file_path)
            if file_type in ['java', 'mybatis_xml']:
                success = process_project_with_custom_rules(project_name, file_path, file_type, graph_db)
                print(f"파일 처리 결과: {file_path} -> {'성공' if success else '실패'}")
    
    # 6. 규칙 파일 확인
    print("\n6. 규칙 파일 확인")
    rule_files = [
        "csa/rules/rule001_extraction_logical_name.md",
        f"csa/rules/{project_name}_logical_name_rules.md"
    ]
    
    for rule_file in rule_files:
        if os.path.exists(rule_file):
            print(f"규칙 파일 존재: {rule_file}")
        else:
            print(f"규칙 파일 없음: {rule_file}")
    
    print("\n=== 사용 예시 완료 ===")
    
    # 연결 종료
    graph_db.close()

def test_logical_name_extraction():
    """논리명 추출 테스트"""
    
    print("\n=== 논리명 추출 테스트 ===")
    
    project_name = "car-center-devlab"
    java_extractor = LogicalNameExtractorFactory.create_extractor(project_name, 'java')
    
    # 테스트용 Java 소스 코드
    test_java_source = '''
package com.example.controller;

/**
 * 사용자 관리 컨트롤러
 */
@RestController
public class UserController {
    
    /**
     * 사용자 정보 조회
     */
    @GetMapping("/users/{id}")
    public ResponseEntity<User> getUser(@PathVariable Long id) {
        return ResponseEntity.ok(userService.findById(id));
    }
    
    /**
     * 사용자 생성
     */
    @PostMapping("/users")
    public ResponseEntity<User> createUser(@RequestBody User user) {
        return ResponseEntity.ok(userService.save(user));
    }
}
'''
    
    # 클래스 논리명 추출 테스트
    class_logical_name = java_extractor.extract_class_logical_name(test_java_source, "UserController")
    print(f"클래스 논리명: {class_logical_name}")
    
    # 메서드 논리명 추출 테스트
    method_logical_name = java_extractor.extract_method_logical_name(test_java_source, "getUser")
    print(f"getUser 메서드 논리명: {method_logical_name}")
    
    method_logical_name2 = java_extractor.extract_method_logical_name(test_java_source, "createUser")
    print(f"createUser 메서드 논리명: {method_logical_name2}")
    
    print("\n=== 논리명 추출 테스트 완료 ===")

if __name__ == "__main__":
    # 사용 예시 실행
    example_usage()
    
    # 논리명 추출 테스트 실행
    test_logical_name_extraction()
