"""
MyBatis-specific extraction and analysis helpers.
"""
from __future__ import annotations

import os
from dataclasses import asdict
from typing import Any, Dict, List, Optional

from csa.models.graph_entities import (
    Class,
    Method,
    MyBatisMapper,
    MyBatisResultMap,
    MyBatisSqlStatement,
    SqlStatement,
)
from csa.services.graph_db import GraphDB
from csa.services.sql_parser import SQLParser
from csa.utils.logger import get_logger


def extract_sql_statements_from_mappers(mybatis_mappers: list[MyBatisMapper], project_name: str) -> list[SqlStatement]:
    """
    MyBatis mappers에서 SQL statements를 추출하고 SQL 파서를 사용하여 분석합니다.
    
    Args:
        mybatis_mappers: MyBatis mapper 객체들의 리스트
        project_name: 프로젝트 이름
        
    Returns:
        SqlStatement 객체들의 리스트
    """
    sql_parser = SQLParser()
    sql_statements = []
    
    for mapper in mybatis_mappers:
        for sql_dict in mapper.sql_statements:
            sql_content = sql_dict.get('sql_content', '')
            sql_type = sql_dict.get('sql_type', '')
            
            sql_analysis = None
            if sql_content and sql_type:
                sql_analysis = sql_parser.parse_sql_statement(sql_content, sql_type)
            
            sql_statement = SqlStatement(
                id=sql_dict.get('id', ''),
                logical_name=sql_dict.get('logical_name', ''),
                sql_type=sql_type,
                sql_content=sql_content,
                parameter_type=sql_dict.get('parameter_type', ''),
                result_type=sql_dict.get('result_type', ''),
                result_map=sql_dict.get('result_map', ''),
                mapper_name=mapper.name,
                namespace=mapper.namespace,  # namespace 추가
                annotations=[],
                project_name=project_name
            )

            if sql_analysis:
                sql_analysis_dict = asdict(sql_analysis)
                sql_statement.sql_analysis = sql_analysis_dict
                sql_statement.tables = sql_analysis_dict.get('tables', [])
                sql_statement.columns = sql_analysis_dict.get('columns', [])
                sql_statement.complexity_score = sql_analysis_dict.get('complexity_score', 0)

                # 디버깅 로그: tables가 비어있는 경우 (DEBUG 레벨에서만 출력)
                if not sql_statement.tables:
                    from csa.utils.logger import get_logger
                    logger = get_logger(__name__)
                    logger.debug(
                        "SQL %s (%s) has no tables extracted. SQL content: %s",
                        sql_statement.id,
                        mapper.name,
                        sql_content[:200]
                    )
            elif sql_content and sql_type:
                # SQL content와 type이 있는데 파싱 실패한 경우만 경고
                from csa.utils.logger import get_logger
                logger = get_logger(__name__)
                logger.warning(
                    "Failed to parse SQL %s (%s, type=%s). SQL content: %s",
                    sql_dict.get('id', ''),
                    mapper.name,
                    sql_type,
                    sql_content[:200]
                )
            # SQL content가 비어있는 경우는 로그를 출력하지 않음 (정상 케이스)

            sql_statements.append(sql_statement)
    
    return sql_statements

