import os
import yaml
import re
from pathlib import Path

import javalang

from src.models.graph_entities import Class, Method, MethodCall, Field, Package, Annotation, Bean, BeanDependency, Endpoint, MyBatisMapper, MyBatisSqlStatement, MyBatisResultMap, SqlStatement, JpaEntity, JpaColumn, JpaRelationship, JpaRepository, JpaQuery, ConfigFile, DatabaseConfig, ServerConfig, SecurityConfig, LoggingConfig, TestClass, TestMethod, TestConfiguration, Table
from src.services.sql_parser import SQLParser
from src.utils.logger import get_logger
from typing import Optional, List, Literal, Any


def extract_project_name(java_source_folder: str) -> str:
    """
    JAVA_SOURCE_FOLDER 경로에서 프로젝트 이름을 추출합니다.
    
    Args:
        java_source_folder: Java 소스 폴더 경로
        
    Returns:
        프로젝트 이름 (마지막 디렉토리명)
    """
    path = Path(java_source_folder).resolve()
    return path.name


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
                sql_type=sql_type,
                sql_content=sql_content,
                parameter_type=sql_dict.get('parameter_type', ''),
                result_type=sql_dict.get('result_type', ''),
                result_map=sql_dict.get('result_map', ''),
                mapper_name=mapper.name,
                annotations=[],
                project_name=project_name
            )
            
            if sql_analysis:
                sql_statement.sql_analysis = sql_analysis
                sql_statement.tables = sql_analysis.get('tables', [])
                sql_statement.columns = sql_analysis.get('columns', [])
                sql_statement.complexity_score = sql_analysis.get('complexity_score', 0)
            
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
            for param in parameters:
                param_name = param['name']
                relationship_info['parameter_mapping'][param_name] = {
                    'type': param['type'],
                    'pattern': param['pattern']
                }
        
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


def parse_annotations(annotations, target_type: str = "class") -> list[Annotation]:
    """Parse Java annotations into Annotation objects.
    
    Args:
        annotations: List of annotation nodes from javalang
        target_type: Type of target ("class", "method", "field")
    """
    result = []
    for annotation in annotations:
        annotation_name = annotation.name
        parameters = {}
        
        if hasattr(annotation, 'element') and annotation.element:
            for element in annotation.element:
                if hasattr(element, 'name') and hasattr(element, 'value'):
                    parameters[element.name] = element.value.value if hasattr(element.value, 'value') else str(element.value)
        
        result.append(Annotation(
            name=annotation_name,
            parameters=parameters,
            target_type=target_type,
            category=classify_springboot_annotation(annotation_name)
        ))
    
    return result


def classify_springboot_annotation(annotation_name: str) -> str:
    """Classify SpringBoot annotations into categories.
    
    Args:
        annotation_name: Name of the annotation (e.g., "@Component", "@Service")
        
    Returns:
        Category of the annotation
    """
    component_annotations = {
        "Component", "Service", "Repository", "Controller", 
        "RestController", "Configuration", "Bean"
    }
    
    injection_annotations = {
        "Autowired", "Resource", "Value", "Qualifier", "Primary"
    }
    
    web_annotations = {
        "RequestMapping", "GetMapping", "PostMapping", "PutMapping", 
        "DeleteMapping", "PatchMapping", "RequestParam", "PathVariable",
        "RequestBody", "ResponseBody", "ResponseStatus"
    }
    
    jpa_annotations = {
        "Entity", "Table", "MappedSuperclass", "Embeddable", "Embedded",
        
        "Id", "GeneratedValue", "SequenceGenerator", "TableGenerator",
        
        "Column", "Basic", "Transient", "Enumerated", "Temporal", "Lob",
        
        "OneToOne", "OneToMany", "ManyToOne", "ManyToMany",
        "JoinColumn", "JoinColumns", "JoinTable", "PrimaryKeyJoinColumn", "PrimaryKeyJoinColumns",
        
        "ElementCollection", "CollectionTable", "OrderBy", "OrderColumn",
        "MapKey", "MapKeyClass", "MapKeyColumn", "MapKeyJoinColumn", "MapKeyJoinColumns",
        "MapKeyTemporal", "MapKeyEnumerated",
        
        "Inheritance", "DiscriminatorColumn", "DiscriminatorValue",
        
        "SecondaryTable", "SecondaryTables", "AttributeOverride", "AttributeOverrides",
        "AssociationOverride", "AssociationOverrides",
        
        "NamedQuery", "NamedQueries", "NamedNativeQuery", "NamedNativeQueries",
        "SqlResultSetMapping", "SqlResultSetMappings", "ConstructorResult", "ColumnResult",
        "FieldResult", "EntityResult", "EntityResults",
        
        "Cacheable",
        
        "Version",
        
        "Access",
        
        "UniqueConstraint", "Index", "ForeignKey"
    }
    
    test_annotations = {
        "Test", "SpringBootTest", "DataJpaTest", "WebMvcTest",
        "MockBean", "SpyBean", "TestPropertySource"
    }
    
    security_annotations = {
        "PreAuthorize", "PostAuthorize", "Secured", "RolesAllowed",
        "EnableWebSecurity", "EnableGlobalMethodSecurity"
    }
    
    validation_annotations = {
        "Valid", "NotNull", "NotBlank", "NotEmpty", "Size", "Min", "Max",
        "Pattern", "Email", "AssertTrue", "AssertFalse"
    }
    
    mybatis_annotations = {
        "Mapper", "Select", "Insert", "Update", "Delete", "SelectProvider",
        "InsertProvider", "UpdateProvider", "DeleteProvider", "Results",
        "Result", "One", "Many", "MapKey", "Options", "SelectKey"
    }
    
    if annotation_name in component_annotations:
        return "component"
    elif annotation_name in injection_annotations:
        return "injection"
    elif annotation_name in web_annotations:
        return "web"
    elif annotation_name in jpa_annotations:
        return "jpa"
    elif annotation_name in test_annotations:
        return "test"
    elif annotation_name in security_annotations:
        return "security"
    elif annotation_name in validation_annotations:
        return "validation"
    elif annotation_name in mybatis_annotations:
        return "mybatis"
    else:
        return "other"


def classify_test_annotation(annotation_name: str) -> str:
    """Classify test annotations into categories.
    
    Args:
        annotation_name: Name of the annotation
        
    Returns:
        Category of the test annotation
    """
    junit_annotations = {
        "Test", "BeforeEach", "AfterEach", "BeforeAll", "AfterAll",
        "DisplayName", "ParameterizedTest", "ValueSource", "CsvSource",
        "MethodSource", "Timeout", "Disabled", "Nested", "RepeatedTest",
        "Order", "TestMethodOrder", "TestInstance", "TestClassOrder"
    }
    
    spring_test_annotations = {
        "SpringBootTest", "WebMvcTest", "DataJpaTest", "DataJdbcTest",
        "JdbcTest", "JsonTest", "RestClientTest", "WebFluxTest",
        "MockBean", "SpyBean", "TestConfiguration", "ActiveProfiles",
        "TestPropertySource", "DirtiesContext", "Transactional",
        "Rollback", "Commit", "Sql", "SqlGroup", "AutoConfigureTestDatabase",
        "AutoConfigureMockMvc", "AutoConfigureWebMvc", "AutoConfigureWebClient",
        "MockMvc", "TestEntityManager", "TestContainers", "DynamicPropertySource"
    }
    
    testng_annotations = {
        "TestNG", "BeforeMethod", "AfterMethod", "BeforeClass", "AfterClass",
        "BeforeSuite", "AfterSuite", "BeforeGroups", "AfterGroups",
        "DataProvider", "Parameters", "Groups", "Priority", "DependsOnMethods",
        "DependsOnGroups", "ExpectedExceptions", "InvocationCount",
        "SuccessPercentage", "TimeOut"
    }
    
    mockito_annotations = {
        "Mock", "Spy", "InjectMocks", "Captor", "MockedStatic"
    }
    
    assertj_annotations = {
        "AssertJ"
    }
    
    other_test_annotations = {
        "Ignore", "Category", "RunWith", "ExtendWith", "ContextConfiguration"
    }
    
    if annotation_name in junit_annotations:
        return "junit"
    elif annotation_name in spring_test_annotations:
        return "spring_test"
    elif annotation_name in testng_annotations:
        return "testng"
    elif annotation_name in mockito_annotations:
        return "mockito"
    elif annotation_name in assertj_annotations:
        return "assertj"
    elif annotation_name in other_test_annotations:
        return "other_test"
    else:
        return "other"


