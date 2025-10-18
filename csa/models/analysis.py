"""
Analysis-specific data models used for sharing structured results between services.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

from pydantic import BaseModel, Field


class JavaAnalysisStats(BaseModel):
    """Aggregated statistics for a Java analysis run."""

    project_name: Optional[str] = None
    total_files: int = 0
    processed_files: int = 0
    error_files: int = 0
    packages: int = 0
    classes: int = 0
    methods: int = 0
    fields: int = 0
    beans: int = 0
    endpoints: int = 0
    mybatis_mappers: int = 0
    jpa_entities: int = 0
    jpa_repositories: int = 0
    jpa_queries: int = 0
    config_files: int = 0
    test_classes: int = 0
    sql_statements: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    metadata: Dict[str, int] = Field(default_factory=dict)

    class Config:
        allow_mutation = True

    @property
    def duration_seconds(self) -> Optional[float]:
        """Return run duration in seconds if timestamps are available."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None


class DatabaseAnalysisStats(BaseModel):
    """Aggregated statistics for a database analysis run."""

    ddl_files: int = 0
    databases: int = 0
    tables: int = 0
    columns: int = 0
    indexes: int = 0
    constraints: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    metadata: Dict[str, int] = Field(default_factory=dict)

    class Config:
        allow_mutation = True

    @property
    def duration_seconds(self) -> Optional[float]:
        """Return run duration in seconds if timestamps are available."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None


class AnalysisResult(BaseModel):
    """Wrapper representing the outcome of an analysis invocation."""

    success: bool
    java_stats: Optional[JavaAnalysisStats] = None
    db_stats: Optional[DatabaseAnalysisStats] = None
    message: Optional[str] = None
    error: Optional[str] = None

    class Config:
        allow_mutation = True


class JavaAnalysisArtifacts(BaseModel):
    """Container for parsed Java artifacts before persisting to Neo4j."""

    packages: Sequence[Any]
    classes: Sequence[Any]
    class_to_package_map: Dict[str, str]
    beans: Sequence[Any]
    dependencies: Sequence[Any]
    endpoints: Sequence[Any]
    mybatis_mappers: Sequence[Any]
    jpa_entities: Sequence[Any]
    jpa_repositories: Sequence[Any]
    jpa_queries: Sequence[Any]
    config_files: Sequence[Any]
    test_classes: Sequence[Any]
    sql_statements: Sequence[Any]
    project_name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        arbitrary_types_allowed = True
        allow_mutation = True


class DatabaseAnalysisArtifacts(BaseModel):
    """Container for parsed database artifacts prior to persistence."""

    database_name: str
    objects: List[Any]

    class Config:
        arbitrary_types_allowed = True
        allow_mutation = True


class Neo4jDatabaseStats(BaseModel):
    """Neo4j 데이터베이스에 실제 저장된 객체 통계"""

    total_nodes: int = 0
    total_relationships: int = 0
    node_counts_by_label: Dict[str, int] = Field(default_factory=dict)
    relationship_counts_by_type: Dict[str, int] = Field(default_factory=dict)

    class Config:
        allow_mutation = True
