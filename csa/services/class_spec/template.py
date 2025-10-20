"""
클래스 명세서 템플릿 렌더링
"""
from typing import List
from csa.models.class_spec import ClassSpecData, MethodSpec, FieldSpec, DependencySpec, TableUsageSpec


class ClassSpecTemplate:
    """클래스 명세서 Markdown 템플릿 렌더러"""

    def _escape_markdown_table_cell(self, text: str) -> str:
        """
        Markdown 테이블 셀 내 특수문자 이스케이프

        Args:
            text: 이스케이프할 텍스트

        Returns:
            이스케이프된 텍스트
        """
        if not text or text == '-':
            return text

        text = str(text)  # 문자열로 변환

        # 파이프 문자를 HTML 엔티티로 치환
        text = text.replace('|', '&#124;')

        # 줄바꿈을 공백으로 치환
        text = text.replace('\n', ' ').replace('\r', '')

        # 백틱을 이스케이프 (코드 블록 방지)
        text = text.replace('`', '\\`')

        return text

    def render(self, spec_data: ClassSpecData) -> str:
        """
        클래스 명세서를 Markdown 형식으로 렌더링

        Args:
            spec_data: 클래스 명세서 데이터

        Returns:
            Markdown 형식의 문자열
        """
        sections = [
            self._render_header(),
            self._render_basic_info(spec_data),
            self._render_overview(spec_data),
            self._render_fields(spec_data.fields),
            self._render_methods(spec_data),
            self._render_dependencies(spec_data.dependencies),
            self._render_database_info(spec_data.table_usage),
            self._render_diagrams(spec_data),
        ]

        return "\n\n".join(sections)

    def _render_header(self) -> str:
        """헤더 렌더링"""
        return "# 클래스 명세서"

    def _render_basic_info(self, spec_data: ClassSpecData) -> str:
        """기본 정보 렌더링"""
        lines = [
            "## 1. 기본 정보",
            "",
            "| 항목 | 내용 |",
            "|------|------|",
            f"| **클래스명** | {spec_data.class_name} |",
            f"| **논리명** | {spec_data.logical_name or '-'} |",
            f"| **패키지** | {spec_data.package_name or '-'} |",
            f"| **클래스 유형** | {spec_data.type} |",
            f"| **세부 유형** | {spec_data.sub_type or '-'} |",
            f"| **작성일자** | {spec_data.generated_at} |",
            f"| **프로젝트명** | {spec_data.project_name} |",
        ]
        return "\n".join(lines)

    def _render_overview(self, spec_data: ClassSpecData) -> str:
        """클래스 개요 렌더링"""
        lines = [
            "## 2. 클래스 개요",
            "",
            "### 2.1 설명",
            spec_data.description or "_설명 없음_",
            "",
            "### 2.2 클래스 특성",
            f"- **상위 클래스**: {spec_data.superclass or 'None'}",
            f"- **구현 인터페이스**: {', '.join(spec_data.interfaces) if spec_data.interfaces else 'None'}",
            f"- **어노테이션**: {', '.join(spec_data.annotations) if spec_data.annotations else 'None'}",
        ]

        # Spring Bean 정보
        if spec_data.bean_name:
            lines.extend([
                "",
                "### 2.3 Spring Bean 정보",
                f"- **Bean 이름**: {spec_data.bean_name}",
                f"- **Bean 타입**: {spec_data.bean_type or '-'}",
                f"- **Scope**: {spec_data.scope or 'singleton'}",
            ])

        # REST Endpoint 정보
        if spec_data.base_path:
            lines.extend([
                "",
                "### 2.4 REST Endpoint 정보",
                f"- **Base Path**: {spec_data.base_path}",
                "- **매핑 정보**: 하단 메서드 목록 참조",
            ])

        return "\n".join(lines)

    def _render_fields(self, fields: List[FieldSpec]) -> str:
        """속성(필드) 목록 렌더링"""
        lines = [
            "## 3. 속성(필드) 목록",
            "",
        ]

        if not fields:
            lines.append("_속성 없음_")
            return "\n".join(lines)

        lines.extend([
            "| No | 속성명 | 논리명 | 타입 | 접근제어자 | 어노테이션 | 초기값 | 설명 |",
            "|----|--------|--------|------|------------|------------|--------|------|",
        ])

        for idx, field in enumerate(fields, 1):
            modifiers = ', '.join(field.modifiers) if field.modifiers else '-'
            annotations = ', '.join(field.annotations) if field.annotations else '-'
            initial_value = field.initial_value or '-'
            description = field.description or '-'

            lines.append(
                f"| {idx} | {self._escape_markdown_table_cell(field.name)} | "
                f"{self._escape_markdown_table_cell(field.logical_name or '-')} | "
                f"{self._escape_markdown_table_cell(field.type)} | "
                f"{self._escape_markdown_table_cell(modifiers)} | "
                f"{self._escape_markdown_table_cell(annotations)} | "
                f"{self._escape_markdown_table_cell(initial_value)} | "
                f"{self._escape_markdown_table_cell(description)} |"
            )

        return "\n".join(lines)

    def _render_methods(self, spec_data: ClassSpecData) -> str:
        """메서드 목록 렌더링"""
        lines = [
            "## 4. 메서드 목록",
            "",
        ]

        # Public 메서드
        public_methods = spec_data.get_public_methods()
        if public_methods:
            lines.extend(self._render_method_group("4.1 Public 메서드", public_methods))

        # Protected 메서드
        protected_methods = spec_data.get_protected_methods()
        if protected_methods:
            lines.extend(["", ""])
            lines.extend(self._render_method_group("4.2 Protected 메서드", protected_methods))

        # Private 메서드
        private_methods = spec_data.get_private_methods()
        if private_methods:
            lines.extend(["", ""])
            lines.extend(self._render_method_group("4.3 Private 메서드", private_methods))

        # Package-private 메서드
        package_methods = spec_data.get_package_private_methods()
        if package_methods:
            lines.extend(["", ""])
            lines.extend(self._render_method_group("4.4 Package-Private 메서드", package_methods))

        if not spec_data.methods:
            lines.append("_메서드 없음_")

        return "\n".join(lines)

    def _render_method_group(self, title: str, methods: List[MethodSpec]) -> List[str]:
        """메서드 그룹 렌더링"""
        lines = [
            f"### {title}",
            "",
            "| No | 메서드명 | 논리명 | 반환타입 | 파라미터 | 어노테이션 | 설명 |",
            "|----|----------|--------|----------|----------|------------|------|",
        ]

        for idx, method in enumerate(methods, 1):
            params_str = ", ".join([f"{p.type} {p.name}" for p in method.parameters]) if method.parameters else "-"
            annotations = ", ".join(method.annotations) if method.annotations else "-"
            description = method.description or "-"

            lines.append(
                f"| {idx} | {self._escape_markdown_table_cell(method.name)} | "
                f"{self._escape_markdown_table_cell(method.logical_name or '-')} | "
                f"{self._escape_markdown_table_cell(method.return_type)} | "
                f"{self._escape_markdown_table_cell(params_str)} | "
                f"{self._escape_markdown_table_cell(annotations)} | "
                f"{self._escape_markdown_table_cell(description)} |"
            )

        # 상세 정보
        lines.append("")
        for method in methods:
            if method.parameters or method.endpoint or method.sql_statements:
                lines.extend(self._render_method_detail(method))
                lines.append("")

        return lines

    def _render_method_detail(self, method: MethodSpec) -> List[str]:
        """메서드 상세 정보 렌더링"""
        lines = [
            f"#### {method.name}",
            f"**개요**: {method.description or '_설명 없음_'}",
            "",
        ]

        # 파라미터
        if method.parameters:
            lines.extend([
                "**파라미터**:",
                "",
                "| No | 파라미터명 | 논리명 | 타입 | 필수여부 | 설명 |",
                "|----|------------|--------|------|----------|------|",
            ])
            for idx, param in enumerate(method.parameters, 1):
                required = "Y" if param.required else "N"
                lines.append(
                    f"| {idx} | {self._escape_markdown_table_cell(param.name)} | "
                    f"{self._escape_markdown_table_cell(param.logical_name or '-')} | "
                    f"{self._escape_markdown_table_cell(param.type)} | "
                    f"{required} | {self._escape_markdown_table_cell(param.description or '-')} |"
                )
            lines.append("")

        # 반환값
        lines.extend([
            "**반환값**:",
            f"- **타입**: {method.return_type}",
            "",
        ])

        # HTTP 매핑 (REST Endpoint인 경우)
        if method.endpoint:
            lines.extend([
                "**HTTP 매핑**:",
                f"- **Method**: {method.endpoint.http_method}",
                f"- **Path**: {method.endpoint.path}",
            ])
            if method.endpoint.request_body_type:
                lines.append(f"- **Request Body**: {method.endpoint.request_body_type}")
            if method.endpoint.response_type:
                lines.append(f"- **Response**: {method.endpoint.response_type}")
            lines.append("")

        # SQL 문
        if method.sql_statements:
            lines.extend([
                "**실행 SQL**:",
                "",
                "| No | SQL ID | SQL 유형 | 테이블 | 복잡도 |",
                "|----|--------|----------|--------|--------|",
            ])
            for idx, sql in enumerate(method.sql_statements, 1):
                tables_str = ", ".join(sql.tables) if sql.tables else "-"
                complexity = str(sql.complexity) if sql.complexity else "-"
                lines.append(
                    f"| {idx} | {sql.sql_id} | {sql.sql_type} | {tables_str} | {complexity} |"
                )
            lines.append("")

        return lines

    def _render_dependencies(self, dependencies: List[DependencySpec]) -> str:
        """의존성 정보 렌더링"""
        lines = [
            "## 5. 의존성 정보",
            "",
        ]

        if not dependencies:
            lines.append("_의존성 없음_")
            return "\n".join(lines)

        lines.extend([
            "### 5.1 주입받는 의존성 (Injected Dependencies)",
            "",
            "| No | Bean 이름 | 타입 | 주입 방식 | 설명 |",
            "|----|-----------|------|-----------|------|",
        ])

        for idx, dep in enumerate(dependencies, 1):
            injection_type = dep.injection_type.title() if dep.injection_type else "Unknown"
            lines.append(
                f"| {idx} | {dep.bean_name or '-'} | {dep.dependency_class} | "
                f"{injection_type} | {dep.description or '-'} |"
            )

        return "\n".join(lines)

    def _render_database_info(self, table_usage: List[TableUsageSpec]) -> str:
        """데이터베이스 연관 정보 렌더링"""
        lines = [
            "## 6. 데이터베이스 연관 정보",
            "",
        ]

        if not table_usage:
            lines.append("_데이터베이스 연관 정보 없음_")
            return "\n".join(lines)

        lines.extend([
            "### 6.1 사용 테이블",
            "",
            "| No | 테이블명 | 스키마 | CRUD 작업 | 설명 |",
            "|----|----------|--------|-----------|------|",
        ])

        for idx, table in enumerate(table_usage, 1):
            operations_str = "/".join(sorted(table.operations)) if table.operations else "-"
            lines.append(
                f"| {idx} | {table.table_name} | {table.db_schema} | "  # schema → db_schema
                f"{operations_str} | {table.description or '-'} |"
            )

        return "\n".join(lines)

    def _render_diagrams(self, spec_data: ClassSpecData) -> str:
        """관계도 렌더링"""
        lines = [
            "## 7. 관계도",
            "",
            "### 7.1 시퀀스 다이어그램 참조",
            "상세한 메서드 호출 흐름은 시퀀스 다이어그램 참조",
            "",
            f"**파일 위치**: `output/sequence-diagram/{spec_data.project_name}/{spec_data.package_name.replace('.', '/')}/`",
        ]
        return "\n".join(lines)