def extract_beans_from_classes(classes: list[Class]) -> list[Bean]:
    """Extract Spring Beans from parsed classes.
    
    Args:
        classes: List of parsed Class objects
        
    Returns:
        List of Bean objects
    """
    beans = []
    
    for cls in classes:
        component_annotations = [ann for ann in cls.annotations if ann.category == "component"]
        
        has_repository_annotation = any(ann.name == "Repository" for ann in cls.annotations)
        
        if component_annotations or has_repository_annotation:
            bean_type = "component"  # default
            if any(ann.name in ["Service", "Service"] for ann in cls.annotations):
                bean_type = "service"
            elif any(ann.name in ["Repository", "Repository"] for ann in cls.annotations):
                bean_type = "repository"
            elif any(ann.name in ["Controller", "RestController"] for ann in cls.annotations):
                bean_type = "controller"
            elif any(ann.name in ["Configuration", "Configuration"] for ann in cls.annotations):
                bean_type = "configuration"
            
            scope = "singleton"
            for ann in cls.annotations:
                if ann.name == "Scope":
                    if "value" in ann.parameters:
                        scope = ann.parameters["value"]
                    elif "prototype" in str(ann.parameters):
                        scope = "prototype"
                    elif "request" in str(ann.parameters):
                        scope = "request"
                    elif "session" in str(ann.parameters):
                        scope = "session"
            
            bean_name = cls.name[0].lower() + cls.name[1:] if cls.name else cls.name
            
            bean_methods = []
            if bean_type == "configuration":
                for method in cls.methods:
                    if any(ann.name == "Bean" for ann in method.annotations):
                        bean_methods.append(method)
            
            bean = Bean(
                name=bean_name,
                type=bean_type,
                scope=scope,
                class_name=cls.name,
                package_name=cls.package_name,
                annotation_names=[ann.name for ann in cls.annotations] if cls.annotations else [],
                method_count=len(bean_methods) if bean_type == "configuration" else len(cls.methods) if cls.methods else 0,
                property_count=len(cls.properties) if cls.properties else 0
            )
            beans.append(bean)
    
    return beans


def analyze_bean_dependencies(classes: list[Class], beans: list[Bean]) -> list[BeanDependency]:
    """Analyze dependencies between Spring Beans.
    
    Args:
        classes: List of parsed Class objects
        beans: List of Bean objects
        
    Returns:
        List of BeanDependency objects
    """
    dependencies = []
    
    class_to_bean = {}
    for bean in beans:
        class_to_bean[bean.class_name] = bean.name
    
    for cls in classes:
        if cls.name not in class_to_bean:
            continue
            
        source_bean = class_to_bean[cls.name]
        
        for prop in cls.properties:
            if any(ann.category == "injection" for ann in prop.annotations):
                target_bean = None
                field_type = prop.type
                
                if field_type in class_to_bean:
                    target_bean = class_to_bean[field_type]
                else:
                    for bean in beans:
                        if field_type == bean.class_name:
                            target_bean = bean.name
                            break
                
                if target_bean:
                    injection_type = "field"
                    for ann in prop.annotations:
                        if ann.name == "Autowired":
                            injection_type = "field"
                        elif ann.name == "Resource":
                            injection_type = "field"
                        elif ann.name == "Value":
                            injection_type = "field"
                    
                    dependency = BeanDependency(
                        source_bean=source_bean,
                        target_bean=target_bean,
                        injection_type=injection_type,
                        field_name=prop.name
                    )
                    dependencies.append(dependency)
        
        for method in cls.methods:
            if method.name == cls.name:  # Constructor
                for param in method.parameters:
                    if any(ann.category == "injection" for ann in param.annotations):
                        target_bean = None
                        param_type = param.type
                        
                        if param_type in class_to_bean:
                            target_bean = class_to_bean[param_type]
                        else:
                            for bean in beans:
                                if param_type == bean.class_name:
                                    target_bean = bean.name
                                    break
                        
                        if target_bean:
                            dependency = BeanDependency(
                                source_bean=source_bean,
                                target_bean=target_bean,
                                injection_type="constructor",
                                parameter_name=param.name
                            )
                            dependencies.append(dependency)
        
        for method in cls.methods:
            if method.name.startswith("set") and len(method.parameters) == 1:
                if any(ann.category == "injection" for ann in method.annotations):
                    param = method.parameters[0]
                    target_bean = None
                    param_type = param.type
                    
                    if param_type in class_to_bean:
                        target_bean = class_to_bean[param_type]
                    else:
                        for bean in beans:
                            if param_type == bean.class_name:
                                target_bean = bean.name
                                break
                    
                    if target_bean:
                        dependency = BeanDependency(
                            source_bean=source_bean,
                            target_bean=target_bean,
                            injection_type="setter",
                            method_name=method.name,
                            parameter_name=param.name
                        )
                        dependencies.append(dependency)
    
    return dependencies


def extract_endpoints_from_classes(classes: list[Class]) -> list[Endpoint]:
    """Extract REST API endpoints from controller classes.
    
    Args:
        classes: List of parsed Class objects
        
    Returns:
        List of Endpoint objects
    """
    endpoints = []
    
    for cls in classes:
        is_controller = any(ann.name in ["Controller", "RestController"] for ann in cls.annotations)
        
        if not is_controller:
            continue
            
        class_path = ""
        for ann in cls.annotations:
            if ann.name == "RequestMapping":
                if "value" in ann.parameters:
                    class_path = ann.parameters["value"]
                break
        
        for method in cls.methods:
            if method.name == cls.name:
                continue
                
            web_annotations = [ann for ann in method.annotations if ann.category == "web"]
            
            if not web_annotations:
                continue
            
            endpoint_path = ""
            http_method = "GET"  # default
            
            for ann in web_annotations:
                if ann.name in ["RequestMapping", "GetMapping", "PostMapping", "PutMapping", "DeleteMapping", "PatchMapping"]:
                    if "value" in ann.parameters:
                        endpoint_path = ann.parameters["value"]
                    elif "path" in ann.parameters:
                        endpoint_path = ann.parameters["path"]
                    
                    if ann.name == "GetMapping":
                        http_method = "GET"
                    elif ann.name == "PostMapping":
                        http_method = "POST"
                    elif ann.name == "PutMapping":
                        http_method = "PUT"
                    elif ann.name == "DeleteMapping":
                        http_method = "DELETE"
                    elif ann.name == "PatchMapping":
                        http_method = "PATCH"
                    elif ann.name == "RequestMapping":
                        if "method" in ann.parameters:
                            method_value = ann.parameters["method"]
                            if isinstance(method_value, list) and len(method_value) > 0:
                                http_method = method_value[0]
                            else:
                                http_method = str(method_value)
                        else:
                            http_method = "GET"  # default for RequestMapping
                    break
            
            full_path = class_path
            if endpoint_path:
                if full_path and not full_path.endswith("/") and not endpoint_path.startswith("/"):
                    full_path += "/"
                full_path += endpoint_path
            elif not full_path:
                full_path = "/"
            
            parameters = []
            for param in method.parameters:
                param_info = {
                    "name": param.name,
                    "type": param.type,
                    "annotations": [ann.name for ann in param.annotations if ann.category == "web"]
                }
                parameters.append(param_info)
            
            return_type = method.return_type if method.return_type != "constructor" else "void"
            
            endpoint = Endpoint(
                path=endpoint_path or "/",
                method=http_method,
                controller_class=cls.name,
                handler_method=method.name,
                parameters=parameters,
                return_type=return_type,
                annotations=[ann.name for ann in web_annotations],
                full_path=full_path
            )
            endpoints.append(endpoint)
    
    return endpoints


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
            type="interface",
            namespace=f"{cls.package_name}.{cls.name}",
            methods=mapper_methods,
            sql_statements=sql_statements,
            file_path=cls.file_path,
            package_name=cls.package_name
        )
        mappers.append(mapper)
    
    return mappers


def parse_mybatis_xml_file(file_path: str) -> MyBatisMapper:
    """Parse MyBatis XML mapper file.
    
    Args:
        file_path: Path to the XML mapper file
        
    Returns:
        MyBatisMapper object
    """
    import xml.etree.ElementTree as ET
    
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        namespace = root.get("namespace", "")
        
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
            
            sql_content = statement.text.strip() if statement.text else ""
            
            parameter_type = statement.get("parameterType", "")
            result_type = statement.get("resultType", "")
            result_map = statement.get("resultMap", "")
            
            sql_statement = {
                "id": statement_id,
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
            type="xml",
            namespace=namespace,
            methods=[],  # XML mappers don't have Java methods
            sql_statements=sql_statements,
            file_path=file_path,
            package_name=package_name
        )
        
        return mapper
        
    except ET.ParseError as e:
        print(f"Error parsing XML file {file_path}: {e}")
        return None
    except Exception as e:
        print(f"Error reading XML file {file_path}: {e}")
        return None


