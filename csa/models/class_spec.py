"""
클래스 명세서 생성을 위한 데이터 모델
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class FieldSpec(BaseModel):
    """필드 명세 정보"""
    name: str
    logical_name: str = ""
    type: str
    modifiers: List[str] = []
    annotations: List[str] = []
    initial_value: str = ""
    description: str = ""


class ParameterSpec(BaseModel):
    """파라미터 명세 정보"""
    name: str
    logical_name: str = ""
    type: str
    required: bool = True
    description: str = ""


class SqlStatementSpec(BaseModel):
    """SQL 문 명세 정보"""
    sql_id: str
    sql_type: str
    tables: List[str] = []
    complexity: Optional[int] = None


class EndpointSpec(BaseModel):
    """REST Endpoint 명세 정보"""
    path: str = ""
    http_method: str = ""
    request_body_type: str = ""
    response_type: str = ""


class MethodSpec(BaseModel):
    """메서드 명세 정보"""
    name: str
    logical_name: str = ""
    return_type: str
    parameters: List[ParameterSpec] = []
    modifiers: List[str] = []
    annotations: List[str] = []
    description: str = ""
    sql_statements: List[SqlStatementSpec] = []
    endpoint: Optional[EndpointSpec] = None

    @property
    def access_modifier(self) -> str:
        """접근 제어자 반환"""
        if 'public' in self.modifiers:
            return 'public'
        elif 'protected' in self.modifiers:
            return 'protected'
        elif 'private' in self.modifiers:
            return 'private'
        return 'package-private'


class DependencySpec(BaseModel):
    """의존성 명세 정보"""
    bean_name: str
    dependency_class: str
    bean_type: str = ""
    injection_type: str = ""  # constructor, field, setter
    field_name: str = ""
    description: str = ""


class TableUsageSpec(BaseModel):
    """테이블 사용 명세 정보"""
    table_name: str
    db_schema: str = "public"  # schema → db_schema (Pydantic BaseModel.schema() 충돌 방지)
    operations: List[str] = []  # C, R, U, D
    description: str = ""


class ClassSpecData(BaseModel):
    """클래스 명세서 전체 데이터"""
    # 기본 정보
    class_name: str
    logical_name: str = ""
    package_name: str = ""
    type: str = "class"  # class, interface, enum
    sub_type: str = ""  # controller, service, repository, etc.
    description: str = ""
    project_name: str = ""

    # 클래스 특성
    superclass: Optional[str] = None
    interfaces: List[str] = []
    annotations: List[str] = []

    # Spring Bean 정보
    bean_name: str = ""
    bean_type: str = ""
    scope: str = ""

    # REST Endpoint 정보 (Controller인 경우)
    base_path: str = ""

    # 속성(필드) 목록
    fields: List[FieldSpec] = []

    # 메서드 목록
    methods: List[MethodSpec] = []

    # 의존성 정보
    dependencies: List[DependencySpec] = []

    # 데이터베이스 연관 정보
    table_usage: List[TableUsageSpec] = []

    # 메타 정보
    generated_at: str = ""
    file_path: str = ""

    def get_public_methods(self) -> List[MethodSpec]:
        """Public 메서드만 반환"""
        return [m for m in self.methods if 'public' in m.modifiers]

    def get_protected_methods(self) -> List[MethodSpec]:
        """Protected 메서드만 반환"""
        return [m for m in self.methods if 'protected' in m.modifiers]

    def get_private_methods(self) -> List[MethodSpec]:
        """Private 메서드만 반환"""
        return [m for m in self.methods if 'private' in m.modifiers]

    def get_package_private_methods(self) -> List[MethodSpec]:
        """Package-private 메서드만 반환"""
        return [m for m in self.methods if not any(mod in m.modifiers for mod in ['public', 'protected', 'private'])]


class ClassSpecOptions(BaseModel):
    """클래스 명세서 생성 옵션"""
    project_name: str
    class_name: str
    output_dir: str = "./output/class-spec"
    include_diagram: bool = False
    include_crud_info: bool = True