def analyze_mybatis_resultmap_mapping(mybatis_mappers: list[MyBatisMapper], sql_statements: list[SqlStatement]) -> list[dict[str, Any]]:
    """
    MyBatis ResultMap과 테이블 컬럼 매핑을 분석합니다.
    
    Args:
        mybatis_mappers: MyBatis mapper 객체들의 리스트
        sql_statements: SQL statement 객체들의 리스트
        
    Returns:
        ResultMap 매핑 분석 결과 리스트
    """
    mapping_analysis = []
    
    for mapper in mybatis_mappers:
        if mapper.type == "xml":
            result_maps = getattr(mapper, 'result_maps', [])
            
            for result_map in result_maps:
                result_map_id = result_map.get('id', '')
                result_map_type = result_map.get('type', '')
                properties = result_map.get('properties', [])
                
                related_sqls = []
                for sql_stmt in sql_statements:
                    if sql_stmt.mapper_name == mapper.name and sql_stmt.result_map == result_map_id:
                        related_sqls.append(sql_stmt)
                
                mapping_info = {
                    'result_map_id': result_map_id,
                    'result_map_type': result_map_type,
                    'mapper_name': mapper.name,
                    'properties': properties,
                    'related_sqls': [sql.id for sql in related_sqls],
                    'table_column_mapping': {},
                    'mapping_completeness': 0.0,
                    'potential_issues': []
                }
                
                for sql_stmt in related_sqls:
                    if hasattr(sql_stmt, 'sql_analysis') and sql_stmt.sql_analysis:
                        table_column_mapping = sql_stmt.sql_analysis.get('tables', [])
                        for table_info in table_column_mapping:
                            table_name = table_info['name']
                            if table_name not in mapping_info['table_column_mapping']:
                                mapping_info['table_column_mapping'][table_name] = []
                            
                            columns = sql_stmt.sql_analysis.get('columns', [])
                            for col_info in columns:
                                col_name = col_info['name']
                                if col_name != '*' and col_name not in mapping_info['table_column_mapping'][table_name]:
                                    mapping_info['table_column_mapping'][table_name].append(col_name)
                
                total_properties = len(properties)
                mapped_properties = 0
                
                for prop in properties:
                    property_name = prop.get('property', '')
                    column_name = prop.get('column', '')
                    
                    if property_name and column_name:
                        mapped_properties += 1
                        
                        found_in_sql = False
                        for table_name, columns in mapping_info['table_column_mapping'].items():
                            if column_name in columns:
                                found_in_sql = True
                                break
                        
                        if not found_in_sql:
                            mapping_info['potential_issues'].append(
                                f"컬럼 '{column_name}'이 SQL에서 사용되지 않음"
                            )
                
                if total_properties > 0:
                    mapping_info['mapping_completeness'] = mapped_properties / total_properties
                
                mapping_analysis.append(mapping_info)
    
    return mapping_analysis

def analyze_sql_method_relationships(sql_statements: list[SqlStatement], classes: list[Class]) -> list[dict[str, Any]]:
    """
    SQL 문과 Java 메서드 간의 관계를 분석합니다.
    
    Args:
        sql_statements: SQL statement 객체들의 리스트
        classes: Java 클래스 객체들의 리스트
        
    Returns:
        SQL-메서드 관계 분석 결과 리스트
    """
    relationships = []
    
    class_method_map = {}
    for cls in classes:
        class_method_map[cls.name] = cls.methods
    
    for sql_stmt in sql_statements:
        mapper_name = sql_stmt.mapper_name
        
        mapper_class = None
        for cls in classes:
            if cls.name == mapper_name:
                mapper_class = cls
                break
        
        if not mapper_class:
            continue
        
        related_methods = []
        for method in mapper_class.methods:
            if method.name == sql_stmt.id:
                related_methods.append(method)
        
        relationship_info = {
            'sql_id': sql_stmt.id,
            'sql_type': sql_stmt.sql_type,
            'mapper_name': mapper_name,
            'related_methods': [],
            'table_access_pattern': {},
            'parameter_mapping': {},
            'return_type_mapping': {},
            'complexity_analysis': {}
        }
        
        for method in related_methods:
            method_info = {
                'name': method.name,
                'return_type': method.return_type,
                'parameters': [{'name': p.name, 'type': p.type} for p in method.parameters],
                'annotations': [ann.name for ann in method.annotations]
            }
            relationship_info['related_methods'].append(method_info)
        
        if hasattr(sql_stmt, 'sql_analysis') and sql_stmt.sql_analysis:
            tables = sql_stmt.sql_analysis.get('tables', [])
            for table_info in tables:
                table_name = table_info['name']
                relationship_info['table_access_pattern'][table_name] = {
                    'access_type': sql_stmt.sql_type,
                    'alias': table_info.get('alias'),
                    'join_type': table_info.get('type', 'main')
                }
        
        if hasattr(sql_stmt, 'sql_analysis') and sql_stmt.sql_analysis:
            parameters = sql_stmt.sql_analysis.get('parameters', [])
            for index, param in enumerate(parameters, start=1):
                # 파라미터 유형에 따라 제공되는 키가 달라 안전하게 접근한다.
                param_name = param.get('name') or f"{param.get('type', 'param')}_{index}"
                relationship_info['parameter_mapping'][param_name] = {
                    'type': param.get('type', 'unknown')
                }
                if 'pattern' in param:
                    relationship_info['parameter_mapping'][param_name]['pattern'] = param['pattern']
                if 'count' in param:
                    relationship_info['parameter_mapping'][param_name]['count'] = param['count']
        
        if hasattr(sql_stmt, 'complexity_score'):
            relationship_info['complexity_analysis'] = {
                'score': sql_stmt.complexity_score,
                'level': 'simple' if sql_stmt.complexity_score <= 3 else 
                        'medium' if sql_stmt.complexity_score <= 7 else
                        'complex' if sql_stmt.complexity_score <= 12 else 'very_complex'
            }
        
        relationships.append(relationship_info)
    
    return relationships