def extract_mybatis_xml_mappers(directory: str) -> list[MyBatisMapper]:
    """Extract MyBatis XML mappers from directory.
    
    Args:
        directory: Directory to search for XML mapper files
        
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
    
    return mappers


def extract_jpa_entities_from_classes(classes: list[Class]) -> list[JpaEntity]:
    """Extract JPA Entities from parsed classes with enhanced analysis.
    
    Args:
        classes: List of parsed Class objects
        
    Returns:
        List of JpaEntity objects
    """
    entities = []
    
    for cls in classes:
        is_entity = any(ann.name == "Entity" for ann in cls.annotations)
        
        if not is_entity:
            continue
        
        table_info = _extract_table_info(cls)
        
        columns = []
        relationships = []
        
        for prop in cls.properties:
            jpa_annotations = [ann for ann in prop.annotations if ann.category == "jpa"]
            
            if jpa_annotations or _is_jpa_property(prop, cls):
                column_info = _extract_column_info(prop, jpa_annotations)
                if column_info:
                    columns.append(column_info)
                
                relationship_info = _extract_relationship_info(prop, jpa_annotations)
                if relationship_info:
                    relationships.append(relationship_info)
        
        entity = JpaEntity(
            name=cls.name,
            table_name=table_info["name"],
            columns=columns,
            relationships=relationships,
            annotations=[ann.name for ann in cls.annotations if ann.category == "jpa"],
            package_name=cls.package_name,
            file_path=cls.file_path,
            description=table_info.get("description", ""),
            ai_description=table_info.get("ai_description", "")
        )
        entities.append(entity)
    
    return entities


def _extract_table_info(cls: Class) -> dict:
    """Extract table information from entity class annotations."""
    table_name = cls.name.lower()  # default table name
    schema = ""
    catalog = ""
    unique_constraints = []
    indexes = []
    description = ""
    
    for ann in cls.annotations:
        if ann.name == "Table":
            if "name" in ann.parameters:
                table_name = ann.parameters["name"]
            if "schema" in ann.parameters:
                schema = ann.parameters["schema"]
            if "catalog" in ann.parameters:
                catalog = ann.parameters["catalog"]
            if "uniqueConstraints" in ann.parameters:
                unique_constraints = ann.parameters["uniqueConstraints"]
            if "indexes" in ann.parameters:
                indexes = ann.parameters["indexes"]
    
    return {
        "name": table_name,
        "schema": schema,
        "catalog": catalog,
        "unique_constraints": unique_constraints,
        "indexes": indexes,
        "description": description
    }


def _is_jpa_property(prop: Field, cls: Class) -> bool:
    """Check if a property should be considered as JPA property even without explicit annotations."""
    has_transient = any(ann.name == "Transient" for ann in prop.annotations)
    return not has_transient


def _extract_column_info(prop: Field, jpa_annotations: list[Annotation]) -> dict:
    """Extract detailed column information from property and annotations."""
    column_name = prop.name  # default column name
    nullable = True
    unique = False
    length = 0
    precision = 0
    scale = 0
    insertable = True
    updatable = True
    column_definition = ""
    table = ""
    is_primary_key = False
    is_version = False
    is_lob = False
    is_enumerated = False
    is_temporal = False
    temporal_type = ""
    enum_type = ""
    
    for ann in jpa_annotations:
        if ann.name == "Column":
            if "name" in ann.parameters:
                column_name = ann.parameters["name"]
            if "nullable" in ann.parameters:
                nullable = ann.parameters["nullable"]
            if "unique" in ann.parameters:
                unique = ann.parameters["unique"]
            if "length" in ann.parameters:
                length = ann.parameters["length"]
            if "precision" in ann.parameters:
                precision = ann.parameters["precision"]
            if "scale" in ann.parameters:
                scale = ann.parameters["scale"]
            if "insertable" in ann.parameters:
                insertable = ann.parameters["insertable"]
            if "updatable" in ann.parameters:
                updatable = ann.parameters["updatable"]
            if "columnDefinition" in ann.parameters:
                column_definition = ann.parameters["columnDefinition"]
            if "table" in ann.parameters:
                table = ann.parameters["table"]
                
        elif ann.name == "Id":
            column_name = "id"  # Primary key column
            nullable = False
            unique = True
            is_primary_key = True
            
        elif ann.name == "Version":
            is_version = True
            
        elif ann.name == "Lob":
            is_lob = True
            
        elif ann.name == "Enumerated":
            is_enumerated = True
            if "value" in ann.parameters:
                enum_type = ann.parameters["value"]
                
        elif ann.name == "Temporal":
            is_temporal = True
            if "value" in ann.parameters:
                temporal_type = ann.parameters["value"]
                
        elif ann.name == "JoinColumn":
            if "name" in ann.parameters:
                column_name = ann.parameters["name"]
            if "nullable" in ann.parameters:
                nullable = ann.parameters["nullable"]
            if "unique" in ann.parameters:
                unique = ann.parameters["unique"]
            if "insertable" in ann.parameters:
                insertable = ann.parameters["insertable"]
            if "updatable" in ann.parameters:
                updatable = ann.parameters["updatable"]
            if "columnDefinition" in ann.parameters:
                column_definition = ann.parameters["columnDefinition"]
    
    return {
        "property_name": prop.name,
        "column_name": column_name,
        "data_type": prop.type,
        "nullable": nullable,
        "unique": unique,
        "length": length,
        "precision": precision,
        "scale": scale,
        "insertable": insertable,
        "updatable": updatable,
        "column_definition": column_definition,
        "table": table,
        "is_primary_key": is_primary_key,
        "is_version": is_version,
        "is_lob": is_lob,
        "is_enumerated": is_enumerated,
        "is_temporal": is_temporal,
        "temporal_type": temporal_type,
        "enum_type": enum_type,
        "annotations": [ann.name for ann in jpa_annotations]
    }


def _extract_relationship_info(prop: Field, jpa_annotations: list[Annotation]) -> dict:
    """Extract relationship information from property and annotations."""
    relationship_type = None
    target_entity = ""
    mapped_by = ""
    join_column = ""
    join_columns = []
    join_table = ""
    cascade = []
    fetch = "LAZY"
    orphan_removal = False
    optional = True
    
    for ann in jpa_annotations:
        if ann.name in ["OneToOne", "OneToMany", "ManyToOne", "ManyToMany"]:
            relationship_type = ann.name
            if "targetEntity" in ann.parameters:
                target_entity = ann.parameters["targetEntity"]
            if "mappedBy" in ann.parameters:
                mapped_by = ann.parameters["mappedBy"]
            if "cascade" in ann.parameters:
                cascade = ann.parameters["cascade"] if isinstance(ann.parameters["cascade"], list) else [ann.parameters["cascade"]]
            if "fetch" in ann.parameters:
                fetch = ann.parameters["fetch"]
            if "orphanRemoval" in ann.parameters:
                orphan_removal = ann.parameters["orphanRemoval"]
            if "optional" in ann.parameters:
                optional = ann.parameters["optional"]
                
        elif ann.name == "JoinColumn":
            if "name" in ann.parameters:
                join_column = ann.parameters["name"]
            join_columns.append({
                "name": ann.parameters.get("name", ""),
                "referencedColumnName": ann.parameters.get("referencedColumnName", ""),
                "nullable": ann.parameters.get("nullable", True),
                "unique": ann.parameters.get("unique", False),
                "insertable": ann.parameters.get("insertable", True),
                "updatable": ann.parameters.get("updatable", True),
                "columnDefinition": ann.parameters.get("columnDefinition", ""),
                "table": ann.parameters.get("table", "")
            })
            
        elif ann.name == "JoinTable":
            if "name" in ann.parameters:
                join_table = ann.parameters["name"]
    
    if relationship_type:
        return {
            "type": relationship_type,
            "target_entity": target_entity,
            "mapped_by": mapped_by,
            "join_column": join_column,
            "join_columns": join_columns,
            "join_table": join_table,
            "cascade": cascade,
            "fetch": fetch,
            "orphan_removal": orphan_removal,
            "optional": optional,
            "annotations": [ann.name for ann in jpa_annotations]
        }
    
    return None


def extract_jpa_repositories_from_classes(classes: list[Class]) -> list[JpaRepository]:
    """Extract JPA Repositories from parsed classes.
    
    Args:
        classes: List of parsed Class objects
        
    Returns:
        List of JpaRepository objects
    """
    repositories = []
    
    for cls in classes:
        is_repository = _is_jpa_repository(cls)
        
        if not is_repository:
            continue
        
        entity_type = _extract_entity_type_from_repository(cls)
        
        methods = _extract_repository_methods(cls)
        
        repository = JpaRepository(
            name=cls.name,
            entity_type=entity_type,
            methods=methods,
            package_name=cls.package_name,
            file_path=cls.file_path,
            annotations=[ann.name for ann in cls.annotations if ann.category == "jpa"],
            description="",
            ai_description=""
        )
        repositories.append(repository)
    
    return repositories


def _is_jpa_repository(cls: Class) -> bool:
    """Check if a class is a JPA Repository."""
    jpa_repository_interfaces = {
        "JpaRepository", "CrudRepository", "PagingAndSortingRepository",
        "JpaSpecificationExecutor", "QueryByExampleExecutor"
    }
    
    for interface in cls.interfaces:
        interface_name = interface.split('.')[-1]  # Get simple name
        if interface_name in jpa_repository_interfaces:
            return True
    
    has_repository_annotation = any(ann.name == "Repository" for ann in cls.annotations)
    
    is_repository_by_name = cls.name.endswith("Repository")
    
    return has_repository_annotation or is_repository_by_name


def _extract_entity_type_from_repository(cls: Class) -> str:
    """Extract entity type from repository class generic parameters."""
    # This is a simplified implementation
    # In a real implementation, you would parse the generic type parameters
    # from the class declaration
    
    # For now, try to infer from the class name
    # Common patterns: UserRepository -> User, UserEntityRepository -> UserEntity
    class_name = cls.name
    
    if class_name.endswith("Repository"):
        entity_name = class_name[:-10]  # Remove "Repository"
        return entity_name
    elif class_name.endswith("EntityRepository"):
        entity_name = class_name[:-15]  # Remove "EntityRepository"
        return entity_name
    
    return ""


def _extract_repository_methods(cls: Class) -> list[dict]:
    """Extract repository methods with query analysis."""
    methods = []
    
    for method in cls.methods:
        method_info = {
            "name": method.name,
            "return_type": method.return_type,
            "parameters": [{"name": param.name, "type": param.type} for param in method.parameters],
            "annotations": [ann.name for ann in method.annotations],
            "query_info": _analyze_repository_method(method)
        }
        methods.append(method_info)
    
    return methods


def _analyze_repository_method(method: Method) -> dict:
    """Analyze a repository method to extract query information."""
    query_info = {
        "query_type": "METHOD",  # Default to method query
        "query_content": "",
        "is_modifying": False,
        "is_native": False,
        "is_jpql": False,
        "is_named": False,
        "query_name": "",
        "parameters": []
    }
    
    for ann in method.annotations:
        if ann.name == "Query":
            query_info["query_type"] = "JPQL"
            query_info["is_jpql"] = True
            if "value" in ann.parameters:
                query_info["query_content"] = ann.parameters["value"]
            if "nativeQuery" in ann.parameters and ann.parameters["nativeQuery"]:
                query_info["query_type"] = "NATIVE"
                query_info["is_native"] = True
                query_info["is_jpql"] = False
            if "name" in ann.parameters:
                query_info["query_name"] = ann.parameters["name"]
                query_info["is_named"] = True
                
        elif ann.name == "Modifying":
            query_info["is_modifying"] = True
            
        elif ann.name == "NamedQuery":
            query_info["query_type"] = "NAMED"
            query_info["is_named"] = True
            if "name" in ann.parameters:
                query_info["query_name"] = ann.parameters["name"]
            if "query" in ann.parameters:
                query_info["query_content"] = ann.parameters["query"]
    
    if query_info["query_type"] == "METHOD":
        query_info.update(_analyze_method_name_query(method.name, method.parameters))
    
    return query_info


def _analyze_method_name_query(method_name: str, parameters: list[Field]) -> dict:
    """Analyze method name to derive query information."""
    query_info = {
        "derived_query": True,
        "operation": "SELECT",  # Default operation
        "entity_field": "",
        "conditions": [],
        "sorting": [],
        "paging": False
    }
    
    method_name_lower = method_name.lower()
    
    if method_name_lower.startswith("find") or method_name_lower.startswith("get"):
        query_info["operation"] = "SELECT"
    elif method_name_lower.startswith("save") or method_name_lower.startswith("insert"):
        query_info["operation"] = "INSERT"
    elif method_name_lower.startswith("update"):
        query_info["operation"] = "UPDATE"
    elif method_name_lower.startswith("delete") or method_name_lower.startswith("remove"):
        query_info["operation"] = "DELETE"
    elif method_name_lower.startswith("count"):
        query_info["operation"] = "COUNT"
    elif method_name_lower.startswith("exists"):
        query_info["operation"] = "EXISTS"
    
    if "orderby" in method_name_lower or "sort" in method_name_lower:
        query_info["sorting"] = ["field_name"]  # Simplified
    
    if "page" in method_name_lower or "pageable" in method_name_lower:
        query_info["paging"] = True
    
    field_patterns = [
        r"findBy(\w+)",
        r"getBy(\w+)",
        r"countBy(\w+)",
        r"existsBy(\w+)",
        r"deleteBy(\w+)"
    ]
    
    for pattern in field_patterns:
        match = re.search(pattern, method_name, re.IGNORECASE)
        if match:
            field_name = match.group(1)
            query_info["entity_field"] = field_name
            query_info["conditions"].append({
                "field": field_name,
                "operator": "=",
                "parameter": field_name.lower()
            })
            break
    
    return query_info


def extract_jpa_queries_from_repositories(repositories: list[JpaRepository]) -> list[JpaQuery]:
    """Extract JPA Queries from repository methods.
    
    Args:
        repositories: List of JpaRepository objects
        
    Returns:
        List of JpaQuery objects
    """
    queries = []
    
    for repository in repositories:
        for method in repository.methods:
            query_info = method.get("query_info", {})
            
            if query_info.get("query_content") or query_info.get("derived_query"):
                query = JpaQuery(
                    name=f"{repository.name}.{method['name']}",
                    query_type=query_info.get("query_type", "METHOD"),
                    query_content=query_info.get("query_content", ""),
                    return_type=method.get("return_type", ""),
                    parameters=method.get("parameters", []),
                    repository_name=repository.name,
                    method_name=method["name"],
                    annotations=method.get("annotations", []),
                    description="",
                    ai_description=""
                )
                queries.append(query)
    
    return queries


def analyze_jpa_entity_table_mapping(jpa_entities: list[JpaEntity], db_tables: list[Table]) -> dict:
    """Analyze mapping relationships between JPA entities and database tables.
    
    Args:
        jpa_entities: List of JPA entities
        db_tables: List of database tables
        
    Returns:
        Dictionary containing mapping analysis results
    """
    mapping_analysis = {
        "entity_table_mappings": [],
        "unmapped_entities": [],
        "unmapped_tables": [],
        "mapping_issues": [],
        "relationship_analysis": []
    }
    
    # Create table name lookup
    table_lookup = {table.name.lower(): table for table in db_tables}
    
    for entity in jpa_entities:
        entity_table_name = entity.table_name.lower()
        
        if entity_table_name in table_lookup:
            table = table_lookup[entity_table_name]
            
            # Analyze column mappings
            column_mappings = _analyze_column_mappings(entity, table)
            
            mapping_analysis["entity_table_mappings"].append({
                "entity_name": entity.name,
                "table_name": entity.table_name,
                "column_mappings": column_mappings,
                "mapping_accuracy": _calculate_mapping_accuracy(column_mappings),
                "issues": _identify_mapping_issues(entity, table, column_mappings)
            })
        else:
            mapping_analysis["unmapped_entities"].append({
                "entity_name": entity.name,
                "expected_table": entity.table_name,
                "reason": "Table not found in database schema"
            })
    
    # Find unmapped tables
    mapped_table_names = {mapping["table_name"].lower() for mapping in mapping_analysis["entity_table_mappings"]}
    for table in db_tables:
        if table.name.lower() not in mapped_table_names:
            mapping_analysis["unmapped_tables"].append({
                "table_name": table.name,
                "reason": "No corresponding JPA entity found"
            })
    
    # Analyze entity relationships
    mapping_analysis["relationship_analysis"] = _analyze_entity_relationships(jpa_entities)
    
    return mapping_analysis


def _analyze_column_mappings(entity: JpaEntity, table: Table) -> list[dict]:
    """Analyze column mappings between entity and table."""
    column_mappings = []
    
    # Create column lookup for the table
    table_columns = {col.name.lower(): col for col in table.columns}
    
    for column_info in entity.columns:
        column_name = column_info["column_name"].lower()
        
        if column_name in table_columns:
            db_column = table_columns[column_name]
            
            mapping = {
                "entity_property": column_info["property_name"],
                "entity_column": column_info["column_name"],
                "db_column": db_column.name,
                "data_type_match": _compare_data_types(column_info["data_type"], db_column.data_type),
                "nullable_match": column_info["nullable"] == db_column.nullable,
                "unique_match": column_info["unique"] == db_column.unique,
                "is_primary_key": column_info.get("is_primary_key", False) == db_column.primary_key,
                "mapping_quality": "good" if _is_good_mapping(column_info, db_column) else "needs_review"
            }
        else:
            mapping = {
                "entity_property": column_info["property_name"],
                "entity_column": column_info["column_name"],
                "db_column": None,
                "data_type_match": False,
                "nullable_match": False,
                "unique_match": False,
                "is_primary_key": False,
                "mapping_quality": "missing"
            }
        
        column_mappings.append(mapping)
    
    return column_mappings


def _compare_data_types(entity_type: str, db_type: str) -> bool:
    """Compare entity data type with database column type."""
    # Simplified type comparison
    type_mapping = {
        "String": ["varchar", "char", "text", "clob"],
        "Integer": ["int", "integer", "number"],
        "Long": ["bigint", "number"],
        "Double": ["double", "float", "number"],
        "Boolean": ["boolean", "bit"],
        "Date": ["date", "timestamp", "datetime"],
        "LocalDateTime": ["timestamp", "datetime"],
        "BigDecimal": ["decimal", "numeric", "number"]
    }
    
    entity_type_simple = entity_type.split('.')[-1]  # Get simple class name
    
    if entity_type_simple in type_mapping:
        db_type_lower = db_type.lower()
        return any(db_type_lower.startswith(mapped_type) for mapped_type in type_mapping[entity_type_simple])
    
    return False


def _is_good_mapping(column_info: dict, db_column: Table) -> bool:
    """Check if the mapping between entity column and DB column is good."""
    return (
        _compare_data_types(column_info["data_type"], db_column.data_type) and
        column_info["nullable"] == db_column.nullable and
        column_info["unique"] == db_column.unique and
        column_info.get("is_primary_key", False) == db_column.primary_key
    )


def _calculate_mapping_accuracy(column_mappings: list[dict]) -> float:
    """Calculate mapping accuracy percentage."""
    if not column_mappings:
        return 0.0
    
    good_mappings = sum(1 for mapping in column_mappings if mapping["mapping_quality"] == "good")
    return (good_mappings / len(column_mappings)) * 100


def _identify_mapping_issues(entity: JpaEntity, table: Table, column_mappings: list[dict]) -> list[str]:
    """Identify mapping issues between entity and table."""
    issues = []
    
    for mapping in column_mappings:
        if mapping["mapping_quality"] == "missing":
            issues.append(f"Column '{mapping['entity_column']}' not found in table '{table.name}'")
        elif mapping["mapping_quality"] == "needs_review":
            if not mapping["data_type_match"]:
                issues.append(f"Data type mismatch for column '{mapping['entity_column']}'")
            if not mapping["nullable_match"]:
                issues.append(f"Nullable constraint mismatch for column '{mapping['entity_column']}'")
            if not mapping["unique_match"]:
                issues.append(f"Unique constraint mismatch for column '{mapping['entity_column']}'")
    
    return issues


def _analyze_entity_relationships(jpa_entities: list[JpaEntity]) -> list[dict]:
    """Analyze relationships between JPA entities."""
    relationship_analysis = []
    
    for entity in jpa_entities:
        for relationship in entity.relationships:
            analysis = {
                "source_entity": entity.name,
                "target_entity": relationship.get("target_entity", ""),
                "relationship_type": relationship.get("type", ""),
                "mapped_by": relationship.get("mapped_by", ""),
                "join_column": relationship.get("join_column", ""),
                "cascade": relationship.get("cascade", []),
                "fetch_type": relationship.get("fetch", "LAZY"),
                "is_bidirectional": bool(relationship.get("mapped_by", "")),
                "relationship_quality": _assess_relationship_quality(relationship)
            }
            relationship_analysis.append(analysis)
    
    return relationship_analysis


def _assess_relationship_quality(relationship: dict) -> str:
    """Assess the quality of a JPA relationship."""
    issues = []
    
    if not relationship.get("target_entity"):
        issues.append("Missing target entity")
    
    if relationship.get("type") in ["OneToMany", "ManyToMany"] and not relationship.get("mapped_by"):
        issues.append("Missing mappedBy for collection relationship")
    
    if relationship.get("type") in ["OneToOne", "ManyToOne"] and not relationship.get("join_column"):
        issues.append("Missing join column for single relationship")
    
    if not issues:
        return "good"
    elif len(issues) == 1:
        return "needs_review"
    else:
        return "needs_attention"


def parse_yaml_config(file_path: str) -> ConfigFile:
    """Parse YAML configuration file.
    
    Args:
        file_path: Path to the YAML file
        
    Returns:
        ConfigFile object
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            documents = list(yaml.safe_load_all(f))
            content = documents[0] if documents else {}
        
        if not content:
            content = {}
        
        file_name = os.path.basename(file_path)
        file_type = "yaml" if file_path.endswith('.yaml') else "yml"
        
        profiles = []
        if 'spring' in content and 'profiles' in content['spring']:
            if 'active' in content['spring']['profiles']:
                profiles = content['spring']['profiles']['active']
                if isinstance(profiles, str):
                    profiles = [profiles]
        
        # Determine environment
        environment = "dev"  # default
        if profiles:
            environment = profiles[0]
        
        # Extract sections
        sections = []
        for key, value in content.items():
            if isinstance(value, dict):
                sections.append({
                    "name": key,
                    "properties": value,
                    "type": "section"
                })
        
        return ConfigFile(
            name=file_name,
            file_path=file_path,
            file_type=file_type,
            properties=content,
            sections=sections,
            profiles=profiles,
            environment=environment
        )
    
    except Exception as e:
        print(f"Error parsing YAML file {file_path}: {e}")
        return ConfigFile(
            name=os.path.basename(file_path),
            file_path=file_path,
            file_type="yaml",
            properties={},
            sections=[],
            profiles=[],
            environment=""
        )


