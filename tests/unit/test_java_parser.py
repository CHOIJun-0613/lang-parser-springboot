import pytest
from unittest.mock import patch, mock_open
from src.services.java_parser import parse_java_project
from src.models.graph_entities import Class, Property, Method, MethodCall

@patch("os.walk")
@patch("builtins.open", new_callable=mock_open, read_data='''
package com.example;

import com.external.OtherClass;

class MyClass {
    private String myField;

    public MyClass() { 
        // constructor
    }

    public void myMethod(String name) {
        OtherClass other = new OtherClass();
        other.doSomething();
    }

    public int anotherMethod(int count) {
        return count * 2;
    }
}
''')
def test_parse_java_project(mock_file, mock_walk):
    # Given
    mock_walk.return_value = [("/fake/dir", [], ["MyClass.java"])]

    # When
    classes = parse_java_project("/fake/dir")

    # Then
    assert len(classes) == 1
    my_class = classes[0]

    assert my_class.name == "MyClass"
    assert my_class.package == "com.example"
    
    assert len(my_class.properties) == 1
    assert my_class.properties[0].name == "myField"
    assert my_class.properties[0].type == "String"

    # Check method calls
    assert len(my_class.calls) == 1
    call = my_class.calls[0]
    assert isinstance(call, MethodCall)
    assert call.source_package == "com.example"
    assert call.source_class == "MyClass"
    assert call.source_method == "myMethod"
    assert call.target_package == "com.external"
    assert call.target_class == "OtherClass"
    assert call.target_method == "doSomething"

    assert len(my_class.methods) == 3

    # Check constructor
    constructor = next((m for m in my_class.methods if m.name == "MyClass"), None)
    assert constructor is not None
    assert constructor.return_type == "constructor"
    assert len(constructor.parameters) == 0

    # Check myMethod
    my_method = next((m for m in my_class.methods if m.name == "myMethod"), None)
    assert my_method is not None
    assert my_method.return_type == "void"
    assert len(my_method.parameters) == 1
    assert my_method.parameters[0].name == "name"
    assert my_method.parameters[0].type == "String"

    # Check anotherMethod
    another_method = next((m for m in my_class.methods if m.name == "anotherMethod"), None)
    assert another_method is not None
    assert another_method.return_type == "int"
    assert len(another_method.parameters) == 1
    assert another_method.parameters[0].name == "count"
    assert another_method.parameters[0].type == "int"
