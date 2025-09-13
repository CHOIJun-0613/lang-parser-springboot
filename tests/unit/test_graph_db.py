import pytest
from unittest.mock import MagicMock, patch
from src.services.graph_db import GraphDB
from src.models.graph_entities import Class, Property, MethodCall # Import MethodCall

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
        properties=[Property(name="testProp", type="int")],
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
    
    # Check the MERGE query for the class itself
    class_merge_call = mock_tx.run.call_args_list[0]
    assert "MERGE (c:Class {name: $name, package: $package})" in class_merge_call[0][0]
    assert class_merge_call[1]['name'] == "TestClass"

    # Check the MERGE query for the property
    prop_merge_call = mock_tx.run.call_args_list[1]
    assert "MERGE (p:Property {name: $prop_name, type: $prop_type})" in prop_merge_call[0][0]
    assert prop_merge_call[1]['prop_name'] == "testProp"

    # Check the MERGE query for the call relationship
    call_merge_call = mock_tx.run.call_args_list[2]
    assert "MERGE (c1)-[r:CALLS]->(c2)" in call_merge_call[0][0]
    assert call_merge_call[1]['source_package'] == "com.test"
    assert call_merge_call[1]['source_class'] == "TestClass"
    assert call_merge_call[1]['source_method'] == "myCallingMethod"
    assert call_merge_call[1]['target_package'] == "com.another"
    assert call_merge_call[1]['target_class'] == "AnotherClass"
    assert call_merge_call[1]['target_method'] == "someCalledMethod"