def parse_properties_config(file_path: str) -> ConfigFile:
    """Parse Properties configuration file.
    
    Args:
        file_path: Path to the properties file
        
    Returns:
        ConfigFile object
    """
    try:
        properties = {}
        sections = []
        profiles = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Parse key=value pairs
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Remove quotes if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    
                    properties[key] = value
                    
                    # Check for profiles
                    if key == 'spring.profiles.active':
                        profiles = [p.strip() for p in value.split(',')]
        
        # Group properties by section
        section_map = {}
        for key, value in properties.items():
            if '.' in key:
                section = key.split('.')[0]
                if section not in section_map:
                    section_map[section] = {}
                section_map[section][key] = value
            else:
                if 'root' not in section_map:
                    section_map['root'] = {}
                section_map['root'][key] = value
        
        for section_name, section_props in section_map.items():
            sections.append({
                "name": section_name,
                "properties": section_props,
                "type": "section"
            })
        
        # Determine environment
        environment = "dev"  # default
        if profiles:
            environment = profiles[0]
        
        return ConfigFile(
            name=os.path.basename(file_path),
            file_path=file_path,
            file_type="properties",
            properties=properties,
            sections=sections,
            profiles=profiles,
            environment=environment
        )
    
    except Exception as e:
        print(f"Error parsing Properties file {file_path}: {e}")
        return ConfigFile(
            name=os.path.basename(file_path),
            file_path=file_path,
            file_type="properties",
            properties={},
            sections=[],
            profiles=[],
            environment=""
        )


