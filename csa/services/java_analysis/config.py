"""
Configuration file parsing utilities.
"""
from __future__ import annotations

import os
from typing import List

import yaml

from csa.models.graph_entities import (
    ConfigFile,
    DatabaseConfig,
    LoggingConfig,
    SecurityConfig,
    ServerConfig,
)
from csa.utils.logger import get_logger

def parse_yaml_config(file_path: str) -> ConfigFile:
    """Parse YAML configuration file.
    
    Args:
        file_path: Path to the YAML file
        
    Returns:
        ConfigFile object
    """
    logger = get_logger(__name__)
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            documents = list(yaml.safe_load_all(f))
            content = documents[0] if documents else {}
        
        if not content:
            content = {}
        
        file_name = os.path.basename(file_path)
        file_type = "yaml" if file_path.endswith('.yaml') else "yml"
        
        profiles = []
        if 'spring' in content and 'profiles' in content['spring']:
            if 'active' in content['spring']['profiles']:
                profiles = content['spring']['profiles']['active']
                if isinstance(profiles, str):
                    profiles = [profiles]
        
        # Determine environment
        environment = "dev"  # default
        if profiles:
            environment = profiles[0]
        
        # Extract sections
        sections = []
        for key, value in content.items():
            if isinstance(value, dict):
                sections.append({
                    "name": key,
                    "properties": value,
                    "type": "section"
                })
        
        return ConfigFile(
            name=file_name,
            file_path=file_path,
            file_type=file_type,
            properties=content,
            sections=sections,
            profiles=profiles,
            environment=environment
        )
    
    except Exception as e:
        logger.error(f"Error parsing YAML file {file_path}: {e}")
        return ConfigFile(
            name=os.path.basename(file_path),
            file_path=file_path,
            file_type="yaml",
            properties={},
            sections=[],
            profiles=[],
            environment=""
        )

def parse_properties_config(file_path: str) -> ConfigFile:
    """Parse Properties configuration file.
    
    Args:
        file_path: Path to the properties file
        
    Returns:
        ConfigFile object
    """
    logger = get_logger(__name__)
    
    try:
        properties = {}
        sections = []
        profiles = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Parse key=value pairs
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Remove quotes if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    
                    properties[key] = value
                    
                    # Check for profiles
                    if key == 'spring.profiles.active':
                        profiles = [p.strip() for p in value.split(',')]
        
        # Group properties by section
        section_map = {}
        for key, value in properties.items():
            if '.' in key:
                section = key.split('.')[0]
                if section not in section_map:
                    section_map[section] = {}
                section_map[section][key] = value
            else:
                if 'root' not in section_map:
                    section_map['root'] = {}
                section_map['root'][key] = value
        
        for section_name, section_props in section_map.items():
            sections.append({
                "name": section_name,
                "properties": section_props,
                "type": "section"
            })
        
        # Determine environment
        environment = "dev"  # default
        if profiles:
            environment = profiles[0]
        
        return ConfigFile(
            name=os.path.basename(file_path),
            file_path=file_path,
            file_type="properties",
            properties=properties,
            sections=sections,
            profiles=profiles,
            environment=environment
        )
    
    except Exception as e:
        logger.error(f"Error parsing Properties file {file_path}: {e}")
        return ConfigFile(
            name=os.path.basename(file_path),
            file_path=file_path,
            file_type="properties",
            properties={},
            sections=[],
            profiles=[],
            environment=""
        )


