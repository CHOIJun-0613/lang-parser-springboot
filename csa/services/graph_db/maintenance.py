from __future__ import annotations

from csa.services.graph_db.indexes import IndexManager


class MaintenanceMixin:
    """Provide cleanup helpers for the graph database."""

    def ensure_indexes(self) -> None:
        """
        필수 인덱스가 존재하는지 확인하고, 없으면 생성합니다.

        성능 최적화를 위해 analyze 명령 실행 시 자동으로 호출됩니다.
        """
        index_manager = IndexManager(self)
        index_manager.create_all_indexes()

    def list_indexes(self) -> list[dict]:
        """
        현재 데이터베이스의 모든 인덱스 조회

        Returns:
            인덱스 정보 리스트
        """
        index_manager = IndexManager(self)
        return index_manager.list_indexes()

    def drop_all_indexes(self) -> None:
        """
        모든 인덱스 및 제약조건 삭제

        WARNING: 개발/테스트 환경에서만 사용하세요!
        """
        index_manager = IndexManager(self)
        index_manager.drop_all_indexes()

    def delete_class_and_related_data(self, class_name: str, project_name: str) -> None:
        """Delete a class node and every associated artifact."""
        self._execute_write(self._delete_class_and_related_data_tx, class_name, project_name)

    @staticmethod
    def _delete_class_and_related_data_tx(tx, class_name: str, project_name: str) -> None:
        delete_methods_query = """
        MATCH (m:Method {class_name: $class_name})
        DETACH DELETE m
        """
        tx.run(delete_methods_query, class_name=class_name)

        delete_fields_query = """
        MATCH (f:Field {class_name: $class_name, project_name: $project_name})
        DETACH DELETE f
        """
        tx.run(delete_fields_query, class_name=class_name, project_name=project_name)

        delete_beans_query = """
        MATCH (b:Bean {class_name: $class_name, project_name: $project_name})
        DETACH DELETE b
        """
        tx.run(delete_beans_query, class_name=class_name, project_name=project_name)

        delete_endpoints_query = """
        MATCH (e:Endpoint {controller_class: $class_name, project_name: $project_name})
        DETACH DELETE e
        """
        tx.run(delete_endpoints_query, class_name=class_name, project_name=project_name)

        delete_mappers_query = """
        MATCH (m:MyBatisMapper {name: $class_name, project_name: $project_name})
        DETACH DELETE m
        """
        tx.run(delete_mappers_query, class_name=class_name, project_name=project_name)

        delete_sql_statements_query = """
        MATCH (s:SqlStatement {mapper_name: $class_name, project_name: $project_name})
        DETACH DELETE s
        """
        tx.run(delete_sql_statements_query, class_name=class_name, project_name=project_name)

        delete_jpa_entities_query = """
        MATCH (e:JpaEntity {name: $class_name, project_name: $project_name})
        DETACH DELETE e
        """
        tx.run(delete_jpa_entities_query, class_name=class_name, project_name=project_name)

        delete_jpa_repositories_query = """
        MATCH (r:JpaRepository {name: $class_name, project_name: $project_name})
        DETACH DELETE r
        """
        tx.run(delete_jpa_repositories_query, class_name=class_name, project_name=project_name)

        delete_config_files_query = """
        MATCH (cfg:ConfigFile {project_name: $project_name})
        WHERE cfg.file_path CONTAINS $class_name
        DETACH DELETE cfg
        """
        tx.run(delete_config_files_query, class_name=class_name, project_name=project_name)

        delete_test_classes_query = """
        MATCH (tc:TestClass {project_name: $project_name})
        WHERE tc.name CONTAINS $class_name
        DETACH DELETE tc
        """
        tx.run(delete_test_classes_query, class_name=class_name, project_name=project_name)

        delete_class_query = """
        MATCH (c:Class {name: $class_name, project_name: $project_name})
        DETACH DELETE c
        """
        tx.run(delete_class_query, class_name=class_name, project_name=project_name)

    def clean_java_objects(self) -> None:
        """Remove Java-related nodes from the graph."""
        with self._driver.session(database=self._database) as session:
            session.run("MATCH (n:Package) DETACH DELETE n")
            session.run("MATCH (n:Class) DETACH DELETE n")
            session.run("MATCH (n:Method) DETACH DELETE n")
            session.run("MATCH (n:Field) DETACH DELETE n")
            session.run("MATCH (n:Bean) DETACH DELETE n")
            session.run("MATCH (n:Endpoint) DETACH DELETE n")
            session.run("MATCH (n:MyBatisMapper) DETACH DELETE n")
            session.run("MATCH (n:SqlStatement) DETACH DELETE n")
            session.run("MATCH (n:JpaEntity) DETACH DELETE n")
            session.run("MATCH (n:JpaRepository) DETACH DELETE n")
            session.run("MATCH (n:JpaQuery) DETACH DELETE n")
            session.run("MATCH (n:ConfigFile) DETACH DELETE n")
            session.run("MATCH (n:TestClass) DETACH DELETE n")

    def clean_db_objects(self) -> None:
        """Remove database metadata nodes from the graph."""
        with self._driver.session(database=self._database) as session:
            session.run("MATCH (n:Database) DETACH DELETE n")
            session.run("MATCH (n:Table) DETACH DELETE n")
            session.run("MATCH (n:Column) DETACH DELETE n")
            session.run("MATCH (n:Index) DETACH DELETE n")
            session.run("MATCH (n:Constraint) DETACH DELETE n")

    def clean_database(self) -> None:
        """Delete every node and relationship from the database."""
        with self._driver.session(database=self._database) as session:
            session.run("MATCH (n) DETACH DELETE n")
