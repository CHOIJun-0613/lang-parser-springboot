"""
JPA entity and repository analysis helpers.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

from csa.models.graph_entities import (
    Annotation,
    Class,
    Field,
    JpaColumn,
    JpaEntity,
    JpaQuery,
    JpaRelationship,
    JpaRepository,
    Table,
)
from csa.utils.logger import get_logger

def extract_jpa_entities_from_classes(classes: list[Class]) -> list[JpaEntity]:
    """Extract JPA Entities from parsed classes with enhanced analysis.
    
    Args:
        classes: List of parsed Class objects
        
    Returns:
        List of JpaEntity objects
    """
    entities = []
    
    for cls in classes:
        is_entity = any(ann.name == "Entity" for ann in cls.annotations)
        
        if not is_entity:
            continue
        
        table_info = _extract_table_info(cls)
        
        columns = []
        relationships = []
        
        for prop in cls.properties:
            jpa_annotations = [ann for ann in prop.annotations if ann.category == "jpa"]
            
            if jpa_annotations or _is_jpa_property(prop, cls):
                column_info = _extract_column_info(prop, jpa_annotations)
                if column_info:
                    columns.append(column_info)
                
                relationship_info = _extract_relationship_info(prop, jpa_annotations)
                if relationship_info:
                    relationships.append(relationship_info)
        
        entity = JpaEntity(
            name=cls.name,
            table_name=table_info["name"],
            columns=columns,
            relationships=relationships,
            annotations=[ann.name for ann in cls.annotations if ann.category == "jpa"],
            package_name=cls.package_name,
            file_path=cls.file_path,
            description=table_info.get("description", ""),
            ai_description=table_info.get("ai_description", "")
        )
        entities.append(entity)
    
    return entities

def _extract_table_info(cls: Class) -> dict:
    """Extract table information from entity class annotations."""
    table_name = cls.name.lower()  # default table name
    schema = ""
    catalog = ""
    unique_constraints = []
    indexes = []
    description = ""
    
    for ann in cls.annotations:
        if ann.name == "Table":
            if "name" in ann.parameters:
                table_name = ann.parameters["name"]
            if "schema" in ann.parameters:
                schema = ann.parameters["schema"]
            if "catalog" in ann.parameters:
                catalog = ann.parameters["catalog"]
            if "uniqueConstraints" in ann.parameters:
                unique_constraints = ann.parameters["uniqueConstraints"]
            if "indexes" in ann.parameters:
                indexes = ann.parameters["indexes"]
    
    return {
        "name": table_name,
        "schema": schema,
        "catalog": catalog,
        "unique_constraints": unique_constraints,
        "indexes": indexes,
        "description": description
    }

def _is_jpa_property(prop: Field, cls: Class) -> bool:
    """Check if a property should be considered as JPA property even without explicit annotations."""
    has_transient = any(ann.name == "Transient" for ann in prop.annotations)
    return not has_transient

def _extract_column_info(prop: Field, jpa_annotations: list[Annotation]) -> dict:
    """Extract detailed column information from property and annotations."""
    column_name = prop.name  # default column name
    nullable = True
    unique = False
    length = 0
    precision = 0
    scale = 0
    insertable = True
    updatable = True
    column_definition = ""
    table = ""
    is_primary_key = False
    is_version = False
    is_lob = False
    is_enumerated = False
    is_temporal = False
    temporal_type = ""
    enum_type = ""
    
    for ann in jpa_annotations:
        if ann.name == "Column":
            if "name" in ann.parameters:
                column_name = ann.parameters["name"]
            if "nullable" in ann.parameters:
                nullable = ann.parameters["nullable"]
            if "unique" in ann.parameters:
                unique = ann.parameters["unique"]
            if "length" in ann.parameters:
                length = ann.parameters["length"]
            if "precision" in ann.parameters:
                precision = ann.parameters["precision"]
            if "scale" in ann.parameters:
                scale = ann.parameters["scale"]
            if "insertable" in ann.parameters:
                insertable = ann.parameters["insertable"]
            if "updatable" in ann.parameters:
                updatable = ann.parameters["updatable"]
            if "columnDefinition" in ann.parameters:
                column_definition = ann.parameters["columnDefinition"]
            if "table" in ann.parameters:
                table = ann.parameters["table"]
                
        elif ann.name == "Id":
            column_name = "id"  # Primary key column
            nullable = False
            unique = True
            is_primary_key = True
            
        elif ann.name == "Version":
            is_version = True
            
        elif ann.name == "Lob":
            is_lob = True
            
        elif ann.name == "Enumerated":
            is_enumerated = True
            if "value" in ann.parameters:
                enum_type = ann.parameters["value"]
                
        elif ann.name == "Temporal":
            is_temporal = True
            if "value" in ann.parameters:
                temporal_type = ann.parameters["value"]
                
        elif ann.name == "JoinColumn":
            if "name" in ann.parameters:
                column_name = ann.parameters["name"]
            if "nullable" in ann.parameters:
                nullable = ann.parameters["nullable"]
            if "unique" in ann.parameters:
                unique = ann.parameters["unique"]
            if "insertable" in ann.parameters:
                insertable = ann.parameters["insertable"]
            if "updatable" in ann.parameters:
                updatable = ann.parameters["updatable"]
            if "columnDefinition" in ann.parameters:
                column_definition = ann.parameters["columnDefinition"]
    
    return {
        "property_name": prop.name,
        "column_name": column_name,
        "data_type": prop.type,
        "nullable": nullable,
        "unique": unique,
        "length": length,
        "precision": precision,
        "scale": scale,
        "insertable": insertable,
        "updatable": updatable,
        "column_definition": column_definition,
        "table": table,
        "is_primary_key": is_primary_key,
        "is_version": is_version,
        "is_lob": is_lob,
        "is_enumerated": is_enumerated,
        "is_temporal": is_temporal,
        "temporal_type": temporal_type,
        "enum_type": enum_type,
        "annotations": [ann.name for ann in jpa_annotations]
    }

def _extract_relationship_info(prop: Field, jpa_annotations: list[Annotation]) -> dict:
    """Extract relationship information from property and annotations."""
    relationship_type = None
    target_entity = ""
    mapped_by = ""
    join_column = ""
    join_columns = []
    join_table = ""
    cascade = []
    fetch = "LAZY"
    orphan_removal = False
    optional = True
    
    for ann in jpa_annotations:
        if ann.name in ["OneToOne", "OneToMany", "ManyToOne", "ManyToMany"]:
            relationship_type = ann.name
            if "targetEntity" in ann.parameters:
                target_entity = ann.parameters["targetEntity"]
            if "mappedBy" in ann.parameters:
                mapped_by = ann.parameters["mappedBy"]
            if "cascade" in ann.parameters:
                cascade = ann.parameters["cascade"] if isinstance(ann.parameters["cascade"], list) else [ann.parameters["cascade"]]
            if "fetch" in ann.parameters:
                fetch = ann.parameters["fetch"]
            if "orphanRemoval" in ann.parameters:
                orphan_removal = ann.parameters["orphanRemoval"]
            if "optional" in ann.parameters:
                optional = ann.parameters["optional"]
                
        elif ann.name == "JoinColumn":
            if "name" in ann.parameters:
                join_column = ann.parameters["name"]
            join_columns.append({
                "name": ann.parameters.get("name", ""),
                "referencedColumnName": ann.parameters.get("referencedColumnName", ""),
                "nullable": ann.parameters.get("nullable", True),
                "unique": ann.parameters.get("unique", False),
                "insertable": ann.parameters.get("insertable", True),
                "updatable": ann.parameters.get("updatable", True),
                "columnDefinition": ann.parameters.get("columnDefinition", ""),
                "table": ann.parameters.get("table", "")
            })
            
        elif ann.name == "JoinTable":
            if "name" in ann.parameters:
                join_table = ann.parameters["name"]
    
    if relationship_type:
        return {
            "type": relationship_type,
            "target_entity": target_entity,
            "mapped_by": mapped_by,
            "join_column": join_column,
            "join_columns": join_columns,
            "join_table": join_table,
            "cascade": cascade,
            "fetch": fetch,
            "orphan_removal": orphan_removal,
            "optional": optional,
            "annotations": [ann.name for ann in jpa_annotations]
        }
    
    return None

def extract_jpa_repositories_from_classes(classes: list[Class]) -> list[JpaRepository]:
    """Extract JPA Repositories from parsed classes.
    
    Args:
        classes: List of parsed Class objects
        
    Returns:
        List of JpaRepository objects
    """
    repositories = []
    
    for cls in classes:
        is_repository = _is_jpa_repository(cls)
        
        if not is_repository:
            continue
        
        entity_type = _extract_entity_type_from_repository(cls)
        
        methods = _extract_repository_methods(cls)
        
        repository = JpaRepository(
            name=cls.name,
            entity_type=entity_type,
            methods=methods,
            package_name=cls.package_name,
            file_path=cls.file_path,
            annotations=[ann.name for ann in cls.annotations if ann.category == "jpa"],
            description="",
            ai_description=""
        )
        repositories.append(repository)
    
    return repositories

def _is_jpa_repository(cls: Class) -> bool:
    """Check if a class is a JPA Repository."""
    jpa_repository_interfaces = {
        "JpaRepository", "CrudRepository", "PagingAndSortingRepository",
        "JpaSpecificationExecutor", "QueryByExampleExecutor"
    }
    
    for interface in cls.interfaces:
        interface_name = interface.split('.')[-1]  # Get simple name
        if interface_name in jpa_repository_interfaces:
            return True
    
    has_repository_annotation = any(ann.name == "Repository" for ann in cls.annotations)
    
    is_repository_by_name = cls.name.endswith("Repository")
    
    return has_repository_annotation or is_repository_by_name

def _extract_entity_type_from_repository(cls: Class) -> str:
    """Extract entity type from repository class generic parameters."""
    # This is a simplified implementation
    # In a real implementation, you would parse the generic type parameters
    # from the class declaration
    
    # For now, try to infer from the class name
    # Common patterns: UserRepository -> User, UserEntityRepository -> UserEntity
    class_name = cls.name
    
    if class_name.endswith("Repository"):
        entity_name = class_name[:-10]  # Remove "Repository"
        return entity_name
    elif class_name.endswith("EntityRepository"):
        entity_name = class_name[:-15]  # Remove "EntityRepository"
        return entity_name
    
    return ""

def _extract_repository_methods(cls: Class) -> list[dict]:
    """Extract repository methods with query analysis."""
    methods = []
    
    for method in cls.methods:
        method_info = {
            "name": method.name,
            "return_type": method.return_type,
            "parameters": [{"name": param.name, "type": param.type} for param in method.parameters],
            "annotations": [ann.name for ann in method.annotations],
            "query_info": _analyze_repository_method(method)
        }
        methods.append(method_info)
    
    return methods

def _analyze_repository_method(method: Method) -> dict:
    """Analyze a repository method to extract query information."""
    query_info = {
        "query_type": "METHOD",  # Default to method query
        "query_content": "",
        "is_modifying": False,
        "is_native": False,
        "is_jpql": False,
        "is_named": False,
        "query_name": "",
        "parameters": []
    }
    
    for ann in method.annotations:
        if ann.name == "Query":
            query_info["query_type"] = "JPQL"
            query_info["is_jpql"] = True
            if "value" in ann.parameters:
                query_info["query_content"] = ann.parameters["value"]
            if "nativeQuery" in ann.parameters and ann.parameters["nativeQuery"]:
                query_info["query_type"] = "NATIVE"
                query_info["is_native"] = True
                query_info["is_jpql"] = False
            if "name" in ann.parameters:
                query_info["query_name"] = ann.parameters["name"]
                query_info["is_named"] = True
                
        elif ann.name == "Modifying":
            query_info["is_modifying"] = True
            
        elif ann.name == "NamedQuery":
            query_info["query_type"] = "NAMED"
            query_info["is_named"] = True
            if "name" in ann.parameters:
                query_info["query_name"] = ann.parameters["name"]
            if "query" in ann.parameters:
                query_info["query_content"] = ann.parameters["query"]
    
    if query_info["query_type"] == "METHOD":
        query_info.update(_analyze_method_name_query(method.name, method.parameters))
    
    return query_info

def _analyze_method_name_query(method_name: str, parameters: list[Field]) -> dict:
    """Analyze method name to derive query information."""
    query_info = {
        "derived_query": True,
        "operation": "SELECT",  # Default operation
        "entity_field": "",
        "conditions": [],
        "sorting": [],
        "paging": False
    }
    
    method_name_lower = method_name.lower()
    
    if method_name_lower.startswith("find") or method_name_lower.startswith("get"):
        query_info["operation"] = "SELECT"
    elif method_name_lower.startswith("save") or method_name_lower.startswith("insert"):
        query_info["operation"] = "INSERT"
    elif method_name_lower.startswith("update"):
        query_info["operation"] = "UPDATE"
    elif method_name_lower.startswith("delete") or method_name_lower.startswith("remove"):
        query_info["operation"] = "DELETE"
    elif method_name_lower.startswith("count"):
        query_info["operation"] = "COUNT"
    elif method_name_lower.startswith("exists"):
        query_info["operation"] = "EXISTS"
    
    if "orderby" in method_name_lower or "sort" in method_name_lower:
        query_info["sorting"] = ["field_name"]  # Simplified
    
    if "page" in method_name_lower or "pageable" in method_name_lower:
        query_info["paging"] = True
    
    field_patterns = [
        r"findBy(\w+)",
        r"getBy(\w+)",
        r"countBy(\w+)",
        r"existsBy(\w+)",
        r"deleteBy(\w+)"
    ]
    
    for pattern in field_patterns:
        match = re.search(pattern, method_name, re.IGNORECASE)
        if match:
            field_name = match.group(1)
            query_info["entity_field"] = field_name
            query_info["conditions"].append({
                "field": field_name,
                "operator": "=",
                "parameter": field_name.lower()
            })
            break
    
    return query_info

def extract_jpa_queries_from_repositories(repositories: list[JpaRepository]) -> list[JpaQuery]:
    """Extract JPA Queries from repository methods.
    
    Args:
        repositories: List of JpaRepository objects
        
    Returns:
        List of JpaQuery objects
    """
    queries = []
    
    for repository in repositories:
        for method in repository.methods:
            query_info = method.get("query_info", {})
            
            if query_info.get("query_content") or query_info.get("derived_query"):
                query = JpaQuery(
                    name=f"{repository.name}.{method['name']}",
                    query_type=query_info.get("query_type", "METHOD"),
                    query_content=query_info.get("query_content", ""),
                    return_type=method.get("return_type", ""),
                    parameters=method.get("parameters", []),
                    repository_name=repository.name,
                    method_name=method["name"],
                    annotations=method.get("annotations", []),
                    description="",
                    ai_description=""
                )
                queries.append(query)
    
    return queries

def analyze_jpa_entity_table_mapping(jpa_entities: list[JpaEntity], db_tables: list[Table]) -> dict:
    """Analyze mapping relationships between JPA entities and database tables.
    
    Args:
        jpa_entities: List of JPA entities
        db_tables: List of database tables
        
    Returns:
        Dictionary containing mapping analysis results
    """
    mapping_analysis = {
        "entity_table_mappings": [],
        "unmapped_entities": [],
        "unmapped_tables": [],
        "mapping_issues": [],
        "relationship_analysis": []
    }
    
    # Create table name lookup
    table_lookup = {table.name.lower(): table for table in db_tables}
    
    for entity in jpa_entities:
        entity_table_name = entity.table_name.lower()
        
        if entity_table_name in table_lookup:
            table = table_lookup[entity_table_name]
            
            # Analyze column mappings
            column_mappings = _analyze_column_mappings(entity, table)
            
            mapping_analysis["entity_table_mappings"].append({
                "entity_name": entity.name,
                "table_name": entity.table_name,
                "column_mappings": column_mappings,
                "mapping_accuracy": _calculate_mapping_accuracy(column_mappings),
                "issues": _identify_mapping_issues(entity, table, column_mappings)
            })
        else:
            mapping_analysis["unmapped_entities"].append({
                "entity_name": entity.name,
                "expected_table": entity.table_name,
                "reason": "Table not found in database schema"
            })
    
    # Find unmapped tables
    mapped_table_names = {mapping["table_name"].lower() for mapping in mapping_analysis["entity_table_mappings"]}
    for table in db_tables:
        if table.name.lower() not in mapped_table_names:
            mapping_analysis["unmapped_tables"].append({
                "table_name": table.name,
                "reason": "No corresponding JPA entity found"
            })
    
    # Analyze entity relationships
    mapping_analysis["relationship_analysis"] = _analyze_entity_relationships(jpa_entities)
    
    return mapping_analysis

def _analyze_column_mappings(entity: JpaEntity, table: Table) -> list[dict]:
    """Analyze column mappings between entity and table."""
    column_mappings = []
    
    # Create column lookup for the table
    table_columns = {col.name.lower(): col for col in table.columns}
    
    for column_info in entity.columns:
        column_name = column_info["column_name"].lower()
        
        if column_name in table_columns:
            db_column = table_columns[column_name]
            
            mapping = {
                "entity_property": column_info["property_name"],
                "entity_column": column_info["column_name"],
                "db_column": db_column.name,
                "data_type_match": _compare_data_types(column_info["data_type"], db_column.data_type),
                "nullable_match": column_info["nullable"] == db_column.nullable,
                "unique_match": column_info["unique"] == db_column.unique,
                "is_primary_key": column_info.get("is_primary_key", False) == db_column.primary_key,
                "mapping_quality": "good" if _is_good_mapping(column_info, db_column) else "needs_review"
            }
        else:
            mapping = {
                "entity_property": column_info["property_name"],
                "entity_column": column_info["column_name"],
                "db_column": None,
                "data_type_match": False,
                "nullable_match": False,
                "unique_match": False,
                "is_primary_key": False,
                "mapping_quality": "missing"
            }
        
        column_mappings.append(mapping)
    
    return column_mappings

def _compare_data_types(entity_type: str, db_type: str) -> bool:
    """Compare entity data type with database column type."""
    # Simplified type comparison
    type_mapping = {
        "String": ["varchar", "char", "text", "clob"],
        "Integer": ["int", "integer", "number"],
        "Long": ["bigint", "number"],
        "Double": ["double", "float", "number"],
        "Boolean": ["boolean", "bit"],
        "Date": ["date", "timestamp", "datetime"],
        "LocalDateTime": ["timestamp", "datetime"],
        "BigDecimal": ["decimal", "numeric", "number"]
    }
    
    entity_type_simple = entity_type.split('.')[-1]  # Get simple class name
    
    if entity_type_simple in type_mapping:
        db_type_lower = db_type.lower()
        return any(db_type_lower.startswith(mapped_type) for mapped_type in type_mapping[entity_type_simple])
    
    return False

def _is_good_mapping(column_info: dict, db_column: Table) -> bool:
    """Check if the mapping between entity column and DB column is good."""
    return (
        _compare_data_types(column_info["data_type"], db_column.data_type) and
        column_info["nullable"] == db_column.nullable and
        column_info["unique"] == db_column.unique and
        column_info.get("is_primary_key", False) == db_column.primary_key
    )

def _calculate_mapping_accuracy(column_mappings: list[dict]) -> float:
    """Calculate mapping accuracy percentage."""
    if not column_mappings:
        return 0.0
    
    good_mappings = sum(1 for mapping in column_mappings if mapping["mapping_quality"] == "good")
    return (good_mappings / len(column_mappings)) * 100

def _identify_mapping_issues(entity: JpaEntity, table: Table, column_mappings: list[dict]) -> list[str]:
    """Identify mapping issues between entity and table."""
    issues = []
    
    for mapping in column_mappings:
        if mapping["mapping_quality"] == "missing":
            issues.append(f"Column '{mapping['entity_column']}' not found in table '{table.name}'")
        elif mapping["mapping_quality"] == "needs_review":
            if not mapping["data_type_match"]:
                issues.append(f"Data type mismatch for column '{mapping['entity_column']}'")
            if not mapping["nullable_match"]:
                issues.append(f"Nullable constraint mismatch for column '{mapping['entity_column']}'")
            if not mapping["unique_match"]:
                issues.append(f"Unique constraint mismatch for column '{mapping['entity_column']}'")
    
    return issues

def _analyze_entity_relationships(jpa_entities: list[JpaEntity]) -> list[dict]:
    """Analyze relationships between JPA entities."""
    relationship_analysis = []
    
    for entity in jpa_entities:
        for relationship in entity.relationships:
            analysis = {
                "source_entity": entity.name,
                "target_entity": relationship.get("target_entity", ""),
                "relationship_type": relationship.get("type", ""),
                "mapped_by": relationship.get("mapped_by", ""),
                "join_column": relationship.get("join_column", ""),
                "cascade": relationship.get("cascade", []),
                "fetch_type": relationship.get("fetch", "LAZY"),
                "is_bidirectional": bool(relationship.get("mapped_by", "")),
                "relationship_quality": _assess_relationship_quality(relationship)
            }
            relationship_analysis.append(analysis)
    
    return relationship_analysis

def _assess_relationship_quality(relationship: dict) -> str:
    """Assess the quality of a JPA relationship."""
    issues = []
    
    if not relationship.get("target_entity"):
        issues.append("Missing target entity")
    
    if relationship.get("type") in ["OneToMany", "ManyToMany"] and not relationship.get("mapped_by"):
        issues.append("Missing mappedBy for collection relationship")
    
    if relationship.get("type") in ["OneToOne", "ManyToOne"] and not relationship.get("join_column"):
        issues.append("Missing join column for single relationship")
    
    if not issues:
        return "good"
    elif len(issues) == 1:
        return "needs_review"
    else:
        return "needs_attention"


__all__ = [
    "analyze_jpa_entity_table_mapping",
    "extract_jpa_entities_from_classes",
    "extract_jpa_queries_from_repositories",
    "extract_jpa_repositories_from_classes",
]