def extract_database_config(config_file: ConfigFile) -> DatabaseConfig:
    """Extract database configuration from config file.
    
    Args:
        config_file: ConfigFile object
        
    Returns:
        DatabaseConfig object
    """
    db_config = DatabaseConfig()
    
    if config_file.file_type in ["yaml", "yml"]:
        # YAML format
        spring_config = config_file.properties.get('spring', {})
        datasource_config = spring_config.get('datasource', {})
        jpa_config = spring_config.get('jpa', {})
        
        db_config.driver = datasource_config.get('driver-class-name', '')
        db_config.url = datasource_config.get('url', '')
        db_config.username = datasource_config.get('username', '')
        db_config.password = datasource_config.get('password', '')
        db_config.dialect = jpa_config.get('database-platform', '')
        db_config.hibernate_ddl_auto = jpa_config.get('hibernate', {}).get('ddl-auto', '')
        db_config.show_sql = jpa_config.get('show-sql', False)
        db_config.format_sql = jpa_config.get('properties', {}).get('hibernate', {}).get('format_sql', False)
        
        # Store additional JPA properties
        if 'properties' in jpa_config:
            db_config.jpa_properties = jpa_config['properties']
    
    else:
        # Properties format
        props = config_file.properties
        
        db_config.driver = props.get('spring.datasource.driver-class-name', '')
        db_config.url = props.get('spring.datasource.url', '')
        db_config.username = props.get('spring.datasource.username', '')
        db_config.password = props.get('spring.datasource.password', '')
        db_config.dialect = props.get('spring.jpa.database-platform', '')
        db_config.hibernate_ddl_auto = props.get('spring.jpa.hibernate.ddl-auto', '')
        db_config.show_sql = props.get('spring.jpa.show-sql', 'false').lower() == 'true'
        db_config.format_sql = props.get('spring.jpa.properties.hibernate.format_sql', 'false').lower() == 'true'
        
        # Store additional JPA properties
        jpa_props = {}
        for key, value in props.items():
            if key.startswith('spring.jpa.properties.'):
                jpa_props[key] = value
        db_config.jpa_properties = jpa_props
    
    return db_config

def extract_server_config(config_file: ConfigFile) -> ServerConfig:
    """Extract server configuration from config file.
    
    Args:
        config_file: ConfigFile object
        
    Returns:
        ServerConfig object
    """
    server_config = ServerConfig()
    
    if config_file.file_type in ["yaml", "yml"]:
        # YAML format
        server_props = config_file.properties.get('server', {})
        
        server_config.port = server_props.get('port', 8080)
        server_config.context_path = server_props.get('servlet', {}).get('context-path', '')
        server_config.servlet_path = server_props.get('servlet', {}).get('path', '')
        
        # SSL configuration
        ssl_config = server_props.get('ssl', {})
        server_config.ssl_enabled = bool(ssl_config)
        server_config.ssl_key_store = ssl_config.get('key-store', '')
        server_config.ssl_key_store_password = ssl_config.get('key-store-password', '')
        server_config.ssl_key_store_type = ssl_config.get('key-store-type', '')
    
    else:
        # Properties format
        props = config_file.properties
        
        server_config.port = int(props.get('server.port', '8080'))
        server_config.context_path = props.get('server.servlet.context-path', '')
        server_config.servlet_path = props.get('server.servlet.path', '')
        
        # SSL configuration
        server_config.ssl_enabled = any(key.startswith('server.ssl.') for key in props.keys())
        server_config.ssl_key_store = props.get('server.ssl.key-store', '')
        server_config.ssl_key_store_password = props.get('server.ssl.key-store-password', '')
        server_config.ssl_key_store_type = props.get('server.ssl.key-store-type', '')
    
    return server_config

