"""
클래스 명세서 데이터 조회를 위한 Neo4j Repository
"""
import json
from typing import Any, Dict, List, Optional
from neo4j import Driver

from csa.utils.logger import get_logger

logger = get_logger(__name__)


class ClassSpecRepository:
    """클래스 명세서 생성을 위한 Neo4j 데이터 조회 클래스"""

    def __init__(self, driver: Driver, database: Optional[str] = None):
        self.driver = driver
        self.database = database or "neo4j"

    def _parse_json_field(self, value: Any, default: Any = None, field_name: str = "") -> Any:
        """
        JSON 필드를 안전하게 파싱

        Args:
            value: 파싱할 값 (str, list, dict, None)
            default: 파싱 실패 시 기본값 (기본: [])
            field_name: 필드명 (로깅용)

        Returns:
            파싱된 값 또는 기본값
        """
        # None 또는 빈 값 처리
        if not value:
            return default if default is not None else []

        # 이미 리스트/딕셔너리면 그대로 반환
        if isinstance(value, (list, dict)):
            return value

        # 문자열인 경우 JSON 파싱
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                return parsed if parsed else (default if default is not None else [])
            except json.JSONDecodeError as e:
                logger.warning(
                    f"Failed to parse JSON field '{field_name}': {e}, "
                    f"value: {value[:100] if len(value) > 100 else value}"
                )
                return default if default is not None else []

        # 기타 타입은 그대로 반환
        return value

    def _normalize_annotations(self, annotations: Any) -> List[str]:
        """
        어노테이션을 문자열 리스트로 정규화

        Args:
            annotations: 어노테이션 데이터 (list, str, None)

        Returns:
            문자열 리스트
        """
        if not annotations:
            return []

        if not isinstance(annotations, list):
            return []

        result = []
        for item in annotations:
            if isinstance(item, dict):
                # dict 형태: {'name': 'PutMapping', 'parameters': {...}}
                # -> '@PutMapping' 형태로 변환
                name = item.get('name', '')
                if name:
                    result.append(f"@{name}")
            elif isinstance(item, str):
                # 이미 문자열이면 그대로 사용
                result.append(item)
            else:
                # 기타 타입은 문자열로 변환
                result.append(str(item))

        return result

    def get_class_info(self, project_name: str, class_name: str) -> Optional[Dict[str, Any]]:
        """
        클래스 기본 정보 조회

        Args:
            project_name: 프로젝트명
            class_name: 클래스명 (단순명 또는 FQCN)

        Returns:
            클래스 정보 딕셔너리 또는 None
        """
        query = """
        MATCH (c:Class)
        WHERE c.project_name = $project_name
          AND (c.name = $class_name OR c.name ENDS WITH '.' + $class_name)
        OPTIONAL MATCH (c)<-[:PROVIDES]-(b:Bean)
        OPTIONAL MATCH (c)<-[:EXPOSES]-(e:Endpoint)
        RETURN c.name as class_name,
               c.logical_name as logical_name,
               c.package_name as package_name,
               c.type as type,
               c.sub_type as sub_type,
               c.description as description,
               c.superclass as superclass,
               c.interfaces as interfaces,
               c.annotations as annotations,
               c.file_path as file_path,
               b.bean_name as bean_name,
               b.bean_type as bean_type,
               b.scope as scope,
               e.path as base_path
        LIMIT 1
        """

        with self.driver.session(database=self.database) as session:
            result = session.run(query, project_name=project_name, class_name=class_name)
            record = result.single()

            if not record:
                logger.warning(f"Class not found: {class_name} in project {project_name}")
                return None

            # Annotations 및 Interfaces 파싱 (헬퍼 사용)
            annotations_raw = self._parse_json_field(record["annotations"], [], "annotations")
            annotations = self._normalize_annotations(annotations_raw)
            interfaces = self._parse_json_field(record["interfaces"], [], "interfaces")

            return {
                "class_name": record["class_name"],
                "logical_name": record["logical_name"] or "",
                "package_name": record["package_name"] or "",
                "type": record["type"] or "class",
                "sub_type": record["sub_type"] or "",
                "description": record["description"] or "",
                "superclass": record["superclass"],
                "interfaces": interfaces,
                "annotations": annotations,
                "file_path": record["file_path"] or "",
                "bean_name": record["bean_name"] or "",
                "bean_type": record["bean_type"] or "",
                "scope": record["scope"] or "",
                "base_path": record["base_path"] or "",
            }

    def get_methods(self, project_name: str, class_name: str) -> List[Dict[str, Any]]:
        """
        메서드 목록 조회

        Args:
            project_name: 프로젝트명
            class_name: 클래스명

        Returns:
            메서드 정보 리스트
        """
        query = """
        MATCH (c:Class)
        WHERE c.project_name = $project_name
          AND (c.name = $class_name OR c.name ENDS WITH '.' + $class_name)
        MATCH (c)-[:HAS_METHOD]->(m:Method)
        OPTIONAL MATCH (m)-[:CALLS]->(sql:SqlStatement)
        OPTIONAL MATCH (m)<-[:EXPOSES]-(e:Endpoint)
        WITH m,
             collect(DISTINCT {
                 sql_id: sql.id,
                 sql_type: sql.sql_type,
                 tables: sql.tables,
                 complexity: sql.complexity_score
             }) as sql_statements,
             e
        RETURN m.name as method_name,
               m.logical_name as logical_name,
               m.return_type as return_type,
               m.parameters as parameters,
               m.modifiers as modifiers,
               m.annotations as annotations,
               m.description as description,
               sql_statements,
               e.path as endpoint_path,
               e.http_method as http_method,
               e.request_body as request_body_type,
               e.response_type as response_type
        ORDER BY
          CASE WHEN 'public' IN m.modifiers THEN 1
               WHEN 'protected' IN m.modifiers THEN 2
               WHEN 'private' IN m.modifiers THEN 3
               ELSE 4 END,
          m.name
        """

        with self.driver.session(database=self.database) as session:
            result = session.run(query, project_name=project_name, class_name=class_name)
            methods = []

            for record in result:
                # SQL statements 파싱
                sql_statements = []
                for sql_data in record["sql_statements"]:
                    if sql_data and sql_data.get("sql_id"):
                        tables = []
                        if sql_data.get("tables"):
                            try:
                                tables_json = json.loads(sql_data["tables"]) if isinstance(sql_data["tables"], str) else sql_data["tables"]
                                tables = [t["name"] if isinstance(t, dict) else t for t in tables_json]
                            except (json.JSONDecodeError, TypeError):
                                pass

                        sql_statements.append({
                            "sql_id": sql_data["sql_id"],
                            "sql_type": sql_data.get("sql_type", ""),
                            "tables": tables,
                            "complexity": sql_data.get("complexity"),
                        })

                # Parameters 파싱
                parameters = []
                params_data = record["parameters"] or []
                if isinstance(params_data, str):
                    try:
                        params_data = json.loads(params_data)
                    except json.JSONDecodeError:
                        params_data = []

                for param in params_data:
                    if isinstance(param, dict):
                        parameters.append({
                            "name": param.get("name", ""),
                            "logical_name": param.get("logical_name", ""),
                            "type": param.get("type", ""),
                            "required": True,
                            "description": param.get("description", ""),
                        })

                # Endpoint 정보
                endpoint = None
                if record["endpoint_path"]:
                    endpoint = {
                        "path": record["endpoint_path"],
                        "http_method": record["http_method"] or "",
                        "request_body_type": record["request_body_type"] or "",
                        "response_type": record["response_type"] or "",
                    }

                # Annotations 및 Modifiers 파싱 (헬퍼 사용)
                annotations_raw = self._parse_json_field(record["annotations"], [], "method.annotations")
                annotations = self._normalize_annotations(annotations_raw)
                modifiers = self._parse_json_field(record["modifiers"], [], "method.modifiers")

                methods.append({
                    "name": record["method_name"],
                    "logical_name": record["logical_name"] or "",
                    "return_type": record["return_type"] or "void",
                    "parameters": parameters,
                    "modifiers": modifiers,
                    "annotations": annotations,
                    "description": record["description"] or "",
                    "sql_statements": sql_statements,
                    "endpoint": endpoint,
                })

            return methods

    def get_fields(self, project_name: str, class_name: str) -> List[Dict[str, Any]]:
        """
        필드 목록 조회

        Args:
            project_name: 프로젝트명
            class_name: 클래스명

        Returns:
            필드 정보 리스트
        """
        query = """
        MATCH (c:Class)
        WHERE c.project_name = $project_name
          AND (c.name = $class_name OR c.name ENDS WITH '.' + $class_name)
        MATCH (c)-[:HAS_FIELD]->(f:Field)
        RETURN f.name as field_name,
               f.logical_name as logical_name,
               f.type as type,
               f.modifiers as modifiers,
               f.annotations as annotations,
               f.initial_value as initial_value,
               f.description as description
        ORDER BY f.name
        """

        with self.driver.session(database=self.database) as session:
            result = session.run(query, project_name=project_name, class_name=class_name)
            fields = []

            for record in result:
                # Annotations 및 Modifiers 파싱 (헬퍼 사용)
                annotations_raw = self._parse_json_field(record["annotations"], [], "field.annotations")
                annotations = self._normalize_annotations(annotations_raw)
                modifiers = self._parse_json_field(record["modifiers"], [], "field.modifiers")

                fields.append({
                    "name": record["field_name"],
                    "logical_name": record["logical_name"] or "",
                    "type": record["type"] or "",
                    "modifiers": modifiers,
                    "annotations": annotations,
                    "initial_value": record["initial_value"] or "",
                    "description": record["description"] or "",
                })

            return fields

    def get_dependencies(self, project_name: str, class_name: str) -> List[Dict[str, Any]]:
        """
        의존성 정보 조회

        Args:
            project_name: 프로젝트명
            class_name: 클래스명

        Returns:
            의존성 정보 리스트
        """
        query = """
        MATCH (c:Class)
        WHERE c.project_name = $project_name
          AND (c.name = $class_name OR c.name ENDS WITH '.' + $class_name)
        MATCH (c)-[r:INJECTS]->(dep:Class)
        OPTIONAL MATCH (dep)<-[:PROVIDES]-(b:Bean)
        RETURN dep.name as dependency_class,
               b.bean_name as bean_name,
               b.bean_type as bean_type,
               r.injection_type as injection_type,
               r.field_name as field_name,
               dep.description as description
        ORDER BY dep.name
        """

        with self.driver.session(database=self.database) as session:
            result = session.run(query, project_name=project_name, class_name=class_name)
            dependencies = []

            for record in result:
                dependencies.append({
                    "bean_name": record["bean_name"] or "",
                    "dependency_class": record["dependency_class"],
                    "bean_type": record["bean_type"] or "",
                    "injection_type": record["injection_type"] or "",
                    "field_name": record["field_name"] or "",
                    "description": record["description"] or "",
                })

            return dependencies

    def get_crud_info(self, project_name: str, class_name: str) -> List[Dict[str, Any]]:
        """
        CRUD 정보 조회

        Args:
            project_name: 프로젝트명
            class_name: 클래스명

        Returns:
            테이블 사용 정보 리스트
        """
        query = """
        MATCH (c:Class)
        WHERE c.project_name = $project_name
          AND (c.name = $class_name OR c.name ENDS WITH '.' + $class_name)
        MATCH (c)-[:HAS_METHOD]->(m:Method)
        MATCH (m)-[:CALLS]->(sql:SqlStatement)
        WHERE sql.tables IS NOT NULL AND sql.tables <> '[]'
        WITH sql,
             CASE
               WHEN sql.sql_type = 'SELECT' THEN 'R'
               WHEN sql.sql_type = 'INSERT' THEN 'C'
               WHEN sql.sql_type = 'UPDATE' THEN 'U'
               WHEN sql.sql_type = 'DELETE' THEN 'D'
               ELSE 'O'
             END as operation
        RETURN DISTINCT
               sql.tables as tables_json,
               operation
        """

        with self.driver.session(database=self.database) as session:
            result = session.run(query, project_name=project_name, class_name=class_name)

            # 테이블별로 집계
            table_operations: Dict[str, set] = {}

            for record in result:
                try:
                    tables_json = record["tables_json"]
                    operation = record["operation"]

                    if tables_json and tables_json != "[]":
                        tables = json.loads(tables_json) if isinstance(tables_json, str) else tables_json
                        for table_info in tables:
                            if isinstance(table_info, dict) and "name" in table_info:
                                table_name = table_info["name"]
                                schema = table_info.get("schema", "public")

                                key = f"{schema}.{table_name}"
                                if key not in table_operations:
                                    table_operations[key] = {
                                        "table_name": table_name,
                                        "db_schema": schema,  # schema → db_schema
                                        "operations": set()
                                    }
                                table_operations[key]["operations"].add(operation)
                except (json.JSONDecodeError, TypeError, KeyError) as e:
                    logger.warning(f"Failed to parse tables_json: {e}")
                    continue

            # set을 list로 변환
            crud_info = []
            for data in table_operations.values():
                crud_info.append({
                    "table_name": data["table_name"],
                    "db_schema": data["db_schema"],  # schema → db_schema
                    "operations": sorted(list(data["operations"])),
                    "description": "",
                })

            return sorted(crud_info, key=lambda x: x["table_name"])
