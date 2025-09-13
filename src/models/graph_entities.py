from pydantic import BaseModel
from typing import Literal


class Property(BaseModel):
    """Represents a field or property within a class."""

    name: str
    type: str


class Method(BaseModel):
    """Represents a method within a class."""

    name: str
    return_type: str
    parameters: list[Property] = []


class MethodCall(BaseModel):
    """Represents a method call from one method to another."""

    source_package: str
    source_class: str
    source_method: str
    target_package: str
    target_class: str
    target_method: str


class Class(BaseModel):
    """Represents a Java class, interface, or enum."""

    name: str
    package: str
    file_path: str
    type: Literal["class", "interface", "enum"]
    properties: list[Property] = []
    methods: list[Method] = []
    calls: list[MethodCall] = []
