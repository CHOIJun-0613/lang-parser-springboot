from __future__ import annotations

import json

from csa.models.graph_entities import Column, Constraint, Database, Index, Table
from csa.services.graph_db.base import GraphDBBase


class DatabaseMixin:
    """Manage database, table, column, index, and constraint nodes."""

    def add_database(self, database: Database, project_name: str) -> None:
        """Add or update a database node."""
        self._execute_write(self._create_database_node_tx, database, project_name)

    def add_table(self, table: Table, database_name: str, project_name: str) -> None:
        """Add or update a table node."""
        self._execute_write(self._create_table_node_tx, table, database_name, project_name)

    def add_column(self, column: Column, table_name: str, project_name: str) -> None:
        """Add or update a column node."""
        self._execute_write(self._create_column_node_tx, column, table_name, project_name)

    def add_index(self, index: Index, table_name: str, project_name: str) -> None:
        """Add or update an index node."""
        self._execute_write(self._create_index_node_tx, index, table_name, project_name)

    def add_constraint(self, constraint: Constraint, table_name: str, project_name: str) -> None:
        """Add or update a constraint node."""
        self._execute_write(self._create_constraint_node_tx, constraint, table_name, project_name)

    @staticmethod
    def _create_database_node_tx(tx, database: Database, project_name: str) -> None:
        current_timestamp = GraphDBBase._get_current_timestamp()
        database_query = (
            "MERGE (d:Database {name: $name}) "
            "SET d.version = $version, d.environment = $environment, "
            "d.project_name = $project_name, d.description = $description, "
            "d.ai_description = $ai_description, d.updated_at = $updated_at"
        )
        tx.run(
            database_query,
            name=database.name,
            version=database.version,
            environment=database.environment,
            project_name=project_name,
            description=database.description or "",
            ai_description=database.ai_description or "",
            updated_at=current_timestamp,
        )

    @staticmethod
    def _create_table_node_tx(tx, table: Table, database_name: str, project_name: str) -> None:
        current_timestamp = GraphDBBase._get_current_timestamp()
        table_query = (
            "MERGE (t:Table {name: $name}) "
            "SET t.schema = $schema_name, t.database_name = $database_name, "
            "t.project_name = $project_name, t.comment = $comment, "
            "t.ai_description = $ai_description, t.updated_at = $updated_at"
        )
        tx.run(
            table_query,
            name=table.name,
            schema_name=table.schema_name,
            database_name=database_name,
            project_name=project_name,
            comment=table.comment or "",
            ai_description=table.ai_description or "",
            updated_at=current_timestamp,
        )
        db_table_query = (
            "MATCH (d:Database {name: $database_name}) "
            "MATCH (t:Table {name: $table_name}) "
            "MERGE (d)-[:CONTAINS]->(t)"
        )
        tx.run(
            db_table_query,
            database_name=database_name,
            table_name=table.name,
        )

    @staticmethod
    def _create_column_node_tx(tx, column: Column, table_name: str, project_name: str) -> None:
        current_timestamp = GraphDBBase._get_current_timestamp()
        column_query = (
            "MERGE (c:Column {name: $name, table_name: $table_name}) "
            "SET c.data_type = $data_type, c.nullable = $nullable, "
            "c.unique = $unique, c.primary_key = $primary_key, "
            "c.default_value = $default_value, c.constraints = $constraints, "
            "c.project_name = $project_name, c.comment = $comment, "
            "c.ai_description = $ai_description, c.updated_at = $updated_at"
        )
        tx.run(
            column_query,
            name=column.name,
            table_name=table_name,
            data_type=column.data_type,
            nullable=column.nullable,
            unique=column.unique,
            primary_key=column.primary_key,
            default_value=column.default_value or "",
            constraints=json.dumps(column.constraints),
            project_name=project_name,
            comment=column.comment or "",
            ai_description=column.ai_description or "",
            updated_at=current_timestamp,
        )
        table_column_query = (
            "MATCH (t:Table {name: $table_name}) "
            "MATCH (c:Column {name: $column_name, table_name: $table_name}) "
            "MERGE (t)-[:HAS_COLUMN]->(c)"
        )
        tx.run(
            table_column_query,
            table_name=table_name,
            column_name=column.name,
        )

    @staticmethod
    def _create_index_node_tx(tx, index: Index, table_name: str, project_name: str) -> None:
        current_timestamp = GraphDBBase._get_current_timestamp()
        index_query = (
            "MERGE (i:Index {name: $name, table_name: $table_name}) "
            "SET i.type = $type, i.columns = $columns, "
            "i.project_name = $project_name, i.description = $description, "
            "i.ai_description = $ai_description, i.updated_at = $updated_at"
        )
        tx.run(
            index_query,
            name=index.name,
            table_name=table_name,
            type=index.type,
            columns=json.dumps(index.columns),
            project_name=project_name,
            description=index.description or "",
            ai_description=index.ai_description or "",
            updated_at=current_timestamp,
        )
        table_index_query = (
            "MATCH (t:Table {name: $table_name}) "
            "MATCH (i:Index {name: $index_name, table_name: $table_name}) "
            "MERGE (t)-[:HAS_INDEX]->(i)"
        )
        tx.run(
            table_index_query,
            table_name=table_name,
            index_name=index.name,
        )

    @staticmethod
    def _create_constraint_node_tx(tx, constraint: Constraint, table_name: str, project_name: str) -> None:
        current_timestamp = GraphDBBase._get_current_timestamp()
        constraint_query = (
            "MERGE (c:Constraint {name: $name, table_name: $table_name}) "
            "SET c.type = $type, c.columns = $columns, c.reference_table = $reference_table, "
            "c.reference_columns = $reference_columns, c.project_name = $project_name, "
            "c.description = $description, c.ai_description = $ai_description, "
            "c.updated_at = $updated_at"
        )
        tx.run(
            constraint_query,
            name=constraint.name,
            table_name=table_name,
            type=constraint.type,
            columns=json.dumps(constraint.columns),
            reference_table=constraint.reference_table,
            reference_columns=json.dumps(constraint.reference_columns),
            project_name=project_name,
            description=constraint.description or "",
            ai_description=constraint.ai_description or "",
            updated_at=current_timestamp,
        )
        table_constraint_query = (
            "MATCH (t:Table {name: $table_name}) "
            "MATCH (c:Constraint {name: $constraint_name, table_name: $table_name}) "
            "MERGE (t)-[:HAS_CONSTRAINT]->(c)"
        )
        tx.run(
            table_constraint_query,
            table_name=table_name,
            constraint_name=constraint.name,
        )