def generate_db_call_chain_analysis(sql_statements: list[SqlStatement], classes: list[Class]) -> dict[str, Any]:
    """
    데이터베이스 호출 체인을 분석합니다.
    
    Args:
        sql_statements: SQL statement 객체들의 리스트
        classes: Java 클래스 객체들의 리스트
        
    Returns:
        DB 호출 체인 분석 결과
    """
    analysis = {
        'total_sql_statements': len(sql_statements),
        'sql_type_distribution': {},
        'table_usage_statistics': {},
        'complexity_distribution': {},
        'mapper_usage_statistics': {},
        'call_chains': []
    }
    
    for sql_stmt in sql_statements:
        sql_type = sql_stmt.sql_type
        if sql_type not in analysis['sql_type_distribution']:
            analysis['sql_type_distribution'][sql_type] = 0
        analysis['sql_type_distribution'][sql_type] += 1
    
    for sql_stmt in sql_statements:
        if hasattr(sql_stmt, 'sql_analysis') and sql_stmt.sql_analysis:
            tables = sql_stmt.sql_analysis.get('tables', [])
            for table_info in tables:
                table_name = table_info['name']
                if table_name not in analysis['table_usage_statistics']:
                    analysis['table_usage_statistics'][table_name] = {
                        'access_count': 0,
                        'access_types': set(),
                        'mappers': set()
                    }
                
                analysis['table_usage_statistics'][table_name]['access_count'] += 1
                analysis['table_usage_statistics'][table_name]['access_types'].add(sql_stmt.sql_type)
                analysis['table_usage_statistics'][table_name]['mappers'].add(sql_stmt.mapper_name)
    
    for sql_stmt in sql_statements:
        if hasattr(sql_stmt, 'complexity_score'):
            score = sql_stmt.complexity_score
            level = 'simple' if score <= 3 else 'medium' if score <= 7 else 'complex' if score <= 12 else 'very_complex'
            
            if level not in analysis['complexity_distribution']:
                analysis['complexity_distribution'][level] = 0
            analysis['complexity_distribution'][level] += 1
    
    for sql_stmt in sql_statements:
        mapper_name = sql_stmt.mapper_name
        if mapper_name not in analysis['mapper_usage_statistics']:
            analysis['mapper_usage_statistics'][mapper_name] = {
                'sql_count': 0,
                'sql_types': set(),
                'tables_accessed': set()
            }
        
        analysis['mapper_usage_statistics'][mapper_name]['sql_count'] += 1
        analysis['mapper_usage_statistics'][mapper_name]['sql_types'].add(sql_stmt.sql_type)
        
        if hasattr(sql_stmt, 'sql_analysis') and sql_stmt.sql_analysis:
            tables = sql_stmt.sql_analysis.get('tables', [])
            for table_info in tables:
                analysis['mapper_usage_statistics'][mapper_name]['tables_accessed'].add(table_info['name'])
    
    for sql_stmt in sql_statements:
        call_chain = {
            'sql_id': sql_stmt.id,
            'sql_type': sql_stmt.sql_type,
            'mapper_name': sql_stmt.mapper_name,
            'tables': [],
            'complexity_score': getattr(sql_stmt, 'complexity_score', 0)
        }
        
        if hasattr(sql_stmt, 'sql_analysis') and sql_stmt.sql_analysis:
            tables = sql_stmt.sql_analysis.get('tables', [])
            call_chain['tables'] = [table['name'] for table in tables]
        
        analysis['call_chains'].append(call_chain)
    
    return analysis

