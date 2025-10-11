"""
JUnit test extraction utilities.
"""
from __future__ import annotations

from typing import List

from csa.models.graph_entities import Class, TestClass, TestMethod

from .utils import classify_test_annotation

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


__all__ = [
    "analyze_test_methods",
    "extract_test_classes_from_classes",
]

