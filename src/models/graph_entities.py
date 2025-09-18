from pydantic import BaseModel
from typing import Literal


class Package(BaseModel):
    """Represents a Java package."""

    name: str
    logical_name: str = ""


class Property(BaseModel):
    """Represents a field or property within a class."""

    name: str
    type: str
    modifiers: list[str] = []


class Method(BaseModel):
    """Represents a method within a class."""

    name: str
    logical_name: str = ""
    return_type: str
    parameters: list[Property] = []
    modifiers: list[str] = []
    source: str = ""


class MethodCall(BaseModel):
    """Represents a method call from one method to another."""

    source_package: str
    source_class: str
    source_method: str
    target_package: str
    target_class: str
    target_method: str

    def dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            "source_package": self.source_package,
            "source_class": self.source_class,
            "source_method": self.source_method,
            "target_package": self.target_package,
            "target_class": self.target_class,
            "target_method": self.target_method
        }


class Class(BaseModel):
    """Represents a Java class with its methods, properties, and relationships."""

    name: str
    logical_name: str = ""
    file_path: str
    type: Literal["class", "interface", "enum"] = "class"
    methods: list[Method] = []
    properties: list[Property] = []
    calls: list[MethodCall] = []
    source: str = ""
    superclass: str | None = None
    interfaces: list[str] = []
    imports: list[str] = []