def extract_security_config(config_file: ConfigFile) -> SecurityConfig:
    """Extract security configuration from config file.
    
    Args:
        config_file: ConfigFile object
        
    Returns:
        SecurityConfig object
    """
    security_config = SecurityConfig()
    
    if config_file.file_type in ["yaml", "yml"]:
        # YAML format
        security_props = config_file.properties.get('security', {})
        jwt_props = security_props.get('jwt', {})
        cors_props = security_props.get('cors', {})
        
        security_config.enabled = bool(security_props)
        security_config.authentication_type = security_props.get('authentication-type', '')
        security_config.jwt_secret = jwt_props.get('secret', '')
        security_config.jwt_expiration = jwt_props.get('expiration', 0)
        security_config.cors_allowed_origins = cors_props.get('allowed-origins', [])
        security_config.cors_allowed_methods = cors_props.get('allowed-methods', [])
        security_config.cors_allowed_headers = cors_props.get('allowed-headers', [])
    
    else:
        # Properties format
        props = config_file.properties
        
        security_config.enabled = any(key.startswith('security.') for key in props.keys())
        security_config.authentication_type = props.get('security.authentication-type', '')
        security_config.jwt_secret = props.get('security.jwt.secret', '')
        security_config.jwt_expiration = int(props.get('security.jwt.expiration', '0'))
        
        # CORS configuration
        origins = props.get('security.cors.allowed-origins', '')
        if origins:
            security_config.cors_allowed_origins = [o.strip() for o in origins.split(',')]
        
        methods = props.get('security.cors.allowed-methods', '')
        if methods:
            security_config.cors_allowed_methods = [m.strip() for m in methods.split(',')]
        
        headers = props.get('security.cors.allowed-headers', '')
        if headers:
            security_config.cors_allowed_headers = [h.strip() for h in headers.split(',')]
    
    return security_config

def extract_logging_config(config_file: ConfigFile) -> LoggingConfig:
    """Extract logging configuration from config file.
    
    Args:
        config_file: ConfigFile object
        
    Returns:
        LoggingConfig object
    """
    logging_config = LoggingConfig()
    
    if config_file.file_type in ["yaml", "yml"]:
        # YAML format
        logging_props = config_file.properties.get('logging', {})
        
        logging_config.level = logging_props.get('level', {}).get('root', 'INFO')
        logging_config.pattern = logging_props.get('pattern', {}).get('console', '')
        logging_config.file_path = logging_props.get('file', {}).get('name', '')
        logging_config.max_file_size = logging_props.get('file', {}).get('max-size', '')
        logging_config.max_history = logging_props.get('file', {}).get('max-history', 0)
        logging_config.console_output = logging_props.get('console', {}).get('enabled', True)
    
    else:
        # Properties format
        props = config_file.properties
        
        logging_config.level = props.get('logging.level.root', 'INFO')
        logging_config.pattern = props.get('logging.pattern.console', '')
        logging_config.file_path = props.get('logging.file.name', '')
        logging_config.max_file_size = props.get('logging.file.max-size', '')
        logging_config.max_history = int(props.get('logging.file.max-history', '0'))
        logging_config.console_output = props.get('logging.console.enabled', 'true').lower() == 'true'
    
    return logging_config

def extract_config_files(directory: str) -> list[ConfigFile]:
    """Extract configuration files from directory.
    
    Args:
        directory: Directory to search for config files
        
    Returns:
        List of ConfigFile objects
    """
    config_files = []
    
    # Common config file patterns
    config_patterns = [
        "application.yml",
        "application.yaml", 
        "application.properties",
        "application-*.properties",
        "bootstrap.yml",
        "bootstrap.yaml",
        "bootstrap.properties"
    ]
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            # Check if file matches any config pattern
            is_config_file = False
            for pattern in config_patterns:
                if pattern == file or (pattern.endswith('*') and file.startswith(pattern[:-1])):
                    is_config_file = True
                    break
            
            if is_config_file:
                file_path = os.path.join(root, file)
                
                if file.endswith(('.yml', '.yaml')):
                    config_file = parse_yaml_config(file_path)
                elif file.endswith('.properties'):
                    config_file = parse_properties_config(file_path)
                else:
                    continue
                
                config_files.append(config_file)
    
    return config_files


__all__ = [
    "extract_config_files",
    "extract_database_config",
    "extract_logging_config",
    "extract_security_config",
    "extract_server_config",
    "parse_properties_config",
    "parse_yaml_config",
]

