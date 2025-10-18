from __future__ import annotations

import json
from typing import List

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

    def add_mybatis_mappers_batch(self, mappers: List[MyBatisMapper], project_name: str) -> None:
        """Add or update multiple MyBatis mapper nodes in a single transaction."""
        if not mappers:
            return
        self._execute_write(self._create_mybatis_mappers_batch_tx, mappers, project_name)

    def add_jpa_entities_batch(self, entities: List[JpaEntity], project_name: str) -> None:
        """Add or update multiple JPA entity nodes in a single transaction."""
        if not entities:
            return
        self._execute_write(self._create_jpa_entities_batch_tx, entities, project_name)

    def add_jpa_repositories_batch(self, repositories: List[JpaRepository], project_name: str) -> None:
        """Add or update multiple JPA repository nodes in a single transaction."""
        if not repositories:
            return
        self._execute_write(self._create_jpa_repositories_batch_tx, repositories, project_name)

    def add_jpa_queries_batch(self, queries: List[JpaQuery], project_name: str) -> None:
        """Add or update multiple JPA query nodes in a single transaction."""
        if not queries:
            return
        self._execute_write(self._create_jpa_queries_batch_tx, queries, project_name)

    def add_sql_statements_batch(self, sql_statements: List[SqlStatement], project_name: str) -> None:
        """Add or update multiple SQL statement nodes in a single transaction."""
        if not sql_statements:
            return
        self._execute_write(self._create_sql_statements_batch_tx, sql_statements, project_name)

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

    @staticmethod
    def _create_mybatis_mappers_batch_tx(tx, mappers: List[MyBatisMapper], project_name: str) -> None:
        """배치로 여러 MyBatis Mapper를 한 번의 트랜잭션에 저장"""
        current_timestamp = GraphDBBase._get_current_timestamp()
        mapper_query = (
            "UNWIND $mappers AS m "
            "MERGE (mapper:MyBatisMapper {name: m.name, project_name: m.project_name}) "
            "SET mapper.logical_name = m.logical_name, "
            "mapper.type = m.type, "
            "mapper.namespace = m.namespace, "
            "mapper.methods = m.methods, "
            "mapper.sql_statements = m.sql_statements, "
            "mapper.file_path = m.file_path, "
            "mapper.package_name = m.package_name, "
            "mapper.description = m.description, "
            "mapper.ai_description = m.ai_description, "
            "mapper.updated_at = m.updated_at"
        )
        mappers_data = [
            {
                'name': mapper.name,
                'logical_name': mapper.logical_name or "",
                'project_name': project_name,
                'type': mapper.type,
                'namespace': mapper.namespace,
                'methods': json.dumps(mapper.methods),
                'sql_statements': json.dumps(mapper.sql_statements),
                'file_path': mapper.file_path,
                'package_name': mapper.package_name,
                'description': mapper.description or "",
                'ai_description': mapper.ai_description or "",
                'updated_at': current_timestamp,
            }
            for mapper in mappers
        ]
        tx.run(mapper_query, mappers=mappers_data)

    @staticmethod
    def _create_jpa_entities_batch_tx(tx, entities: List[JpaEntity], project_name: str) -> None:
        """배치로 여러 JPA Entity를 한 번의 트랜잭션에 저장"""
        current_timestamp = GraphDBBase._get_current_timestamp()
        entity_query = (
            "UNWIND $entities AS e "
            "MERGE (entity:JpaEntity {name: e.name}) "
            "SET entity.table_name = e.table_name, "
            "entity.columns = e.columns, "
            "entity.relationships = e.relationships, "
            "entity.annotations = e.annotations, "
            "entity.package_name = e.package_name, "
            "entity.file_path = e.file_path, "
            "entity.project_name = e.project_name, "
            "entity.description = e.description, "
            "entity.ai_description = e.ai_description, "
            "entity.updated_at = e.updated_at"
        )
        entities_data = [
            {
                'name': entity.name,
                'table_name': entity.table_name,
                'columns': json.dumps(entity.columns),
                'relationships': json.dumps(entity.relationships),
                'annotations': json.dumps(entity.annotations),
                'package_name': entity.package_name,
                'file_path': entity.file_path,
                'project_name': project_name,
                'description': entity.description or "",
                'ai_description': entity.ai_description or "",
                'updated_at': current_timestamp,
            }
            for entity in entities
        ]
        tx.run(entity_query, entities=entities_data)

    @staticmethod
    def _create_jpa_repositories_batch_tx(tx, repositories: List[JpaRepository], project_name: str) -> None:
        """배치로 여러 JPA Repository를 한 번의 트랜잭션에 저장"""
        current_timestamp = GraphDBBase._get_current_timestamp()
        repository_query = (
            "UNWIND $repositories AS r "
            "MERGE (repo:JpaRepository {name: r.name}) "
            "SET repo.entity_type = r.entity_type, "
            "repo.methods = r.methods, "
            "repo.annotations = r.annotations, "
            "repo.package_name = r.package_name, "
            "repo.file_path = r.file_path, "
            "repo.project_name = r.project_name, "
            "repo.description = r.description, "
            "repo.ai_description = r.ai_description, "
            "repo.updated_at = r.updated_at"
        )
        repositories_data = [
            {
                'name': repo.name,
                'entity_type': repo.entity_type,
                'methods': json.dumps(repo.methods),
                'annotations': json.dumps(repo.annotations),
                'package_name': repo.package_name,
                'file_path': repo.file_path,
                'project_name': project_name,
                'description': repo.description or "",
                'ai_description': repo.ai_description or "",
                'updated_at': current_timestamp,
            }
            for repo in repositories
        ]
        tx.run(repository_query, repositories=repositories_data)

    @staticmethod
    def _create_jpa_queries_batch_tx(tx, queries: List[JpaQuery], project_name: str) -> None:
        """배치로 여러 JPA Query를 한 번의 트랜잭션에 저장"""
        current_timestamp = GraphDBBase._get_current_timestamp()
        query_query = (
            "UNWIND $queries AS q "
            "MERGE (query:JpaQuery {name: q.name, project_name: q.project_name}) "
            "SET query.query_type = q.query_type, "
            "query.query_content = q.query_content, "
            "query.return_type = q.return_type, "
            "query.parameters = q.parameters, "
            "query.repository_name = q.repository_name, "
            "query.method_name = q.method_name, "
            "query.annotations = q.annotations, "
            "query.description = q.description, "
            "query.ai_description = q.ai_description, "
            "query.updated_at = q.updated_at"
        )
        queries_data = [
            {
                'name': str(q.name) if q.name else "",
                'project_name': str(project_name) if project_name else "",
                'query_type': str(q.query_type) if q.query_type else "",
                'query_content': str(q.query_content) if q.query_content else "",
                'return_type': str(q.return_type) if q.return_type else "",
                'parameters': json.dumps(q.parameters if isinstance(q.parameters, list) else []),
                'repository_name': str(q.repository_name) if q.repository_name else "",
                'method_name': str(q.method_name) if q.method_name else "",
                'annotations': json.dumps(q.annotations if isinstance(q.annotations, list) else []),
                'description': str(q.description) if q.description else "",
                'ai_description': str(q.ai_description) if q.ai_description else "",
                'updated_at': current_timestamp,
            }
            for q in queries
        ]
        tx.run(query_query, queries=queries_data)

    @staticmethod
    def _create_sql_statements_batch_tx(tx, sql_statements: List[SqlStatement], project_name: str) -> None:
        """배치로 여러 SQL Statement를 한 번의 트랜잭션에 저장"""
        current_timestamp = GraphDBBase._get_current_timestamp()
        sql_query = (
            "UNWIND $statements AS s "
            "MERGE (stmt:SqlStatement {id: s.id, mapper_name: s.mapper_name}) "
            "SET stmt.logical_name = s.logical_name, "
            "stmt.sql_type = s.sql_type, "
            "stmt.sql_content = s.sql_content, "
            "stmt.parameter_type = s.parameter_type, "
            "stmt.result_type = s.result_type, "
            "stmt.result_map = s.result_map, "
            "stmt.annotations = s.annotations, "
            "stmt.project_name = s.project_name, "
            "stmt.description = s.description, "
            "stmt.ai_description = s.ai_description, "
            "stmt.complexity_score = s.complexity_score, "
            "stmt.tables = s.tables, "
            "stmt.columns = s.columns, "
            "stmt.sql_analysis = s.sql_analysis, "
            "stmt.updated_at = s.updated_at"
        )
        statements_data = [
            {
                'id': stmt.id,
                'logical_name': stmt.logical_name or "",
                'mapper_name': stmt.mapper_name,
                'sql_type': stmt.sql_type,
                'sql_content': stmt.sql_content,
                'parameter_type': stmt.parameter_type,
                'result_type': stmt.result_type,
                'result_map': stmt.result_map,
                'annotations': json.dumps([{"name": a.name, "parameters": a.parameters} for a in stmt.annotations]),
                'project_name': project_name,
                'description': stmt.description or "",
                'ai_description': stmt.ai_description or "",
                'complexity_score': stmt.complexity_score,
                'tables': json.dumps(stmt.tables),
                'columns': json.dumps(stmt.columns),
                'sql_analysis': json.dumps(stmt.sql_analysis),
                'updated_at': current_timestamp,
            }
            for stmt in sql_statements
        ]
        tx.run(sql_query, statements=statements_data)
