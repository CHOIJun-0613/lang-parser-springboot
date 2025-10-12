import pytest
from unittest.mock import MagicMock, patch
import json # Added import for json

from csa.services.graph_db import GraphDB
from csa.models.graph_entities import Class, Field, Method, MethodCall # Import Method and Field


def _find_call_kwargs(call_args_list, **expected_kwargs):
    """mock_tx.run 호출 기록 중 원하는 파라미터 조합을 찾아 반환합니다.
    모든 키-값 조건을 만족하는 호출이 없으면 테스트를 실패시킵니다.
    """
    for call in call_args_list:
        kwargs = call[1]  # call.args 는 0, kwargs 는 1
        if all(kwargs.get(key) == value for key, value in expected_kwargs.items()):
            return kwargs
    expected_str = ", ".join(f"{key}={value!r}" for key, value in expected_kwargs.items())
    pytest.fail(f"mock_tx.run 호출에서 {expected_str} 조건을 만족하는 항목을 찾지 못했습니다.")


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

    run_calls = mock_tx.run.call_args_list
    assert run_calls, "mock_tx.run 이 호출되지 않았습니다."

    class_kwargs = _find_call_kwargs(run_calls, name="TestClass")
    assert class_kwargs["package_name"] == "com.test"

    prop_kwargs = _find_call_kwargs(run_calls, prop_name="testProp")
    assert prop_kwargs["class_name"] == "TestClass"
    assert prop_kwargs["prop_type"] == "int"
    assert json.loads(prop_kwargs["prop_modifiers_json"]) == []

    call_kwargs = _find_call_kwargs(
        run_calls,
        source_method="myCallingMethod",
        target_method="someCalledMethod",
    )
    assert call_kwargs["source_class"] == "TestClass"
    assert call_kwargs["source_package"] == "com.test"
    assert call_kwargs["target_class"] == "AnotherClass"
    assert call_kwargs["target_package"] == "com.another"


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
    run_calls = mock_tx.run.call_args_list
    assert run_calls, "mock_tx.run 이 호출되지 않았습니다."

    class_kwargs = _find_call_kwargs(run_calls, name="Greeter")
    assert class_kwargs["package_name"] == "com.example"

    greeting_kwargs = _find_call_kwargs(run_calls, prop_name="greeting")
    assert greeting_kwargs["prop_type"] == "String"
    assert json.loads(greeting_kwargs["prop_modifiers_json"]) == ["private"]

    max_value_kwargs = _find_call_kwargs(run_calls, prop_name="MAX_VALUE")
    assert max_value_kwargs["prop_type"] == "int"
    assert json.loads(max_value_kwargs["prop_modifiers_json"]) == ["public", "static", "final"]
