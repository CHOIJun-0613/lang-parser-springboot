from pydantic import BaseModel
from typing import Literal, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from typing import List


class Annotation(BaseModel):
    """Represents a Java annotation."""
    
    name: str
    parameters: dict[str, Any] = {}
    target_type: str = "class"  # "class", "method", "field"
    category: str = "other"  # "component", "injection", "web", "jpa", "test", "security", "validation", "other"
    description: str = ""  # Brief description of the annotation
    ai_description: str = ""  # AI-generated description of the annotation


class Package(BaseModel):
    """Represents a Java package."""

    name: str
    logical_name: str = ""
    description: str = ""  # Brief description of the package
    ai_description: str = ""  # AI-generated description of the package


class Field(BaseModel):
    """Represents a field or property within a class."""

    name: str
    logical_name: str = ""
    type: str
    modifiers: list[str] = []
    package_name: str = ""
    class_name: str = ""
    annotations: list[Annotation] = []
    initial_value: str = ""  # Initial value of the field
    description: str = ""  # Brief description of the field
    ai_description: str = ""  # AI-generated description of the field


class Method(BaseModel):
    """Represents a method within a class."""

    name: str
    logical_name: str = ""
    return_type: str
    parameters: list[Field] = []
    modifiers: list[str] = []
    source: str = ""
    package_name: str = ""
    annotations: list[Annotation] = []
    description: str = ""  # Brief description of the method
    ai_description: str = ""  # AI-generated description of the method


class MethodCall(BaseModel):
    """Represents a method call from one method to another."""

    source_package: str
    source_class: str
    source_method: str
    target_package: str
    target_class: str
    target_method: str
    call_order: int = 0  # 순서 정보 (0부터 시작)
    line_number: int = 0  # 소스 코드에서의 라인 번호
    return_type: str = "void"  # 피호출 메서드의 return type
    description: str = ""  # Brief description of the method call
    ai_description: str = ""  # AI-generated description of the method call

    def dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            "source_package": self.source_package,
            "source_class": self.source_class,
            "source_method": self.source_method,
            "target_package": self.target_package,
            "target_class": self.target_class,
            "target_method": self.target_method,
            "call_order": self.call_order,
            "line_number": self.line_number,
            "return_type": self.return_type
        }


class Bean(BaseModel):
    """Represents a Spring Bean."""
    
    name: str
    type: str  # "component", "service", "repository", "controller", "configuration"
    scope: str  # "singleton", "prototype", "request", "session"
    class_name: str
    package_name: str = ""
    annotation_names: list[str] = []  # Just store annotation names
    method_count: int = 0  # Number of methods
    property_count: int = 0  # Number of properties
    description: str = ""  # Brief description of the bean
    ai_description: str = ""  # AI-generated description of the bean


class BeanDependency(BaseModel):
    """Represents a dependency between Spring Beans."""
    
    source_bean: str
    target_bean: str
    injection_type: str  # "field", "constructor", "setter"
    field_name: str = ""
    method_name: str = ""
    parameter_name: str = ""
    description: str = ""  # Brief description of the dependency
    ai_description: str = ""  # AI-generated description of the dependency


class Endpoint(BaseModel):
    """Represents a REST API endpoint."""
    
    path: str
    method: str  # "GET", "POST", "PUT", "DELETE", "PATCH"
    controller_class: str
    handler_method: str
    parameters: list[dict] = []  # Request parameters
    return_type: str = ""
    annotations: list[str] = []  # Web annotations on the method
    full_path: str = ""  # Complete URL path including class-level mapping
    description: str = ""  # Brief description of the endpoint
    ai_description: str = ""  # AI-generated description of the endpoint


class MyBatisMapper(BaseModel):
    """Represents a MyBatis Mapper interface or XML file."""
    
    name: str
    type: str  # "interface", "xml"
    namespace: str = ""
    methods: list[dict] = []  # Mapper methods
    sql_statements: list[dict] = []  # SQL statements
    file_path: str = ""
    package_name: str = ""
    description: str = ""  # Brief description of the mapper
    ai_description: str = ""  # AI-generated description of the mapper