def extract_mybatis_mappers_from_classes(classes: list[Class]) -> list[MyBatisMapper]:
    """Extract MyBatis Mappers from parsed classes.
    
    Args:
        classes: List of parsed Class objects
        
    Returns:
        List of MyBatisMapper objects
    """
    mappers = []
    
    for cls in classes:
        is_mapper = any(ann.name == "Mapper" for ann in cls.annotations)
        
        if not is_mapper:
            continue
        
        mapper_methods = []
        sql_statements = []
        
        for method in cls.methods:
            if method.name == cls.name:
                continue
            
            mybatis_annotations = [ann for ann in method.annotations if ann.category == "mybatis"]
            
            
            sql_type = "SELECT"  # default
            sql_content = ""
            parameter_type = ""
            result_type = ""
            result_map = ""
            
            if mybatis_annotations:
                for ann in mybatis_annotations:
                    if ann.name in ["Select", "SelectProvider"]:
                        sql_type = "SELECT"
                        if "value" in ann.parameters:
                            sql_content = ann.parameters["value"]
                    elif ann.name in ["Insert", "InsertProvider"]:
                        sql_type = "INSERT"
                        if "value" in ann.parameters:
                            sql_content = ann.parameters["value"]
                    elif ann.name in ["Update", "UpdateProvider"]:
                        sql_type = "UPDATE"
                        if "value" in ann.parameters:
                            sql_content = ann.parameters["value"]
                    elif ann.name in ["Delete", "DeleteProvider"]:
                        sql_type = "DELETE"
                        if "value" in ann.parameters:
                            sql_content = ann.parameters["value"]
                    
                    if "parameterType" in ann.parameters:
                        parameter_type = ann.parameters["parameterType"]
                    if "resultType" in ann.parameters:
                        result_type = ann.parameters["resultType"]
                    if "resultMap" in ann.parameters:
                        result_map = ann.parameters["resultMap"]
            else:
                method_name_lower = method.name.lower()
                if any(keyword in method_name_lower for keyword in ['find', 'get', 'select', 'search', 'list']):
                    sql_type = "SELECT"
                elif any(keyword in method_name_lower for keyword in ['save', 'insert', 'create', 'add']):
                    sql_type = "INSERT"
                elif any(keyword in method_name_lower for keyword in ['update', 'modify', 'change']):
                    sql_type = "UPDATE"
                elif any(keyword in method_name_lower for keyword in ['delete', 'remove']):
                    sql_type = "DELETE"
            
            method_info = {
                "name": method.name,
                "return_type": method.return_type,
                "parameters": [{"name": p.name, "type": p.type} for p in method.parameters],
                "annotations": [ann.name for ann in mybatis_annotations]
            }
            mapper_methods.append(method_info)
            
            sql_statement = {
                "id": method.name,
                "sql_type": sql_type,
                "sql_content": sql_content,
                "parameter_type": parameter_type,
                "result_type": result_type,
                "result_map": result_map,
                "annotations": [ann.name for ann in mybatis_annotations]
            }
            sql_statements.append(sql_statement)
        
        # Create mapper
        mapper = MyBatisMapper(
            name=cls.name,
            logical_name="",
            type="interface",
            namespace=f"{cls.package_name}.{cls.name}",
            methods=mapper_methods,
            sql_statements=sql_statements,
            file_path=cls.file_path,
            package_name=cls.package_name
        )
        mappers.append(mapper)
    
    return mappers

__all__ = [
    "analyze_mybatis_resultmap_mapping",
    "analyze_sql_method_relationships",
    "extract_mybatis_mappers_from_classes",
    "extract_mybatis_xml_mappers",
    "extract_sql_statements_from_mappers",
    "generate_db_call_chain_analysis",
    "parse_mybatis_xml_file",
]