def extract_database_config(config_file: ConfigFile) -> DatabaseConfig:
    """Extract database configuration from config file.
    
    Args:
        config_file: ConfigFile object
        
    Returns:
        DatabaseConfig object
    """
    db_config = DatabaseConfig()
    
    if config_file.file_type in ["yaml", "yml"]:
        # YAML format
        spring_config = config_file.properties.get('spring', {})
        datasource_config = spring_config.get('datasource', {})
        jpa_config = spring_config.get('jpa', {})
        
        db_config.driver = datasource_config.get('driver-class-name', '')
        db_config.url = datasource_config.get('url', '')
        db_config.username = datasource_config.get('username', '')
        db_config.password = datasource_config.get('password', '')
        db_config.dialect = jpa_config.get('database-platform', '')
        db_config.hibernate_ddl_auto = jpa_config.get('hibernate', {}).get('ddl-auto', '')
        db_config.show_sql = jpa_config.get('show-sql', False)
        db_config.format_sql = jpa_config.get('properties', {}).get('hibernate', {}).get('format_sql', False)
        
        # Store additional JPA properties
        if 'properties' in jpa_config:
            db_config.jpa_properties = jpa_config['properties']
    
    else:
        # Properties format
        props = config_file.properties
        
        db_config.driver = props.get('spring.datasource.driver-class-name', '')
        db_config.url = props.get('spring.datasource.url', '')
        db_config.username = props.get('spring.datasource.username', '')
        db_config.password = props.get('spring.datasource.password', '')
        db_config.dialect = props.get('spring.jpa.database-platform', '')
        db_config.hibernate_ddl_auto = props.get('spring.jpa.hibernate.ddl-auto', '')
        db_config.show_sql = props.get('spring.jpa.show-sql', 'false').lower() == 'true'
        db_config.format_sql = props.get('spring.jpa.properties.hibernate.format_sql', 'false').lower() == 'true'
        
        # Store additional JPA properties
        jpa_props = {}
        for key, value in props.items():
            if key.startswith('spring.jpa.properties.'):
                jpa_props[key] = value
        db_config.jpa_properties = jpa_props
    
    return db_config


def extract_server_config(config_file: ConfigFile) -> ServerConfig:
    """Extract server configuration from config file.
    
    Args:
        config_file: ConfigFile object
        
    Returns:
        ServerConfig object
    """
    server_config = ServerConfig()
    
    if config_file.file_type in ["yaml", "yml"]:
        # YAML format
        server_props = config_file.properties.get('server', {})
        
        server_config.port = server_props.get('port', 8080)
        server_config.context_path = server_props.get('servlet', {}).get('context-path', '')
        server_config.servlet_path = server_props.get('servlet', {}).get('path', '')
        
        # SSL configuration
        ssl_config = server_props.get('ssl', {})
        server_config.ssl_enabled = bool(ssl_config)
        server_config.ssl_key_store = ssl_config.get('key-store', '')
        server_config.ssl_key_store_password = ssl_config.get('key-store-password', '')
        server_config.ssl_key_store_type = ssl_config.get('key-store-type', '')
    
    else:
        # Properties format
        props = config_file.properties
        
        server_config.port = int(props.get('server.port', '8080'))
        server_config.context_path = props.get('server.servlet.context-path', '')
        server_config.servlet_path = props.get('server.servlet.path', '')
        
        # SSL configuration
        server_config.ssl_enabled = any(key.startswith('server.ssl.') for key in props.keys())
        server_config.ssl_key_store = props.get('server.ssl.key-store', '')
        server_config.ssl_key_store_password = props.get('server.ssl.key-store-password', '')
        server_config.ssl_key_store_type = props.get('server.ssl.key-store-type', '')
    
    return server_config


