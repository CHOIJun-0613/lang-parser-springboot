from __future__ import annotations

import json

from csa.models.graph_entities import JpaEntity, JpaQuery, JpaRepository, MyBatisMapper, SqlStatement
from csa.services.graph_db.base import GraphDBBase


class PersistenceMixin:
    """Manage persistence layer nodes such as MyBatis and JPA artifacts."""

    def add_mybatis_mapper(self, mapper: MyBatisMapper, project_name: str) -> None:
        """Add or update a MyBatis mapper node."""
        self._execute_write(self._create_mybatis_mapper_node_tx, mapper, project_name)

    def add_jpa_entity(self, entity: JpaEntity, project_name: str) -> None:
        """Add or update a JPA entity node."""
        self._execute_write(self._create_jpa_entity_node_tx, entity, project_name)

    def add_jpa_repository(self, repository: JpaRepository, project_name: str) -> None:
        """Add or update a JPA repository node."""
        self._execute_write(self._create_jpa_repository_node_tx, repository, project_name)

    def add_jpa_query(self, query: JpaQuery, project_name: str) -> None:
        """Add or update a JPA query node."""
        self._execute_write(self._create_jpa_query_node_tx, query, project_name)

    def add_sql_statement(self, sql_statement: SqlStatement, project_name: str) -> None:
        """Add or update a SQL statement node."""
        self._execute_write(self._create_sql_statement_node_tx, sql_statement, project_name)

    @staticmethod
    def _create_mybatis_mapper_node_tx(tx, mapper: MyBatisMapper, project_name: str) -> None:
        current_timestamp = GraphDBBase._get_current_timestamp()
        mapper_query = (
            "MERGE (m:MyBatisMapper {name: $name, project_name: $project_name}) "
            "SET m.logical_name = $logical_name, m.type = $type, m.namespace = $namespace, m.methods = $methods, "
            "m.sql_statements = $sql_statements, m.file_path = $file_path, "
            "m.package_name = $package_name, m.description = $description, m.ai_description = $ai_description, "
            "m.updated_at = $updated_at"
        )
        tx.run(
            mapper_query,
            name=mapper.name,
            logical_name=mapper.logical_name or "",
            project_name=project_name,
            type=mapper.type,
            namespace=mapper.namespace,
            methods=json.dumps(mapper.methods),
            sql_statements=json.dumps(mapper.sql_statements),
            file_path=mapper.file_path,
            package_name=mapper.package_name,
            description=mapper.description or "",
            ai_description=mapper.ai_description or "",
            updated_at=current_timestamp,
        )

    @staticmethod
    def _create_jpa_entity_node_tx(tx, entity: JpaEntity, project_name: str) -> None:
        current_timestamp = GraphDBBase._get_current_timestamp()
        entity_query = (
            "MERGE (e:JpaEntity {name: $name}) "
            "SET e.table_name = $table_name, e.columns = $columns, "
            "e.relationships = $relationships, e.annotations = $annotations, "
            "e.package_name = $package_name, e.file_path = $file_path, "
            "e.project_name = $project_name, e.description = $description, e.ai_description = $ai_description, "
            "e.updated_at = $updated_at"
        )
        tx.run(
            entity_query,
            name=entity.name,
            table_name=entity.table_name,
            columns=json.dumps(entity.columns),
            relationships=json.dumps(entity.relationships),
            annotations=json.dumps(entity.annotations),
            package_name=entity.package_name,
            file_path=entity.file_path,
            project_name=project_name,
            description=entity.description or "",
            ai_description=entity.ai_description or "",
            updated_at=current_timestamp,
        )

    @staticmethod
    def _create_jpa_repository_node_tx(tx, repository: JpaRepository, project_name: str) -> None:
        current_timestamp = GraphDBBase._get_current_timestamp()
        repository_query = (
            "MERGE (r:JpaRepository {name: $name}) "
            "SET r.entity_type = $entity_type, r.methods = $methods, "
            "r.annotations = $annotations, r.package_name = $package_name, "
            "r.file_path = $file_path, r.project_name = $project_name, "
            "r.description = $description, r.ai_description = $ai_description, "
            "r.updated_at = $updated_at"
        )
        tx.run(
            repository_query,
            name=repository.name,
            entity_type=repository.entity_type,
            methods=json.dumps(repository.methods),
            annotations=json.dumps(repository.annotations),
            package_name=repository.package_name,
            file_path=repository.file_path,
            project_name=project_name,
            description=repository.description or "",
            ai_description=repository.ai_description or "",
            updated_at=current_timestamp,
        )

    @staticmethod
    def _create_jpa_query_node_tx(tx, query: JpaQuery, project_name: str) -> None:
        current_timestamp = GraphDBBase._get_current_timestamp()
        query_query = (
            "MERGE (q:JpaQuery {name: $name, project_name: $project_name}) "
            "SET q.query_type = $query_type, q.query_content = $query_content, "
            "q.return_type = $return_type, q.parameters = $parameters, "
            "q.repository_name = $repository_name, q.method_name = $method_name, "
            "q.annotations = $annotations, q.description = $description, "
            "q.ai_description = $ai_description, q.updated_at = $updated_at"
        )
        parameters_dict = {
            "name": str(query.name) if query.name else "",
            "project_name": str(project_name) if project_name else "",
            "query_type": str(query.query_type) if query.query_type else "",
            "query_content": str(query.query_content) if query.query_content else "",
            "return_type": str(query.return_type) if query.return_type else "",
            "parameters": json.dumps(query.parameters if isinstance(query.parameters, list) else []),
            "repository_name": str(query.repository_name) if query.repository_name else "",
            "method_name": str(query.method_name) if query.method_name else "",
            "annotations": json.dumps(query.annotations if isinstance(query.annotations, list) else []),
            "description": str(query.description) if query.description else "",
            "ai_description": str(query.ai_description) if query.ai_description else "",
            "updated_at": current_timestamp,
        }
        tx.run(query_query, parameters_dict)

    @staticmethod
    def _create_sql_statement_node_tx(tx, sql_statement: SqlStatement, project_name: str) -> None:
        current_timestamp = GraphDBBase._get_current_timestamp()
        sql_query = (
            "MERGE (s:SqlStatement {id: $id, mapper_name: $mapper_name}) "
            "SET s.logical_name = $logical_name, s.sql_type = $sql_type, s.sql_content = $sql_content, "
            "s.parameter_type = $parameter_type, s.result_type = $result_type, "
            "s.result_map = $result_map, s.annotations = $annotations, "
            "s.project_name = $project_name, s.description = $description, s.ai_description = $ai_description, "
            "s.complexity_score = $complexity_score, s.tables = $tables, s.columns = $columns, "
            "s.sql_analysis = $sql_analysis, s.updated_at = $updated_at"
        )
        tx.run(
            sql_query,
            id=sql_statement.id,
            logical_name=sql_statement.logical_name or "",
            mapper_name=sql_statement.mapper_name,
            sql_type=sql_statement.sql_type,
            sql_content=sql_statement.sql_content,
            parameter_type=sql_statement.parameter_type,
            result_type=sql_statement.result_type,
            result_map=sql_statement.result_map,
            annotations=json.dumps([{"name": a.name, "parameters": a.parameters} for a in sql_statement.annotations]),
            project_name=project_name,
            description=sql_statement.description or "",
            ai_description=sql_statement.ai_description or "",
            complexity_score=sql_statement.complexity_score,
            tables=json.dumps(sql_statement.tables),
            columns=json.dumps(sql_statement.columns),
            sql_analysis=json.dumps(sql_statement.sql_analysis),
            updated_at=current_timestamp,
        )

    @staticmethod
    def _create_mapper_sql_relationship_tx(tx, mapper_name: str, sql_id: str, project_name: str) -> None:
        relationship_query = (
            "MATCH (m:MyBatisMapper {name: $mapper_name, project_name: $project_name}) "
            "MATCH (s:SqlStatement {id: $sql_id, mapper_name: $mapper_name, project_name: $project_name}) "
            "MERGE (m)-[:HAS_SQL_STATEMENT]->(s)"
        )
        tx.run(
            relationship_query,
            mapper_name=mapper_name,
            sql_id=sql_id,
            project_name=project_name,
        )

    def create_method_sql_relationships(self, project_name: str) -> None:
        """Create CALLS relationships between repository methods and SQL statements."""
        self._execute_write(self._create_method_sql_relationships_tx, project_name)

    @staticmethod
    def _create_method_sql_relationships_tx(tx, project_name: str) -> int:
        relationship_query = """
        MATCH (c:Class {project_name: $project_name})
        WHERE c.name ENDS WITH 'Repository' OR c.name ENDS WITH 'Mapper'
        MATCH (c)-[:HAS_METHOD]->(m:Method)
        MATCH (s:SqlStatement {project_name: $project_name})
        WHERE s.mapper_name = c.name 
          AND s.id = m.name
        MERGE (m)-[:CALLS]->(s)
        RETURN count(*) as relationships_created
        """
        result = tx.run(relationship_query, project_name=project_name)
        return result.single()["relationships_created"]