def parse_mybatis_xml_file(file_path: str) -> MyBatisMapper:
    """Parse MyBatis XML mapper file.
    
    Args:
        file_path: Path to the XML mapper file
        
    Returns:
        MyBatisMapper object
    """
    import xml.etree.ElementTree as ET
    logger = get_logger(__name__)
    
    try:
        # XML 원본 파일 읽기 (주석 추출용)
        with open(file_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()
        
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        namespace = root.get("namespace", "")
        
        # Mapper 논리명 추출
        from csa.services.java_parser_addon_r001 import extract_mapper_logical_name_from_xml_content
        mapper_logical_name = extract_mapper_logical_name_from_xml_content(xml_content, namespace)
        
        sql_statements = []
        for statement in root.findall(".//*[@id]"):
            statement_id = statement.get("id")
            tag_name = statement.tag.lower()
            
            sql_type = "SELECT"
            if tag_name == "insert":
                sql_type = "INSERT"
            elif tag_name == "update":
                sql_type = "UPDATE"
            elif tag_name == "delete":
                sql_type = "DELETE"
            
            # SQL 내용 추출 - CDATA와 하위 요소들 포함
            sql_content = ""
            if statement.text:
                sql_content += statement.text.strip()
            
            # 하위 요소들의 텍스트도 포함
            for child in statement:
                if child.text:
                    sql_content += " " + child.text.strip()
                if child.tail:
                    sql_content += " " + child.tail.strip()
            
            # CDATA 섹션 처리
            if not sql_content:
                # CDATA가 있는 경우를 위해 전체 텍스트 추출
                import xml.etree.ElementTree as ET
                sql_content = ET.tostring(statement, encoding='unicode', method='text').strip()
            
            sql_content = sql_content.strip()
            
            parameter_type = statement.get("parameterType", "")
            result_type = statement.get("resultType", "")
            result_map = statement.get("resultMap", "")
            
            # SQL 논리명 추출
            from csa.services.java_parser_addon_r001 import extract_sql_logical_name_from_xml_content
            sql_logical_name = extract_sql_logical_name_from_xml_content(xml_content, statement_id)
            
            sql_statement = {
                "id": statement_id,
                "logical_name": sql_logical_name if sql_logical_name else "",
                "sql_type": sql_type,
                "sql_content": sql_content,
                "parameter_type": parameter_type,
                "result_type": result_type,
                "result_map": result_map,
                "annotations": []
            }
            sql_statements.append(sql_statement)
        
        result_maps = []
        for result_map in root.findall(".//resultMap"):
            result_map_id = result_map.get("id")
            result_map_type = result_map.get("type", "")
            
            properties = []
            for property_elem in result_map.findall(".//result"):
                prop = {
                    "property": property_elem.get("property", ""),
                    "column": property_elem.get("column", ""),
                    "jdbc_type": property_elem.get("jdbcType", "")
                }
                properties.append(prop)
            
            result_map_info = {
                "id": result_map_id,
                "type": result_map_type,
                "properties": properties,
                "associations": [],
                "collections": []
            }
            result_maps.append(result_map_info)
        
        # Create mapper
        mapper_name = namespace.split(".")[-1] if namespace else os.path.basename(file_path).replace(".xml", "")
        package_name = ".".join(namespace.split(".")[:-1]) if namespace else ""
        
        mapper = MyBatisMapper(
            name=mapper_name,
            logical_name=mapper_logical_name if mapper_logical_name else "",
            type="xml",
            namespace=namespace,
            methods=[],  # XML mappers don't have Java methods
            sql_statements=sql_statements,
            file_path=file_path,
            package_name=package_name
        )
        
        return mapper
        
    except ET.ParseError as e:
        logger.error(f"Error parsing XML file {file_path}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error reading XML file {file_path}: {e}")
        return None

def extract_mybatis_xml_mappers(directory: str, project_name: str = "", graph_db: GraphDB = None) -> list[MyBatisMapper]:
    """Extract MyBatis XML mappers from directory.
    
    Args:
        directory: Directory to search for XML mapper files
        project_name: Project name for logical name extraction
        graph_db: GraphDB instance for logical name extraction
        
    Returns:
        List of MyBatisMapper objects
    """
    mappers = []
    
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith("Mapper.xml") or file.endswith("Dao.xml"):
                file_path = os.path.join(root, file)
                mapper = parse_mybatis_xml_file(file_path)
                if mapper:
                    mappers.append(mapper)
                    # Rule001 논리명 추출 로직 제거 - 이미 파싱 시 처리됨
    
    return mappers