def extract_security_config(config_file: ConfigFile) -> SecurityConfig:
    """Extract security configuration from config file.
    
    Args:
        config_file: ConfigFile object
        
    Returns:
        SecurityConfig object
    """
    security_config = SecurityConfig()
    
    if config_file.file_type in ["yaml", "yml"]:
        # YAML format
        security_props = config_file.properties.get('security', {})
        jwt_props = security_props.get('jwt', {})
        cors_props = security_props.get('cors', {})
        
        security_config.enabled = bool(security_props)
        security_config.authentication_type = security_props.get('authentication-type', '')
        security_config.jwt_secret = jwt_props.get('secret', '')
        security_config.jwt_expiration = jwt_props.get('expiration', 0)
        security_config.cors_allowed_origins = cors_props.get('allowed-origins', [])
        security_config.cors_allowed_methods = cors_props.get('allowed-methods', [])
        security_config.cors_allowed_headers = cors_props.get('allowed-headers', [])
    
    else:
        # Properties format
        props = config_file.properties
        
        security_config.enabled = any(key.startswith('security.') for key in props.keys())
        security_config.authentication_type = props.get('security.authentication-type', '')
        security_config.jwt_secret = props.get('security.jwt.secret', '')
        security_config.jwt_expiration = int(props.get('security.jwt.expiration', '0'))
        
        # CORS configuration
        origins = props.get('security.cors.allowed-origins', '')
        if origins:
            security_config.cors_allowed_origins = [o.strip() for o in origins.split(',')]
        
        methods = props.get('security.cors.allowed-methods', '')
        if methods:
            security_config.cors_allowed_methods = [m.strip() for m in methods.split(',')]
        
        headers = props.get('security.cors.allowed-headers', '')
        if headers:
            security_config.cors_allowed_headers = [h.strip() for h in headers.split(',')]
    
    return security_config


def extract_logging_config(config_file: ConfigFile) -> LoggingConfig:
    """Extract logging configuration from config file.
    
    Args:
        config_file: ConfigFile object
        
    Returns:
        LoggingConfig object
    """
    logging_config = LoggingConfig()
    
    if config_file.file_type in ["yaml", "yml"]:
        # YAML format
        logging_props = config_file.properties.get('logging', {})
        
        logging_config.level = logging_props.get('level', {}).get('root', 'INFO')
        logging_config.pattern = logging_props.get('pattern', {}).get('console', '')
        logging_config.file_path = logging_props.get('file', {}).get('name', '')
        logging_config.max_file_size = logging_props.get('file', {}).get('max-size', '')
        logging_config.max_history = logging_props.get('file', {}).get('max-history', 0)
        logging_config.console_output = logging_props.get('console', {}).get('enabled', True)
    
    else:
        # Properties format
        props = config_file.properties
        
        logging_config.level = props.get('logging.level.root', 'INFO')
        logging_config.pattern = props.get('logging.pattern.console', '')
        logging_config.file_path = props.get('logging.file.name', '')
        logging_config.max_file_size = props.get('logging.file.max-size', '')
        logging_config.max_history = int(props.get('logging.file.max-history', '0'))
        logging_config.console_output = props.get('logging.console.enabled', 'true').lower() == 'true'
    
    return logging_config


def extract_config_files(directory: str) -> list[ConfigFile]:
    """Extract configuration files from directory.
    
    Args:
        directory: Directory to search for config files
        
    Returns:
        List of ConfigFile objects
    """
    config_files = []
    
    # Common config file patterns
    config_patterns = [
        "application.yml",
        "application.yaml", 
        "application.properties",
        "application-*.properties",
        "bootstrap.yml",
        "bootstrap.yaml",
        "bootstrap.properties"
    ]
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            # Check if file matches any config pattern
            is_config_file = False
            for pattern in config_patterns:
                if pattern == file or (pattern.endswith('*') and file.startswith(pattern[:-1])):
                    is_config_file = True
                    break
            
            if is_config_file:
                file_path = os.path.join(root, file)
                
                if file.endswith(('.yml', '.yaml')):
                    config_file = parse_yaml_config(file_path)
                elif file.endswith('.properties'):
                    config_file = parse_properties_config(file_path)
                else:
                    continue
                
                config_files.append(config_file)
    
    return config_files


def extract_test_classes_from_classes(classes: list[Class]) -> list[TestClass]:
    """Extract test classes from parsed classes.
    
    Args:
        classes: List of parsed Class objects
        
    Returns:
        List of TestClass objects
    """
    test_classes = []
    
    for cls in classes:
        test_annotations = [ann for ann in cls.annotations if classify_test_annotation(ann.name) in ["junit", "spring_test", "testng"]]
        
        if not test_annotations:
            continue
        
        test_framework = "junit"  # default
        test_type = "unit"  # default
        
        for ann in test_annotations:
            if ann.name in ["SpringBootTest", "WebMvcTest", "DataJpaTest", "DataJdbcTest", "JdbcTest", "JsonTest", "RestClientTest", "WebFluxTest"]:
                test_framework = "spring_test"
                if ann.name == "SpringBootTest":
                    test_type = "integration"
                else:
                    test_type = "slice"
            elif ann.name in ["TestNG", "BeforeMethod", "AfterMethod", "BeforeClass", "AfterClass"]:
                test_framework = "testng"
            elif ann.name in ["Test", "BeforeEach", "AfterEach", "BeforeAll", "AfterAll"]:
                test_framework = "junit"
        
        test_methods = []
        setup_methods = []
        
        for method in cls.methods:
            method_annotations = [ann.name for ann in method.annotations if classify_test_annotation(ann.name) in ["junit", "spring_test", "testng"]]
            
            if method_annotations:
                if any(ann in method_annotations for ann in ["BeforeEach", "AfterEach", "BeforeAll", "AfterAll", "BeforeMethod", "AfterMethod", "BeforeClass", "AfterClass", "BeforeSuite", "AfterSuite"]):
                    setup_methods.append({
                        "name": method.name,
                        "annotations": method_annotations,
                        "return_type": method.return_type,
                        "parameters": [{"name": p.name, "type": p.type} for p in method.parameters]
                    })
                else:
                    test_method_info = {
                        "name": method.name,
                        "annotations": method_annotations,
                        "return_type": method.return_type,
                        "parameters": [{"name": p.name, "type": p.type} for p in method.parameters],
                        "assertions": [],
                        "mock_calls": [],
                        "test_data": [],
                        "expected_exceptions": [],
                        "timeout": 0,
                        "display_name": ""
                    }
                    
                    for ann in method.annotations:
                        if ann.name == "DisplayName" and "value" in ann.parameters:
                            test_method_info["display_name"] = ann.parameters["value"]
                        elif ann.name == "Timeout" and "value" in ann.parameters:
                            test_method_info["timeout"] = ann.parameters["value"]
                    
                    for ann in method.annotations:
                        if ann.name == "ExpectedExceptions" and "value" in ann.parameters:
                            test_method_info["expected_exceptions"] = ann.parameters["value"] if isinstance(ann.parameters["value"], list) else [ann.parameters["value"]]
                    
                    test_methods.append(test_method_info)
        
        mock_dependencies = []
        for prop in cls.properties:
            prop_annotations = [ann.name for ann in prop.annotations if classify_test_annotation(ann.name) in ["mockito", "spring_test"]]
            if prop_annotations:
                mock_dependencies.append({
                    "name": prop.name,
                    "type": prop.type,
                    "annotations": prop_annotations,
                    "mock_type": "mock" if "Mock" in prop_annotations else "spy" if "Spy" in prop_annotations else "bean"
                })
        
        test_configurations = []
        for ann in cls.annotations:
            if ann.name in ["TestConfiguration", "ActiveProfiles", "TestPropertySource"]:
                config_info = {
                    "name": ann.name,
                    "type": "configuration" if ann.name == "TestConfiguration" else "profile" if ann.name == "ActiveProfiles" else "property",
                    "properties": ann.parameters,
                    "active_profiles": ann.parameters.get("value", []) if ann.name == "ActiveProfiles" else [],
                    "test_slices": [],
                    "mock_beans": [],
                    "spy_beans": []
                }
                test_configurations.append(config_info)
        
        test_class = TestClass(
            name=cls.name,
            package_name=cls.package_name,
            test_framework=test_framework,
            test_type=test_type,
            annotations=[ann.name for ann in test_annotations],
            test_methods=test_methods,
            setup_methods=setup_methods,
            mock_dependencies=mock_dependencies,
            test_configurations=test_configurations,
            file_path=cls.file_path
        )
        test_classes.append(test_class)
    
    return test_classes


