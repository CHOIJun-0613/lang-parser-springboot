"""
Utility helpers for Java parsing.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import List

from csa.vendor import javalang

from csa.models.graph_entities import Annotation, Class, Field, Method, MethodCall


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

def extract_sub_type(package_name: str, class_name: str, annotations: list[Annotation]) -> str:
    """
    패키지명과 클래스명, 어노테이션을 기반으로 sub_type을 추출합니다.
    
    Args:
        package_name: 패키지명
        class_name: 클래스명
        annotations: 클래스 어노테이션 리스트
        
    Returns:
        sub_type (controller, service, util, dto, config, mapper, repository, entity, exception, client)
    """
    # 패키지명의 마지막 단어 추출
    package_parts = package_name.split('.')
    last_package_part = package_parts[-1].lower() if package_parts else ""
    
    # 어노테이션 기반 판단
    annotation_names = [ann.name.lower() for ann in annotations]
    
    # Controller 판단
    if any(ann in annotation_names for ann in ['@controller', '@restcontroller', '@controlleradvice']):
        return 'controller'
    
    # Service 판단
    if any(ann in annotation_names for ann in ['@service', '@component']):
        return 'service'
    
    # Repository 판단
    if any(ann in annotation_names for ann in ['@repository', '@mapper']):
        return 'repository'
    
    # Entity 판단
    if any(ann in annotation_names for ann in ['@entity', '@table', '@mappedsuperclass']):
        return 'entity'
    
    # Configuration 판단
    if any(ann in annotation_names for ann in ['@configuration', '@config', '@enableautoconfiguration']):
        return 'config'
    
    # 패키지명 기반 판단
    if last_package_part in ['controller', 'controllers']:
        return 'controller'
    elif last_package_part in ['service', 'services']:
        return 'service'
    elif last_package_part in ['util', 'utils', 'utility']:
        return 'util'
    elif last_package_part in ['dto', 'dtos', 'model', 'models']:
        return 'dto'
    elif last_package_part in ['config', 'configuration']:
        return 'config'
    elif last_package_part in ['mapper', 'mappers']:
        return 'mapper'
    elif last_package_part in ['repository', 'repositories']:
        return 'repository'
    elif last_package_part in ['entity', 'entities', 'domain']:
        return 'entity'
    elif last_package_part in ['exception', 'exceptions']:
        return 'exception'
    elif last_package_part in ['client', 'clients']:
        return 'client'
    
    # 클래스명 기반 판단 (fallback)
    class_name_lower = class_name.lower()
    if class_name_lower.endswith('controller'):
        return 'controller'
    elif class_name_lower.endswith('service'):
        return 'service'
    elif class_name_lower.endswith('util') or class_name_lower.endswith('utils'):
        return 'util'
    elif class_name_lower.endswith('dto') or class_name_lower.endswith('request') or class_name_lower.endswith('response'):
        return 'dto'
    elif class_name_lower.endswith('config') or class_name_lower.endswith('configuration'):
        return 'config'
    elif class_name_lower.endswith('mapper'):
        return 'mapper'
    elif class_name_lower.endswith('repository'):
        return 'repository'
    elif class_name_lower.endswith('entity'):
        return 'entity'
    elif class_name_lower.endswith('exception'):
        return 'exception'
    elif class_name_lower.endswith('client'):
        return 'client'
    
    return ""

__all__ = [
    "classify_springboot_annotation",
    "classify_test_annotation",
    "extract_project_name",
    "extract_sub_type",
    "generate_lombok_methods",
    "parse_annotations",
]
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
            logical_name="",
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
        parameters=[Field(name="obj", logical_name="", type="Object", package_name=package_name, class_name=class_name)],
        modifiers=["public"],
        source="",  # Generated method, no source
        package_name=package_name,
        annotations=[],
        description="Generated equals method for object comparison",  # Generated method description
        ai_description="",
        is_lombok_generated=True  # Lombok generated method flag
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
        ai_description="",
        is_lombok_generated=True  # Lombok generated method flag
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
        ai_description="",
        is_lombok_generated=True  # Lombok generated method flag
    )
    methods.append(tostring_method)
    
    return methods

