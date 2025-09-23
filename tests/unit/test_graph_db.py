import pytest
from unittest.mock import MagicMock, patch
import json # Added import for json

from src.services.graph_db import GraphDB
from src.models.graph_entities import Class, Field, Method, MethodCall # Import Method and Field

@pytest.fixture
def mock_db():
    with patch('neo4j.GraphDatabase.driver') as mock_driver_constructor:
        mock_driver_instance = MagicMock()
        mock_driver_constructor.return_value = mock_driver_instance
        db_service = GraphDB("uri", "user", "pass")
        yield db_service, mock_driver_instance
        db_service.close()

def test_add_class(mock_db):
    # Given
    db_service, mock_driver = mock_db
    mock_session = MagicMock()
    mock_tx = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session
    mock_session.write_transaction.side_effect = lambda func, *args: func(mock_tx, *args)

    test_class = Class(
        name="TestClass",
        package="com.test",
        file_path="/path/to/TestClass.java",
        type="class",
        properties=[Field(name="testProp", type="int", description="Test property", ai_description="AI-generated description for testProp")],
        calls=[
            MethodCall(
                source_package="com.test",
                source_class="TestClass",
                source_method="myCallingMethod",
                target_package="com.another",
                target_class="AnotherClass",
                target_method="someCalledMethod"
            )
        ]
    )

    # When
    db_service.add_class(test_class)

    # Then
    assert mock_session.write_transaction.called
    
    # Collect all executed queries
    executed_queries = [call[0][0] for call in mock_tx.run.call_args_list]
    executed_params = [call[1] for call in mock_tx.run.call_args_list]

    # Check the MERGE query for the class itself
    class_query_found = False
    for i, query in enumerate(executed_queries):
        if "MERGE (c:Class {name: $name, package: $package})" in query:
            assert executed_params[i]['name'] == "TestClass"
            assert executed_params[i]['package'] == "com.test"
            class_query_found = True
            break
    assert class_query_found

    # Check the MERGE query for the property
    prop_query_found = False
    for i, query in enumerate(executed_queries):
        if "MERGE (p:Field {name: $prop_name, class_name: $class_name, project_name: $project_name})" in query:
            assert executed_params[i]['prop_name'] == "testProp"
            prop_query_found = True
            break
    assert prop_query_found

    # Check the MERGE query for the call relationship
    call_query_found = False
    for i, query in enumerate(executed_queries):
        if "MERGE (sm)-[r:CALLS]->(tm)" in query: # Changed to match the actual query in graph_db.py
            assert executed_params[i]['source_package'] == "com.test"
            assert executed_params[i]['source_class'] == "TestClass"
            assert executed_params[i]['source_method'] == "myCallingMethod"
            assert executed_params[i]['target_package'] == "com.another"
            assert executed_params[i]['target_class'] == "AnotherClass"
            assert executed_params[i]['target_method'] == "someCalledMethod"
            call_query_found = True
            break
    assert call_query_found


def test_add_class_with_fields(mock_db):
    # Given
    db_service, mock_driver = mock_db
    mock_session = MagicMock()
    mock_tx = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session
    mock_session.write_transaction.side_effect = lambda func, *args: func(mock_tx, *args)

    test_field_private = Field(
        name="greeting", type="String", modifiers=["private"], description="Private greeting field", ai_description="AI-generated description for greeting field"
    )
    test_field_public_static_final = Field(
        name="MAX_VALUE", type="int", modifiers=["public", "static", "final"], description="Public static final constant", ai_description="AI-generated description for MAX_VALUE constant"
    )
    test_class = Class(
        name="Greeter",
        package="com.example",
        file_path="/path/to/Greeter.java",
        source="class Greeter { private String greeting; }",
        properties=[test_field_private, test_field_public_static_final],
    )

    # When
    db_service.add_class(test_class)

    # Then
    # Check the MERGE query for the class itself
    class_merge_call = mock_tx.run.call_args_list[0]
    assert "MERGE (c:Class {name: $name, package: $package})" in class_merge_call[0][0]
    assert class_merge_call[1]['name'] == "Greeter"

    # Check the MERGE query for the first property (greeting)
    prop1_merge_call = mock_tx.run.call_args_list[1]
    assert (
        "MERGE (p:Field {name: $prop_name, class_name: $class_name, project_name: $project_name}) "
        "SET p.modifiers = $prop_modifiers "
        "MERGE (c)-[:HAS_FIELD]->(p)"
    ) in prop1_merge_call[0][0]
    assert prop1_merge_call[1]['prop_name'] == "greeting"
    assert prop1_merge_call[1]['prop_type'] == "String"
    assert prop1_merge_call[1]['prop_modifiers'] == ["private"]

    # Check the MERGE query for the second property (MAX_VALUE)
    prop2_merge_call = mock_tx.run.call_args_list[2]
    assert (
        "MERGE (p:Field {name: $prop_name, class_name: $class_name, project_name: $project_name}) "
        "SET p.modifiers = $prop_modifiers "
        "MERGE (c)-[:HAS_FIELD]->(p)"
    ) in prop2_merge_call[0][0]
    assert prop2_merge_call[1]['prop_name'] == "MAX_VALUE"
    assert prop2_merge_call[1]['prop_type'] == "int"
    assert prop2_merge_call[1]['prop_modifiers'] == ["public", "static", "final"]