class MyBatisSqlStatement(BaseModel):
    """Represents a MyBatis SQL statement."""
    
    id: str  # Method name or statement ID
    sql_type: str  # "SELECT", "INSERT", "UPDATE", "DELETE"
    sql_content: str = ""
    parameter_type: str = ""
    result_type: str = ""
    result_map: str = ""
    mapper_name: str = ""
    annotations: list[str] = []  # MyBatis annotations
    description: str = ""  # Brief description of the SQL statement
    ai_description: str = ""  # AI-generated description of the SQL statement


class SqlStatement(BaseModel):
    """Represents a SQL statement node in the graph database."""
    
    id: str  # Statement ID
    sql_type: str  # "SELECT", "INSERT", "UPDATE", "DELETE"
    sql_content: str = ""
    parameter_type: str = ""
    result_type: str = ""
    result_map: str = ""
    mapper_name: str = ""
    annotations: list[Annotation] = []  # MyBatis annotations as Annotation objects
    project_name: str = ""
    description: str = ""  # Brief description of the SQL statement
    ai_description: str = ""  # AI-generated description of the SQL statement


class MyBatisResultMap(BaseModel):
    """Represents a MyBatis ResultMap."""
    
    id: str
    type: str
    properties: list[dict] = []  # Property mappings
    associations: list[dict] = []  # Association mappings
    collections: list[dict] = []  # Collection mappings
    mapper_name: str = ""
    description: str = ""  # Brief description of the result map
    ai_description: str = ""  # AI-generated description of the result map


class JpaEntity(BaseModel):
    """Represents a JPA Entity."""
    
    name: str
    table_name: str = ""
    columns: list[dict] = []  # Column mappings
    relationships: list[dict] = []  # Entity relationships
    annotations: list[str] = []  # JPA annotations
    package_name: str = ""
    file_path: str = ""
    description: str = ""  # Brief description of the entity
    ai_description: str = ""  # AI-generated description of the entity


class JpaColumn(BaseModel):
    """Represents a JPA Column mapping."""
    
    property_name: str
    column_name: str = ""
    data_type: str = ""
    nullable: bool = True
    unique: bool = False
    length: int = 0
    precision: int = 0
    scale: int = 0
    annotations: list[str] = []  # Column annotations
    description: str = ""  # Brief description of the column
    ai_description: str = ""  # AI-generated description of the column


class JpaRelationship(BaseModel):
    """Represents a JPA Entity relationship."""
    
    type: str  # "OneToOne", "OneToMany", "ManyToOne", "ManyToMany"
    target_entity: str = ""
    mapped_by: str = ""
    join_column: str = ""
    join_table: str = ""
    cascade: list[str] = []  # Cascade types
    fetch: str = "LAZY"  # Fetch type
    annotations: list[str] = []  # Relationship annotations
    description: str = ""  # Brief description of the relationship
    ai_description: str = ""  # AI-generated description of the relationship


class ConfigFile(BaseModel):
    """Represents a configuration file."""
    
    name: str
    file_path: str
    file_type: str  # "yaml", "yml", "properties"
    properties: dict[str, Any] = {}
    sections: list[dict] = []  # Configuration sections
    profiles: list[str] = []  # Active profiles
    environment: str = ""  # Environment (dev, prod, test)
    description: str = ""  # Brief description of the config file
    ai_description: str = ""  # AI-generated description of the config file


class DatabaseConfig(BaseModel):
    """Represents database configuration."""
    
    driver: str = ""
    url: str = ""
    username: str = ""
    password: str = ""
    dialect: str = ""
    hibernate_ddl_auto: str = ""
    show_sql: bool = False
    format_sql: bool = False
    jpa_properties: dict[str, Any] = {}
    description: str = ""  # Brief description of the database config
    ai_description: str = ""  # AI-generated description of the database config


class ServerConfig(BaseModel):
    """Represents server configuration."""
    
    port: int = 8080
    context_path: str = ""
    servlet_path: str = ""
    ssl_enabled: bool = False
    ssl_key_store: str = ""
    ssl_key_store_password: str = ""
    ssl_key_store_type: str = ""
    description: str = ""  # Brief description of the server config
    ai_description: str = ""  # AI-generated description of the server config


class SecurityConfig(BaseModel):
    """Represents security configuration."""
    
    enabled: bool = False
    authentication_type: str = ""  # "jwt", "session", "oauth2"
    jwt_secret: str = ""
    jwt_expiration: int = 0
    cors_allowed_origins: list[str] = []
    cors_allowed_methods: list[str] = []
    cors_allowed_headers: list[str] = []
    description: str = ""  # Brief description of the security config
    ai_description: str = ""  # AI-generated description of the security config