def analyze_test_methods(test_class: TestClass, class_obj: Class) -> list[TestMethod]:
    """Analyze test methods for assertions, mock calls, and test data.
    
    Args:
        test_class: TestClass object
        class_obj: Original Class object
        
    Returns:
        List of analyzed TestMethod objects
    """
    test_methods = []
    
    for method_info in test_class.test_methods:
        method_obj = None
        for method in class_obj.methods:
            if method.name == method_info["name"]:
                method_obj = method
                break
        
        if not method_obj:
            continue
        
        assertions = []
        mock_calls = []
        test_data = []
        
        if method_obj.source:
            source_code = method_obj.source
            
            assertion_patterns = [
                r'assert\w+\(',  # JUnit assertions
                r'assertThat\(',  # AssertJ
                r'assertEquals\(',  # JUnit
                r'assertTrue\(',  # JUnit
                r'assertFalse\(',  # JUnit
                r'assertNotNull\(',  # JUnit
                r'assertNull\(',  # JUnit
                r'assertThrows\(',  # JUnit 5
                r'assertDoesNotThrow\(',  # JUnit 5
                r'verify\(',  # Mockito verify
                r'when\(',  # Mockito when
                r'then\(',  # Mockito then
                r'given\(',  # BDDMockito given
                r'willReturn\(',  # Mockito willReturn
                r'willThrow\(',  # Mockito willThrow
            ]
            
            for pattern in assertion_patterns:
                matches = re.findall(pattern, source_code)
                for match in matches:
                    assertions.append({
                        "type": match,
                        "line": source_code.find(match) + 1
                    })
            
            mock_call_patterns = [
                r'(\w+)\.(\w+)\(',  # Method calls on objects
                r'mock\(',  # Mockito mock creation
                r'spy\(',  # Mockito spy creation
                r'@Mock\s+(\w+)',  # @Mock annotation
                r'@Spy\s+(\w+)',  # @Spy annotation
                r'@InjectMocks\s+(\w+)',  # @InjectMocks annotation
            ]
            
            for pattern in mock_call_patterns:
                matches = re.findall(pattern, source_code)
                for match in matches:
                    if isinstance(match, tuple):
                        mock_calls.append({
                            "object": match[0],
                            "method": match[1],
                            "type": "method_call"
                        })
                    else:
                        mock_calls.append({
                            "type": match,
                            "line": source_code.find(match) + 1
                        })
            
            test_data_patterns = [
                r'new\s+(\w+)\(',  # Object creation
                r'(\w+)\s*=\s*new\s+(\w+)\(',  # Variable assignment with new
                r'@ValueSource\(',  # JUnit 5 @ValueSource
                r'@CsvSource\(',  # JUnit 5 @CsvSource
                r'@MethodSource\(',  # JUnit 5 @MethodSource
            ]
            
            for pattern in test_data_patterns:
                matches = re.findall(pattern, source_code)
                for match in matches:
                    if isinstance(match, tuple):
                        test_data.append({
                            "variable": match[0],
                            "type": match[1],
                            "pattern": "object_creation"
                        })
                    else:
                        test_data.append({
                            "type": match,
                            "pattern": "annotation"
                        })
        
        test_method = TestMethod(
            name=method_info["name"],
            return_type=method_info["return_type"],
            annotations=method_info["annotations"],
            assertions=assertions,
            mock_calls=mock_calls,
            test_data=test_data,
            expected_exceptions=method_info["expected_exceptions"],
            timeout=method_info["timeout"],
            display_name=method_info["display_name"]
        )
        test_methods.append(test_method)
    
    return test_methods


def generate_lombok_methods(properties: list[Field], class_name: str, package_name: str) -> list[Method]:
    """Generate Lombok @Data methods (getters, setters, equals, hashCode, toString) for properties."""
    methods = []
    
    for prop in properties:
        getter_name = f"get{prop.name[0].upper()}{prop.name[1:]}"
        if prop.type == "Boolean" and prop.name.startswith("is"):
            getter_name = prop.name
        
        getter = Method(
            name=getter_name,
            logical_name=f"{package_name}.{class_name}.{getter_name}",
            return_type=prop.type,
            parameters=[],
            modifiers=["public"],
            source="",  # Generated method, no source
            package_name=package_name,
            annotations=[],
            description=f"Generated getter for {prop.name} field",  # Generated method description
            ai_description=""
        )
        methods.append(getter)
        
        setter_name = f"set{prop.name[0].upper()}{prop.name[1:]}"
        setter_param = Field(
            name=prop.name,
            logical_name=f"{package_name}.{class_name}.{prop.name}",
            type=prop.type,
            package_name=package_name,
            class_name=class_name
        )
        
        setter = Method(
            name=setter_name,
            logical_name=f"{package_name}.{class_name}.{setter_name}",
            return_type="void",
            parameters=[setter_param],
            modifiers=["public"],
            source="",  # Generated method, no source
            package_name=package_name,
            annotations=[],
            description=f"Generated setter for {prop.name} field",  # Generated method description
            ai_description=""
        )
        methods.append(setter)
    
    equals_method = Method(
        name="equals",
        logical_name=f"{package_name}.{class_name}.equals",
        return_type="boolean",
        parameters=[Field(name="obj", logical_name=f"{package_name}.{class_name}.obj", type="Object", package_name=package_name, class_name=class_name)],
        modifiers=["public"],
        source="",  # Generated method, no source
        package_name=package_name,
        annotations=[],
        description="Generated equals method for object comparison",  # Generated method description
        ai_description=""
    )
    methods.append(equals_method)
    
    hashcode_method = Method(
        name="hashCode",
        logical_name=f"{package_name}.{class_name}.hashCode",
        return_type="int",
        parameters=[],
        modifiers=["public"],
        source="",  # Generated method, no source
        package_name=package_name,
        annotations=[],
        description="Generated hashCode method for object hashing",  # Generated method description
        ai_description=""
    )
    methods.append(hashcode_method)
    
    tostring_method = Method(
        name="toString",
        logical_name=f"{package_name}.{class_name}.toString",
        return_type="String",
        parameters=[],
        modifiers=["public"],
        source="",  # Generated method, no source
        package_name=package_name,
        annotations=[],
        description="Generated toString method for string representation",  # Generated method description
        ai_description=""
    )
    methods.append(tostring_method)
    
    return methods


def parse_single_java_file(file_path: str, project_name: str) -> tuple[Package, Class, str]:
    """Parse a single Java file and return parsed entities."""
    logger = get_logger(__name__)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        file_content = f.read()
    
    try:
        tree = javalang.parse.parse(file_content)
        print(f"DEBUG: Successfully parsed file: {file_path}")
        logger.info(f"Successfully parsed file: {file_path}")
        
        package_name = tree.package.name if tree.package else ""
        print(f"DEBUG: Parsed package name: {package_name}")
        logger.info(f"Parsed package name: {package_name}")
        
        if package_name:
            package_node = Package(name=package_name)
        else:
            package_name = "default"
            package_node = Package(name=package_name)
        
        import_map = {}
        for imp in tree.imports:
            class_name = imp.path.split('.')[-1]
            import_map[class_name] = imp.path
    except Exception as e:
        logger.error(f"Error parsing file: {e}")
        return None, None, ""


