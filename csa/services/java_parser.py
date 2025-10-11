"""
Backward-compatible facade exposing Java parsing helpers.
"""
from __future__ import annotations

from csa.services.java_analysis.config import (
    extract_config_files,
    extract_database_config,
    extract_logging_config,
    extract_security_config,
    extract_server_config,
    parse_properties_config,
    parse_yaml_config,
)
from csa.services.java_analysis.jpa import (
    analyze_jpa_entity_table_mapping,
    extract_jpa_entities_from_classes,
    extract_jpa_queries_from_repositories,
    extract_jpa_repositories_from_classes,
)
from csa.services.java_analysis.mybatis import (
    analyze_mybatis_resultmap_mapping,
    analyze_sql_method_relationships,
    extract_mybatis_mappers_from_classes,
    extract_mybatis_xml_mappers,
    extract_sql_statements_from_mappers,
    generate_db_call_chain_analysis,
    parse_mybatis_xml_file,
)
from csa.services.java_analysis.project import (
    parse_java_project,
    parse_java_project_full,
    parse_single_java_file,
)
from csa.services.java_analysis.spring import (
    analyze_bean_dependencies,
    extract_beans_from_classes,
    extract_endpoints_from_classes,
)
from csa.services.java_analysis.tests import (
    analyze_test_methods,
    extract_test_classes_from_classes,
)
from csa.services.java_analysis.utils import (
    classify_springboot_annotation,
    classify_test_annotation,
    extract_project_name,
    extract_sub_type,
    generate_lombok_methods,
    parse_annotations,
)

__all__ = [
    # utils
    "classify_springboot_annotation",
    "classify_test_annotation",
    "extract_project_name",
    "extract_sub_type",
    "generate_lombok_methods",
    "parse_annotations",
    # spring
    "analyze_bean_dependencies",
    "extract_beans_from_classes",
    "extract_endpoints_from_classes",
    # mybatis
    "analyze_mybatis_resultmap_mapping",
    "analyze_sql_method_relationships",
    "extract_mybatis_mappers_from_classes",
    "extract_mybatis_xml_mappers",
    "extract_sql_statements_from_mappers",
    "generate_db_call_chain_analysis",
    "parse_mybatis_xml_file",
    # jpa
    "analyze_jpa_entity_table_mapping",
    "extract_jpa_entities_from_classes",
    "extract_jpa_queries_from_repositories",
    "extract_jpa_repositories_from_classes",
    # config
    "extract_config_files",
    "extract_database_config",
    "extract_logging_config",
    "extract_security_config",
    "extract_server_config",
    "parse_properties_config",
    "parse_yaml_config",
    # tests
    "analyze_test_methods",
    "extract_test_classes_from_classes",
    # project
    "parse_java_project",
    "parse_java_project_full",
    "parse_single_java_file",
]
