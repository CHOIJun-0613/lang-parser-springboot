"""Class 노드 관련 유틸리티 함수"""

from typing import Optional


def is_external_library(class_name: str, package: Optional[str] = None) -> bool:
    """
    외부 라이브러리 클래스인지 판별

    외부 라이브러리(Java 표준, Spring Framework 등)인 경우 True,
    프로젝트 내부 클래스인 경우 False를 반환합니다.

    Args:
        class_name: 클래스명 (full qualified name 또는 simple name)
        package: 패키지명 (선택적)

    Returns:
        외부 라이브러리이면 True, 프로젝트 내부이면 False

    Examples:
        >>> is_external_library("java.util.List")
        True
        >>> is_external_library("List", "java.util")
        True
        >>> is_external_library("UserService", "com.carcare.service")
        False
        >>> is_external_library("com.carcare.service.UserService")
        False
    """
    # Full qualified name에서 패키지 추출
    if "." in class_name and not package:
        parts = class_name.rsplit(".", 1)
        if len(parts) == 2:
            package = parts[0]

    if not package:
        # 패키지 정보 없으면 외부 라이브러리로 간주
        return True

    # 외부 라이브러리 패키지 패턴
    external_prefixes = (
        "java.",
        "javax.",
        "jakarta.",
        "org.springframework.",
        "org.apache.",
        "org.hibernate.",
        "org.slf4j.",
        "org.junit.",
        "org.mockito.",
        "org.hamcrest.",
        "lombok.",
        "lombok",
        "com.fasterxml.jackson.",
        "ch.qos.logback.",
        "junit.",
    )

    return package.startswith(external_prefixes)


def extract_package_from_full_name(full_name: str) -> tuple[str, Optional[str]]:
    """
    Full qualified name에서 클래스명과 패키지 분리

    전체 클래스명(package.ClassName 형식)을 입력받아
    클래스명과 패키지명을 분리하여 반환합니다.

    Args:
        full_name: 전체 클래스명 (예: "com.carcare.service.UserService")

    Returns:
        (class_name, package) 튜플

    Examples:
        >>> extract_package_from_full_name("com.carcare.service.UserService")
        ("UserService", "com.carcare.service")
        >>> extract_package_from_full_name("UserService")
        ("UserService", None)
        >>> extract_package_from_full_name("java.util.List")
        ("List", "java.util")
    """
    if "." not in full_name:
        return full_name, None

    parts = full_name.rsplit(".", 1)
    return parts[1], parts[0]


def normalize_class_identifier(
    class_name: str,
    package: Optional[str] = None
) -> dict[str, Optional[str]]:
    """
    Class 노드 식별자를 정규화

    내부 클래스($), full qualified name 등 다양한 형식의 클래스명을
    정규화하여 일관된 식별자를 반환합니다.

    Args:
        class_name: 클래스명
        package: 패키지명

    Returns:
        정규화된 식별자 dict (keys: "name", "package")

    Examples:
        >>> normalize_class_identifier("UserService", "com.carcare.service")
        {"name": "UserService", "package": "com.carcare.service"}
        >>> normalize_class_identifier("com.carcare.service.UserService")
        {"name": "UserService", "package": "com.carcare.service"}
        >>> normalize_class_identifier("UserService$Builder", "com.carcare.service")
        {"name": "UserService", "package": "com.carcare.service"}
    """
    # Full qualified name인 경우 분리 (package가 명시적으로 주어진 경우는 제외)
    if "." in class_name:
        extracted_name, extracted_package = extract_package_from_full_name(class_name)
        # package가 명시적으로 주어진 경우는 그것을 사용
        if package is None:
            class_name = extracted_name
            package = extracted_package
        # 명시적 package가 있으면 추출된 name만 사용
        else:
            class_name = extracted_name

    # 내부 클래스 처리 (예: "UserService$InnerClass" -> "UserService")
    if "$" in class_name:
        class_name = class_name.split("$")[0]

    return {
        "name": class_name,
        "package": package,
    }


__all__ = [
    "is_external_library",
    "extract_package_from_full_name",
    "normalize_class_identifier",
]