def parse_java_project(directory: str) -> tuple[list[Package], list[Class], dict[str, str], list[Bean], list[BeanDependency], list[Endpoint], list[MyBatisMapper], list[JpaEntity], list[JpaRepository], list[JpaQuery], list[ConfigFile], list[TestClass], list[SqlStatement], str]:
    """Parse Java project and return parsed entities."""
    logger = get_logger(__name__)
    
    project_name = extract_project_name(directory)
    packages = {}
    classes = {}
    class_to_package_map = {}
    
    logger.info(f"Starting Java project analysis in: {directory}")
    logger.info(f"Project name: {project_name}")

    java_file_count = 0
    processed_file_count = 0
    
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".java"):
                java_file_count += 1
                file_path = os.path.join(root, file)
                logger.debug(f"Processing Java file {java_file_count}: {file_path}")
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_content = f.read()
                
                if '<html' in file_content.lower() or '<body' in file_content.lower() or '<div' in file_content.lower():
                    logger.warning(f"Skipping file with HTML content: {file_path}")
                    continue
                
                try:
                    tree = javalang.parse.parse(file_content)
                    package_name = tree.package.name if tree.package else ""
                    logger.debug(f"Parsed file: {file_path}, package: {package_name}")
                    
                    if package_name and package_name not in packages:
                        packages[package_name] = Package(
                            name=package_name
                        )
                    elif not package_name:
                        package_name = "default"
                        if package_name not in packages:
                            packages[package_name] = Package(
                                name=package_name
                            )
                    
                    import_map = {}
                    for imp in tree.imports:
                        class_name = imp.path.split('.')[-1]
                        import_map[class_name] = imp.path

                    class_declarations = []
                    for type_decl in tree.types:
                        if isinstance(type_decl, (javalang.tree.ClassDeclaration, javalang.tree.InterfaceDeclaration)):
                            class_declarations.append((None, type_decl))
                    
                    for _, class_declaration in class_declarations:
                        class_name = class_declaration.name
                        class_key = f"{package_name}.{class_name}"
                        logger.debug(f"Processing class/interface: {class_name} (type: {type(class_declaration).__name__})")
                        
                        if class_key not in classes:
                            class_annotations = parse_annotations(class_declaration.annotations, "class") if hasattr(class_declaration, 'annotations') else []
                            class_type = "interface" if isinstance(class_declaration, javalang.tree.InterfaceDeclaration) else "class"
                            
                            classes[class_key] = Class(
                                name=class_name,
                                logical_name=class_key,
                                file_path=file_path,
                                type=class_type,
                                source=file_content,
                                annotations=class_annotations,
                                package_name=package_name,
                                project_name=project_name,
                                description="",
                                ai_description=""
                            )
                            class_to_package_map[class_key] = package_name
                            logger.info(f"Successfully added class to classes dict: {class_name} (key: {class_key})")
                        else:
                            logger.debug(f"Class {class_name} already exists, skipping")
                        
                        for imp in tree.imports:
                            classes[class_key].imports.append(imp.path)

                        if class_declaration.extends:
                            superclass_name = class_declaration.extends.name
                            if superclass_name in import_map:
                                classes[class_key].superclass = import_map[superclass_name]
                            else:
                                classes[class_key].superclass = f"{package_name}.{superclass_name}" if package_name else superclass_name

                        if hasattr(class_declaration, 'implements') and class_declaration.implements:
                            for impl_ref in class_declaration.implements:
                                interface_name = impl_ref.name
                                if interface_name in import_map:
                                    classes[class_key].interfaces.append(import_map[interface_name])
                                else:
                                    classes[class_key].interfaces.append(f"{package_name}.{interface_name}" if package_name else interface_name)

                        field_map = {}
                        for field_declaration in class_declaration.fields:
                            for declarator in field_declaration.declarators:
                                field_map[declarator.name] = field_declaration.type.name
                                
                                field_annotations = parse_annotations(field_declaration.annotations, "field") if hasattr(field_declaration, 'annotations') else []
                                
                                initial_value = ""
                                if hasattr(declarator, 'initializer') and declarator.initializer:
                                    if hasattr(declarator.initializer, 'value'):
                                        initial_value = str(declarator.initializer.value)
                                    elif hasattr(declarator.initializer, 'type'):
                                        initial_value = str(declarator.initializer.type)
                                    else:
                                        initial_value = str(declarator.initializer)
                                
                                prop = Field(
                                    name=declarator.name,
                                    logical_name=f"{package_name}.{class_name}.{declarator.name}",
                                    type=field_declaration.type.name,
                                    modifiers=list(field_declaration.modifiers),
                                    package_name=package_name,
                                    class_name=class_name,
                                    annotations=field_annotations,
                                    initial_value=initial_value,
                                    description="",
                                    ai_description=""
                                )
                                classes[class_key].properties.append(prop)

                        all_declarations = class_declaration.methods + class_declaration.constructors
                        
                        for declaration in all_declarations:
                            local_var_map = field_map.copy()
                            params = []
                            for param in declaration.parameters:
                                param_type_name = 'Unknown'
                                if hasattr(param.type, 'name'):
                                    param_type_name = param.type.name
                                local_var_map[param.name] = param_type_name
                                params.append(Field(name=param.name, logical_name=f"{package_name}.{class_name}.{param.name}", type=param_type_name, package_name=package_name, class_name=class_name))

                            if declaration.body:
                                for _, var_decl in declaration.filter(javalang.tree.LocalVariableDeclaration):
                                    for declarator in var_decl.declarators:
                                        local_var_map[declarator.name] = var_decl.type.name
                            
                            if isinstance(declaration, javalang.tree.MethodDeclaration):
                                return_type = declaration.return_type.name if declaration.return_type else "void"
                            else:
                                return_type = "constructor"

                            modifiers = list(declaration.modifiers)
                            method_annotations = parse_annotations(declaration.annotations, "method") if hasattr(declaration, 'annotations') else []

                            method_source = ""
                            if declaration.position:
                                lines = file_content.splitlines(keepends=True)
                                start_line = declaration.position.line - 1
                                
                                brace_count = 0
                                end_line = start_line
                                for i in range(start_line, len(lines)):
                                    line = lines[i]
                                    for char in line:
                                        if char == '{':
                                            brace_count += 1
                                        elif char == '}':
                                            brace_count -= 1
                                            if brace_count == 0:
                                                end_line = i
                                                break
                                    if brace_count == 0:
                                        break
                                
                                method_source = "".join(lines[start_line:end_line + 1])

                            method = Method(
                                name=declaration.name,
                                logical_name=f"{class_key}.{declaration.name}",
                                return_type=return_type,
                                parameters=params,
                                modifiers=modifiers,
                                source=method_source,
                                package_name=package_name,
                                annotations=method_annotations,
                                description="",
                                ai_description=""
                            )
                            classes[class_key].methods.append(method)

                            call_order = 0
                            for _, invocation in declaration.filter(javalang.tree.MethodInvocation):
                                target_class_name = None
                                resolved_target_package = ""
                                resolved_target_class_name = ""
                                
                                if invocation.qualifier:
                                    if invocation.qualifier in local_var_map:
                                        target_class_name = local_var_map[invocation.qualifier]
                                    else:
                                        target_class_name = invocation.qualifier
                                    
                                    if target_class_name:
                                        if target_class_name == "System.out":
                                            resolved_target_package = "java.io"
                                            resolved_target_class_name = "PrintStream"
                                        else:
                                            if invocation.qualifier in local_var_map:
                                                resolved_target_class_name = target_class_name
                                                if target_class_name in import_map:
                                                    resolved_target_package = ".".join(import_map[target_class_name].split(".")[:-1])
                                                else:
                                                    resolved_target_package = package_name
                                                    
                                                    if package_name and 'controller' in package_name:
                                                        service_package = package_name.replace('controller', 'service')
                                                        resolved_target_package = service_package
                                                    
                                                    elif package_name and 'domain' in package_name:
                                                        domain_parts = package_name.split('.')
                                                        if len(domain_parts) >= 3:
                                                            domain_base = '.'.join(domain_parts[:3])
                                                            service_package = f"{domain_base}.{domain_parts[2]}.service"
                                                            resolved_target_package = service_package
                                                
                                                if '<' in target_class_name:
                                                    base_type = target_class_name.split('<')[0]
                                                    resolved_target_class_name = base_type
                                            else:
                                                if target_class_name in import_map:
                                                    resolved_target_package = ".".join(import_map[target_class_name].split(".")[:-1])
                                                else:
                                                    resolved_target_package = package_name
                                                resolved_target_class_name = target_class_name
                                else:
                                    resolved_target_package = package_name
                                    resolved_target_class_name = class_name

                                if resolved_target_class_name:
                                    method_name = invocation.member
                                    if method_name in {'collect', 'map', 'filter', 'forEach', 'stream', 'reduce', 'findFirst', 'findAny', 'anyMatch', 'allMatch', 'noneMatch', 'count', 'distinct', 'sorted', 'limit', 'skip', 'peek', 'flatMap', 'toArray'}:
                                        continue
                                        
                                    line_number = invocation.position.line if invocation.position else 0

                                    call = MethodCall(
                                        source_package=package_name,
                                        source_class=class_name,
                                        source_method=declaration.name,
                                        target_package=resolved_target_package,
                                        target_class=resolved_target_class_name,
                                        target_method=invocation.member,
                                        call_order=call_order,
                                        line_number=line_number,
                                        return_type="void"
                                    )
                                    classes[class_key].calls.append(call)
                                    call_order += 1
                        
                        has_data_annotation = any(ann.name == "Data" for ann in classes[class_key].annotations)
                        if has_data_annotation:
                            logger.debug(f"Found @Data annotation on {class_name}, generating Lombok methods")
                            lombok_methods = generate_lombok_methods(classes[class_key].properties, class_name, package_name)
                            classes[class_key].methods.extend(lombok_methods)
                            logger.debug(f"Generated {len(lombok_methods)} Lombok methods for {class_name}")
                    
                    processed_file_count += 1
                    logger.debug(f"Successfully processed file: {file_path}")
                
                except Exception as e:
                    logger.error(f"Error processing file {file_path}: {e}")
                    continue
    
    classes_list = list(classes.values())
    beans = extract_beans_from_classes(classes_list)
    dependencies = analyze_bean_dependencies(classes_list, beans)
    endpoints = extract_endpoints_from_classes(classes_list)
    mybatis_mappers = extract_mybatis_mappers_from_classes(classes_list)
    jpa_entities = extract_jpa_entities_from_classes(classes_list)
    jpa_repositories = extract_jpa_repositories_from_classes(classes_list)
    jpa_queries = extract_jpa_queries_from_repositories(jpa_repositories)
    config_files = extract_config_files(directory)
    test_classes = extract_test_classes_from_classes(classes_list)
    
    xml_mappers = extract_mybatis_xml_mappers(directory)
    mybatis_mappers.extend(xml_mappers)
    
    sql_statements = extract_sql_statements_from_mappers(mybatis_mappers, project_name)
    
    resultmap_mapping_analysis = analyze_mybatis_resultmap_mapping(mybatis_mappers, sql_statements)
    sql_method_relationships = analyze_sql_method_relationships(sql_statements, classes_list)
    db_call_chain_analysis = generate_db_call_chain_analysis(sql_statements, classes_list)
    
    logger.info(f"Java project analysis complete:")
    logger.info(f"  - Java files processed: {processed_file_count}/{java_file_count}")
    logger.info(f"  - Packages found: {len(packages)}")
    logger.info(f"  - Classes found: {len(classes)}")
    logger.info(f"  - Classes list length: {len(classes_list)}")
    
    return list(packages.values()), classes_list, class_to_package_map, beans, dependencies, endpoints, mybatis_mappers, jpa_entities, jpa_repositories, jpa_queries, config_files, test_classes, sql_statements, project_name