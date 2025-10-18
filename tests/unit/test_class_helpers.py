"""class_helpers 유틸리티 함수 테스트"""

import pytest
from csa.utils.class_helpers import (
    is_external_library,
    extract_package_from_full_name,
    normalize_class_identifier,
)


class TestIsExternalLibrary:
    """is_external_library 함수 테스트"""

    def test_java_standard_library_full_name(self):
        """Java 표준 라이브러리 - full qualified name"""
        assert is_external_library("java.util.List") is True
        assert is_external_library("java.lang.String") is True
        assert is_external_library("java.time.LocalDateTime") is True

    def test_java_standard_library_simple_name(self):
        """Java 표준 라이브러리 - simple name + package"""
        assert is_external_library("List", "java.util") is True
        assert is_external_library("String", "java.lang") is True

    def test_javax_library(self):
        """javax 라이브러리"""
        assert is_external_library("javax.servlet.Servlet") is True
        assert is_external_library("javax.annotation.Nullable") is True

    def test_jakarta_library(self):
        """Jakarta 라이브러리"""
        assert is_external_library("jakarta.servlet.Servlet") is True

    def test_spring_framework(self):
        """Spring Framework"""
        assert is_external_library("org.springframework.stereotype.Component") is True
        assert is_external_library("org.springframework.beans.factory.annotation.Autowired") is True
        assert is_external_library("Component", "org.springframework.stereotype") is True

    def test_apache_library(self):
        """Apache 라이브러리"""
        assert is_external_library("org.apache.commons.lang.StringUtils") is True

    def test_hibernate_library(self):
        """Hibernate 라이브러리"""
        assert is_external_library("org.hibernate.Session") is True

    def test_lombok_library(self):
        """Lombok 라이브러리"""
        assert is_external_library("lombok.extern.slf4j.Slf4j") is True
        assert is_external_library("lombok.Data") is True

    def test_jackson_library(self):
        """Jackson 라이브러리"""
        assert is_external_library("com.fasterxml.jackson.databind.ObjectMapper") is True

    def test_logging_library(self):
        """로깅 라이브러리"""
        assert is_external_library("org.slf4j.Logger") is True
        assert is_external_library("ch.qos.logback.classic.Logger") is True

    def test_project_internal_class(self):
        """프로젝트 내부 클래스"""
        assert is_external_library("UserService", "com.carcare.service") is False
        assert is_external_library("com.carcare.service.UserService") is False
        assert is_external_library("VehicleValidator", "com.carcare.domain.vehicle.validator") is False
        assert is_external_library("com.carcare.domain.vehicle.validator.VehicleValidator") is False

    def test_no_package_defaults_to_external(self):
        """패키지 정보 없으면 외부 라이브러리로 간주"""
        assert is_external_library("UnknownClass") is True
        assert is_external_library("SomeClass", None) is True

    def test_empty_package_defaults_to_external(self):
        """빈 패키지도 외부 라이브러리로 간주"""
        assert is_external_library("MyClass", "") is True


class TestExtractPackageFromFullName:
    """extract_package_from_full_name 함수 테스트"""

    def test_full_qualified_name(self):
        """일반적인 full qualified name"""
        name, package = extract_package_from_full_name("com.carcare.service.UserService")
        assert name == "UserService"
        assert package == "com.carcare.service"

    def test_java_util(self):
        """Java 표준 라이브러리"""
        name, package = extract_package_from_full_name("java.util.List")
        assert name == "List"
        assert package == "java.util"

    def test_spring_framework_class(self):
        """Spring Framework 클래스"""
        name, package = extract_package_from_full_name(
            "org.springframework.beans.factory.annotation.Autowired"
        )
        assert name == "Autowired"
        assert package == "org.springframework.beans.factory.annotation"

    def test_simple_name_no_package(self):
        """패키지 없는 simple name"""
        name, package = extract_package_from_full_name("UserService")
        assert name == "UserService"
        assert package is None

    def test_nested_package(self):
        """깊은 패키지 구조"""
        name, package = extract_package_from_full_name("com.a.b.c.d.MyClass")
        assert name == "MyClass"
        assert package == "com.a.b.c.d"

    def test_single_level_package(self):
        """한 단계 패키지"""
        name, package = extract_package_from_full_name("com.MyClass")
        assert name == "MyClass"
        assert package == "com"


class TestNormalizeClassIdentifier:
    """normalize_class_identifier 함수 테스트"""

    def test_with_package(self):
        """클래스명과 패키지 모두 제공"""
        result = normalize_class_identifier("UserService", "com.carcare.service")
        assert result == {"name": "UserService", "package": "com.carcare.service"}

    def test_full_qualified_name(self):
        """Full qualified name"""
        result = normalize_class_identifier("com.carcare.service.UserService")
        assert result == {"name": "UserService", "package": "com.carcare.service"}

    def test_full_qualified_name_with_package(self):
        """Full qualified name + package 제공 (package가 우선)"""
        result = normalize_class_identifier(
            "com.carcare.service.UserService",
            "com.carcare.service"
        )
        assert result == {"name": "UserService", "package": "com.carcare.service"}

    def test_inner_class(self):
        """내부 클래스 처리"""
        result = normalize_class_identifier("UserService$Builder", "com.carcare.service")
        assert result == {"name": "UserService", "package": "com.carcare.service"}

    def test_inner_class_full_qualified_name(self):
        """내부 클래스 full qualified name"""
        result = normalize_class_identifier("com.carcare.service.UserService$Builder")
        assert result == {"name": "UserService", "package": "com.carcare.service"}

    def test_simple_name_no_package(self):
        """Simple name, no package"""
        result = normalize_class_identifier("UserService")
        assert result == {"name": "UserService", "package": None}

    def test_simple_name_with_package(self):
        """Simple name with package"""
        result = normalize_class_identifier("List", "java.util")
        assert result == {"name": "List", "package": "java.util"}

    def test_multiple_dollar_signs(self):
        """다중 내부 클래스 (첫 번째만 사용)"""
        result = normalize_class_identifier(
            "UserService$Builder$Inner",
            "com.carcare.service"
        )
        assert result == {"name": "UserService", "package": "com.carcare.service"}


class TestIntegration:
    """통합 테스트"""

    def test_library_detection_workflow(self):
        """라이브러리 감지 및 정규화 워크플로우"""
        # 외부 라이브러리
        full_name = "org.springframework.stereotype.Component"
        is_external = is_external_library(full_name)
        assert is_external is True

        # 정규화
        normalized = normalize_class_identifier(full_name)
        assert normalized["name"] == "Component"
        assert normalized["package"] == "org.springframework.stereotype"

    def test_internal_class_workflow(self):
        """프로젝트 내부 클래스 처리 워크플로우"""
        # 내부 클래스
        full_name = "com.carcare.domain.vehicle.validator.VehicleValidator"
        is_external = is_external_library(full_name)
        assert is_external is False

        # 정규화
        normalized = normalize_class_identifier(full_name)
        assert normalized["name"] == "VehicleValidator"
        assert normalized["package"] == "com.carcare.domain.vehicle.validator"

    def test_inner_class_workflow(self):
        """내부 클래스 처리 워크플로우"""
        # 내부 클래스
        full_name = "com.carcare.service.UserService$Builder"
        is_external = is_external_library(full_name)
        assert is_external is False

        # 정규화
        normalized = normalize_class_identifier(full_name)
        assert normalized["name"] == "UserService"
        assert normalized["package"] == "com.carcare.service"