class LoggingConfig(BaseModel):
    """Represents logging configuration."""
    
    level: str = "INFO"
    pattern: str = ""
    file_path: str = ""
    max_file_size: str = ""
    max_history: int = 0
    console_output: bool = True
    description: str = ""  # Brief description of the logging config
    ai_description: str = ""  # AI-generated description of the logging config


class TestClass(BaseModel):
    """Represents a test class."""
    
    name: str
    package_name: str = ""
    test_framework: str = ""  # "junit", "testng", "spock"
    test_type: str = ""  # "unit", "integration", "end-to-end"
    annotations: list[str] = []  # Test annotations
    test_methods: list[dict] = []  # Test methods
    setup_methods: list[dict] = []  # Setup/teardown methods
    mock_dependencies: list[dict] = []  # Mocked dependencies
    test_configurations: list[dict] = []  # Test configurations
    file_path: str = ""
    description: str = ""  # Brief description of the test class
    ai_description: str = ""  # AI-generated description of the test class


class TestMethod(BaseModel):
    """Represents a test method."""
    
    name: str
    return_type: str = "void"
    annotations: list[str] = []  # Test method annotations
    assertions: list[dict] = []  # Assertions in the test
    mock_calls: list[dict] = []  # Mock method calls
    test_data: list[dict] = []  # Test data setup
    expected_exceptions: list[str] = []  # Expected exceptions
    timeout: int = 0  # Test timeout
    display_name: str = ""  # @DisplayName value
    description: str = ""  # Brief description of the test method
    ai_description: str = ""  # AI-generated description of the test method


class TestConfiguration(BaseModel):
    """Represents test configuration."""
    
    name: str
    type: str = ""  # "configuration", "profile", "property"
    properties: dict[str, Any] = {}
    active_profiles: list[str] = []
    test_slices: list[str] = []  # @WebMvcTest, @DataJpaTest, etc.
    mock_beans: list[dict] = []  # @MockBean definitions
    spy_beans: list[dict] = []  # @SpyBean definitions
    description: str = ""  # Brief description of the test configuration
    ai_description: str = ""  # AI-generated description of the test configuration


class Database(BaseModel):
    """Represents a database."""
    
    name: str
    version: str = ""
    environment: str = ""  # "development", "production", "test"
    description: str = ""
    ai_description: str = ""
    updated_at: str = ""


class Table(BaseModel):
    """Represents a database table."""
    
    name: str
    schema: str = "public"
    comment: str = ""
    ai_description: str = ""
    updated_at: str = ""


class Column(BaseModel):
    """Represents a database column."""
    
    name: str
    data_type: str
    nullable: bool = True
    unique: bool = False
    primary_key: bool = False
    default_value: str = ""
    constraints: list[str] = []
    table_name: str = ""  # Add table_name for relationship
    comment: str = ""
    ai_description: str = ""
    updated_at: str = ""


class Index(BaseModel):
    """Represents a database index."""
    
    name: str
    type: str = "B-tree"  # "B-tree", "UNIQUE", "GIN", "GIST" 등
    columns: list[str] = []
    table_name: str = ""  # Add table_name for relationship
    description: str = ""
    ai_description: str = ""
    updated_at: str = ""


class Constraint(BaseModel):
    """Represents a database constraint."""
    
    name: str
    type: str  # "CHECK", "FOREIGN KEY", "UNIQUE", "PRIMARY KEY" 등
    definition: str = ""
    table_name: str = ""  # Add table_name for relationship
    description: str = ""
    ai_description: str = ""
    updated_at: str = ""


class Class(BaseModel):
    """Represents a Java class with its methods, properties, and relationships."""

    name: str
    logical_name: str = ""
    file_path: str
    type: Literal["class", "interface", "enum"] = "class"
    methods: list[Method] = []
    properties: list[Field] = []
    calls: list[MethodCall] = []
    source: str = ""
    superclass: str | None = None
    interfaces: list[str] = []
    imports: list[str] = []
    annotations: list[Annotation] = []
    package_name: str = ""
    description: str = ""  # Brief description of the class
    ai_description: str = ""  # AI-generated description of the class

