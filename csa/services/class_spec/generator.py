"""
클래스 명세서 생성 오케스트레이터
"""
import os
from datetime import datetime
from typing import Dict, Optional

from neo4j import Driver

from csa.models.class_spec import (
    ClassSpecData,
    ClassSpecOptions,
    DependencySpec,
    EndpointSpec,
    FieldSpec,
    MethodSpec,
    ParameterSpec,
    SqlStatementSpec,
    TableUsageSpec,
)
from csa.services.class_spec.repository import ClassSpecRepository
from csa.services.class_spec.template import ClassSpecTemplate
from csa.utils.logger import get_logger

logger = get_logger(__name__)


class ClassSpecGenerator:
    """클래스 명세서 생성 오케스트레이터"""

    def __init__(self, driver: Driver, database: Optional[str] = None):
        """
        Initialize the class specification generator.

        Args:
            driver: Neo4j driver instance
            database: Target Neo4j database (optional)
        """
        self.repository = ClassSpecRepository(driver, database)
        self.template = ClassSpecTemplate()

    def generate_spec(self, options: ClassSpecOptions) -> Dict:
        """
        클래스 명세서 생성

        Args:
            options: 명세서 생성 옵션

        Returns:
            결과 딕셔너리 (success, file_path, message 등)
        """
        result = {
            "success": False,
            "message": "",
            "file_path": "",
            "stats": {},
        }

        try:
            logger.info(f"Generating class specification for: {options.class_name}")

            # 1. 클래스 정보 조회
            class_info = self.repository.get_class_info(options.project_name, options.class_name)
            if not class_info:
                result["message"] = f"Class not found: {options.class_name} in project {options.project_name}"
                logger.error(result["message"])
                return result

            logger.info(f"✓ Class information retrieved: {class_info['class_name']}")

            # 2-4. 필수 정보 조회 (메서드, 필드, 의존성)
            try:
                methods_data = self.repository.get_methods(options.project_name, options.class_name)
                logger.info(f"✓ Methods retrieved: {len(methods_data)}")

                fields_data = self.repository.get_fields(options.project_name, options.class_name)
                logger.info(f"✓ Fields retrieved: {len(fields_data)}")

                dependencies_data = self.repository.get_dependencies(options.project_name, options.class_name)
                logger.info(f"✓ Dependencies retrieved: {len(dependencies_data)}")
            except Exception as e:
                logger.error(f"Error retrieving class details: {e}", exc_info=True)
                raise  # 필수 정보이므로 실패 시 중단

            # 5. CRUD 정보 조회 (선택적, 실패해도 계속 진행)
            crud_data = []
            if options.include_crud_info:
                try:
                    crud_data = self.repository.get_crud_info(options.project_name, options.class_name)
                    logger.info(f"✓ CRUD information retrieved: {len(crud_data)} tables")
                except Exception as e:
                    logger.warning(f"Failed to retrieve CRUD info: {e}, continuing without it")
                    # 실패해도 계속 진행

            # 6-8. 템플릿 처리
            try:
                spec_data = self._build_spec_data(
                    class_info,
                    methods_data,
                    fields_data,
                    dependencies_data,
                    crud_data,
                    options.project_name,
                )
                spec_content = self.template.render(spec_data)
                file_path = self._save_spec(spec_content, spec_data, options.output_dir)
                logger.info(f"Specification saved to: {file_path}")
            except Exception as e:
                logger.error(f"Error generating specification document: {e}", exc_info=True)
                raise

            result["success"] = True
            result["message"] = "Class specification generated successfully"
            result["file_path"] = file_path
            result["stats"] = {
                "class_name": spec_data.class_name,
                "package_name": spec_data.package_name,
                "type": spec_data.type,
                "sub_type": spec_data.sub_type,
                "methods_count": len(spec_data.methods),
                "fields_count": len(spec_data.fields),
                "dependencies_count": len(spec_data.dependencies),
                "tables_count": len(spec_data.table_usage),
            }

        except Exception as e:
            logger.error(f"Error generating class specification: {e}", exc_info=True)
            result["message"] = f"Error: {str(e)}"

        return result

    def _build_spec_data(
        self,
        class_info: Dict,
        methods_data: list,
        fields_data: list,
        dependencies_data: list,
        crud_data: list,
        project_name: str,
    ) -> ClassSpecData:
        """
        데이터 모델 구성

        Args:
            class_info: 클래스 기본 정보
            methods_data: 메서드 정보 리스트
            fields_data: 필드 정보 리스트
            dependencies_data: 의존성 정보 리스트
            crud_data: CRUD 정보 리스트
            project_name: 프로젝트명

        Returns:
            ClassSpecData 인스턴스
        """
        # 필드 변환
        fields = [FieldSpec(**field) for field in fields_data]

        # 메서드 변환
        methods = []
        for method_data in methods_data:
            # Parameters 변환
            parameters = [ParameterSpec(**param) for param in method_data.get("parameters", [])]

            # SQL Statements 변환
            sql_statements = [SqlStatementSpec(**sql) for sql in method_data.get("sql_statements", []) if sql.get("sql_id")]

            # Endpoint 변환
            endpoint = None
            if method_data.get("endpoint"):
                endpoint = EndpointSpec(**method_data["endpoint"])

            methods.append(
                MethodSpec(
                    name=method_data["name"],
                    logical_name=method_data.get("logical_name", ""),
                    return_type=method_data.get("return_type", "void"),
                    parameters=parameters,
                    modifiers=method_data.get("modifiers", []),
                    annotations=method_data.get("annotations", []),
                    description=method_data.get("description", ""),
                    sql_statements=sql_statements,
                    endpoint=endpoint,
                )
            )

        # 의존성 변환
        dependencies = [DependencySpec(**dep) for dep in dependencies_data]

        # CRUD 정보 변환
        table_usage = [TableUsageSpec(**table) for table in crud_data]

        # ClassSpecData 생성
        return ClassSpecData(
            class_name=class_info["class_name"],
            logical_name=class_info.get("logical_name", ""),
            package_name=class_info.get("package_name", ""),
            type=class_info.get("type", "class"),
            sub_type=class_info.get("sub_type", ""),
            description=class_info.get("description", ""),
            project_name=project_name,
            superclass=class_info.get("superclass"),
            interfaces=class_info.get("interfaces", []),
            annotations=class_info.get("annotations", []),
            bean_name=class_info.get("bean_name", ""),
            bean_type=class_info.get("bean_type", ""),
            scope=class_info.get("scope", ""),
            base_path=class_info.get("base_path", ""),
            fields=fields,
            methods=methods,
            dependencies=dependencies,
            table_usage=table_usage,
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            file_path=class_info.get("file_path", ""),
        )

    def _save_spec(self, spec_content: str, spec_data: ClassSpecData, output_dir: str) -> str:
        """
        명세서를 파일로 저장

        Args:
            spec_content: 명세서 내용
            spec_data: 명세서 데이터
            output_dir: 출력 디렉터리

        Returns:
            저장된 파일 경로
        """
        # 패키지명을 디렉토리 경로로 변환
        package_path = spec_data.package_name.replace('.', os.sep) if spec_data.package_name else ""

        # 최종 출력 디렉터리: output_dir/project_name/package_path
        if package_path:
            final_output_dir = os.path.join(output_dir, spec_data.project_name, package_path)
        else:
            final_output_dir = os.path.join(output_dir, spec_data.project_name)

        # 디렉터리 생성
        os.makedirs(final_output_dir, exist_ok=True)

        # 파일명 생성: CLASS_SPEC_{class_name}_{timestamp}.md
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        # 클래스명에서 패키지 경로 제거 (단순 클래스명만 사용)
        simple_class_name = spec_data.class_name.split('.')[-1]
        filename = f"CLASS_SPEC_{simple_class_name}_{timestamp}.md"

        # 파일 경로
        file_path = os.path.join(final_output_dir, filename)

        # 파일 저장
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(spec_content)

        return file_path
