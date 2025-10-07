import re
import os
from typing import List, Dict, Any, Optional
from datetime import datetime

from src.models.graph_entities import Database, Table, Column, Index, Constraint
from src.utils.logger import get_logger


class DBParser:
    """A parser for analyzing database DDL scripts and creating graph entities."""

    def __init__(self):
        self.logger = get_logger(__name__)

    def parse_ddl_file(self, file_path: str, project_name: str) -> List[Dict[str, Any]]:
        """
        Parse a DDL file and return database objects.
        
        Args:
            file_path: Path to the DDL file
            project_name: Name of the project
            
        Returns:
            List of database objects to be added to the graph
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            # Extract database name from comments or filename
            database_name = self._extract_database_name(content, file_path)
            environment = self._extract_environment(content, file_path)
            
            # Parse tables
            tables = self._parse_tables(content)
            
            # Parse indexes
            indexes = self._parse_indexes(content)
            
            # Parse constraints
            constraints = self._parse_constraints(content)
            
            # Create database object
            database = Database(
                name=database_name,
                version="1.0",
                environment=environment,
                description=f"Database schema for {project_name}",
                ai_description="",
                updated_at=datetime.now().strftime("%Y/%m/%d %H:%M:%S.%f")[:-3]
            )
            
            # Create table objects
            table_objects = []
            column_objects = []
            
            for table_name, table_info in tables.items():
                table = Table(
                    name=table_name,
                    schema=table_info.get('schema', 'public'),
                    comment=table_info.get('description', ''),
                    ai_description="",
                    updated_at=datetime.now().strftime("%Y/%m/%d %H:%M:%S.%f")[:-3]
                )
                table_objects.append(table)
                
                # Create column objects for this table
                for column_info in table_info.get('columns', []):
                    column = Column(
                        name=column_info['name'],
                        data_type=column_info['data_type'],
                        nullable=column_info.get('nullable', True),
                        unique=column_info.get('unique', False),
                        primary_key=column_info.get('primary_key', False),
                        default_value=column_info.get('default_value', ''),
                        constraints=column_info.get('constraints', []),
                        comment=column_info.get('description', ''),
                        ai_description="",
                        updated_at=datetime.now().strftime("%Y/%m/%d %H:%M:%S.%f")[:-3]
                    )
                    # Add table_name to column for relationship
                    column.table_name = table_name
                    column_objects.append(column)
            
            # Create index objects
            index_objects = []
            for table_name, table_indexes in indexes.items():
                for index_info in table_indexes:
                    index = Index(
                        name=index_info['name'],
                        type=index_info.get('type', 'B-tree'),
                        columns=index_info.get('columns', []),
                        table_name=table_name,
                        description=index_info.get('description', ''),
                        ai_description="",
                        updated_at=datetime.now().strftime("%Y/%m/%d %H:%M:%S.%f")[:-3]
                    )
                    index_objects.append((index, table_name))
            
            # Create constraint objects
            constraint_objects = []
            for table_name, table_constraints in constraints.items():
                for constraint_info in table_constraints:
                    constraint = Constraint(
                        name=constraint_info['name'],
                        type=constraint_info['type'],
                        definition=constraint_info.get('definition', ''),
                        table_name=table_name,
                        description=constraint_info.get('description', ''),
                        ai_description="",
                        updated_at=datetime.now().strftime("%Y/%m/%d %H:%M:%S.%f")[:-3]
                    )
                    constraint_objects.append((constraint, table_name))
            
            return {
                'database': database,
                'tables': table_objects,
                'columns': column_objects,
                'indexes': index_objects,
                'constraints': constraint_objects
            }
            
        except Exception as e:
            self.logger.error(f"Error parsing DDL file {file_path}: {str(e)}")
            raise

    def _extract_database_name(self, content: str, file_path: str) -> str:
        """Extract database name from DDL content or filename."""
        # Try to extract from comments
        db_match = re.search(r"-- Database:\s*(\w+)", content, re.IGNORECASE)
        if db_match:
            return db_match.group(1)
        
        # Try to extract from CREATE DATABASE statements
        create_db_match = re.search(r"CREATE\s+DATABASE\s+(\w+)", content, re.IGNORECASE)
        if create_db_match:
            return create_db_match.group(1)
        
        # Extract from filename
        filename = os.path.basename(file_path)
        return os.path.splitext(filename)[0]

    def _extract_environment(self, content: str, file_path: str) -> str:
        """Extract environment from DDL content or filename."""
        # Try to extract from comments
        env_match = re.search(r"-- Environment:\s*(\w+)", content, re.IGNORECASE)
        if env_match:
            return env_match.group(1).lower()
        
        # Check filename for environment indicators
        filename = os.path.basename(file_path).lower()
        if 'dev' in filename:
            return 'development'
        elif 'prod' in filename:
            return 'production'
        elif 'test' in filename:
            return 'test'
        
        return 'development'  # Default

    def _parse_tables(self, content: str) -> Dict[str, Dict[str, Any]]:
        """Parse table definitions from DDL content."""
        tables = {}
        
        # Find all CREATE TABLE statements - improved pattern
        table_pattern = r"CREATE\s+TABLE\s+(\w+)\s*\((.*?)\);"
        table_matches = re.finditer(table_pattern, content, re.DOTALL | re.IGNORECASE)
        
        for match in table_matches:
            table_name = match.group(1)
            table_body = match.group(2)
            
            # Parse columns
            columns = self._parse_columns(table_body)
            
            # Parse table constraints
            table_constraints = self._parse_table_constraints(table_body)
            
            # Only add if we have valid columns
            if columns:
                tables[table_name] = {
                    'schema': 'public',
                    'description': f"Table {table_name}",
                    'columns': columns,
                    'constraints': table_constraints
                }
        
        return tables

    def _parse_columns(self, table_body: str) -> List[Dict[str, Any]]:
        """Parse column definitions from table body."""
        columns = []
        
        # Improved column parsing - split by comma but handle nested parentheses
        # First, remove comments
        clean_body = re.sub(r'--.*$', '', table_body, flags=re.MULTILINE)
        
        # Split by comma, but be careful with nested parentheses
        parts = []
        current_part = ""
        paren_count = 0
        
        for char in clean_body:
            if char == '(':
                paren_count += 1
            elif char == ')':
                paren_count -= 1
            elif char == ',' and paren_count == 0:
                parts.append(current_part.strip())
                current_part = ""
                continue
            current_part += char
        
        if current_part.strip():
            parts.append(current_part.strip())
        
        # Parse each part as a potential column
        for part in parts:
            if not part:
                continue
            column_info = self._parse_single_column(part)
            if column_info:
                columns.append(column_info)
        
        return columns

    def _parse_single_column(self, column_def: str) -> Optional[Dict[str, Any]]:
        """Parse a single column definition."""
        if not column_def or column_def.startswith('CONSTRAINT') or column_def.startswith('PRIMARY KEY'):
            return None
            
        # Extract column name - more robust pattern
        name_match = re.match(r"(\w+)", column_def.strip())
        if not name_match:
            return None
            
        column_name = name_match.group(1)
        
        # Skip if this looks like a constraint or other non-column definition
        if column_name.upper() in ['CONSTRAINT', 'PRIMARY', 'FOREIGN', 'CHECK', 'UNIQUE']:
            return None
        
        # Extract data type - look for the word after column name
        # Pattern: column_name DATA_TYPE (with optional parameters)
        type_pattern = r"^\s*\w+\s+(\w+(?:\([^)]*\))?(?:\s+WITH\s+TIME\s+ZONE)?)"
        type_match = re.search(type_pattern, column_def.strip())
        if not type_match:
            return None
            
        data_type = type_match.group(1)
        
        # Extract constraints
        nullable = 'NOT NULL' not in column_def.upper()
        unique = 'UNIQUE' in column_def.upper()
        primary_key = 'PRIMARY KEY' in column_def.upper()
        
        # Extract default value - improved pattern
        default_pattern = r"DEFAULT\s+([^,\s]+(?:\s+[^,\s]+)*)"
        default_match = re.search(default_pattern, column_def, re.IGNORECASE)
        default_value = default_match.group(1).strip() if default_match else ""
        
        # Extract constraints list
        constraints = []
        if 'NOT NULL' in column_def.upper():
            constraints.append('NOT NULL')
        if 'UNIQUE' in column_def.upper():
            constraints.append('UNIQUE')
        if 'PRIMARY KEY' in column_def.upper():
            constraints.append('PRIMARY KEY')
        
        return {
            'name': column_name,
            'data_type': data_type,
            'nullable': nullable,
            'unique': unique,
            'primary_key': primary_key,
            'default_value': default_value,
            'constraints': constraints,
            'description': f"Column {column_name} of type {data_type}"
        }

    def _parse_table_constraints(self, table_body: str) -> List[Dict[str, Any]]:
        """Parse table-level constraints."""
        constraints = []
        
        # Find CONSTRAINT definitions
        constraint_pattern = r"CONSTRAINT\s+(\w+)\s+([^,]+)"
        constraint_matches = re.finditer(constraint_pattern, table_body, re.IGNORECASE)
        
        for match in constraint_matches:
            constraint_name = match.group(1)
            constraint_def = match.group(2).strip()
            
            constraint_type = self._determine_constraint_type(constraint_def)
            
            constraints.append({
                'name': constraint_name,
                'type': constraint_type,
                'definition': constraint_def,
                'description': f"Constraint {constraint_name}"
            })
        
        return constraints

    def _determine_constraint_type(self, constraint_def: str) -> str:
        """Determine the type of constraint based on its definition."""
        constraint_def_upper = constraint_def.upper()
        
        if 'CHECK' in constraint_def_upper:
            return 'CHECK'
        elif 'FOREIGN KEY' in constraint_def_upper:
            return 'FOREIGN KEY'
        elif 'UNIQUE' in constraint_def_upper:
            return 'UNIQUE'
        elif 'PRIMARY KEY' in constraint_def_upper:
            return 'PRIMARY KEY'
        else:
            return 'OTHER'

    def _parse_indexes(self, content: str) -> Dict[str, List[Dict[str, Any]]]:
        """Parse index definitions from DDL content."""
        indexes = {}
        
        # Find all CREATE INDEX statements
        index_pattern = r"CREATE\s+(?:UNIQUE\s+)?INDEX\s+(\w+)\s+ON\s+(\w+)\s*\(([^)]+)\)"
        index_matches = re.finditer(index_pattern, content, re.IGNORECASE)
        
        for match in index_matches:
            index_name = match.group(1)
            table_name = match.group(2)
            columns_str = match.group(3)
            
            # Parse columns
            columns = [col.strip() for col in columns_str.split(',')]
            
            # Determine index type
            index_type = 'UNIQUE' if 'UNIQUE' in match.group(0).upper() else 'B-tree'
            
            if table_name not in indexes:
                indexes[table_name] = []
            
            indexes[table_name].append({
                'name': index_name,
                'type': index_type,
                'columns': columns,
                'description': f"Index {index_name} on {table_name}"
            })
        
        return indexes

    def _parse_constraints(self, content: str) -> Dict[str, List[Dict[str, Any]]]:
        """Parse constraint definitions from DDL content."""
        constraints = {}
        
        # Find all ALTER TABLE ADD CONSTRAINT statements
        constraint_pattern = r"ALTER\s+TABLE\s+(\w+)\s+ADD\s+CONSTRAINT\s+(\w+)\s+([^;]+)"
        constraint_matches = re.finditer(constraint_pattern, content, re.IGNORECASE)
        
        for match in constraint_matches:
            table_name = match.group(1)
            constraint_name = match.group(2)
            constraint_def = match.group(3).strip()
            
            constraint_type = self._determine_constraint_type(constraint_def)
            
            if table_name not in constraints:
                constraints[table_name] = []
            
            constraints[table_name].append({
                'name': constraint_name,
                'type': constraint_type,
                'definition': constraint_def,
                'description': f"Constraint {constraint_name} on {table_name}"
            })
        
        # Also parse inline constraints from CREATE TABLE statements
        table_pattern = r"CREATE\s+TABLE\s+(\w+)\s*\((.*?)\);"
        table_matches = re.finditer(table_pattern, content, re.DOTALL | re.IGNORECASE)
        
        for match in table_matches:
            table_name = match.group(1)
            table_body = match.group(2)
            
            # Find inline constraints
            inline_constraints = self._parse_inline_constraints(table_body, table_name)
            if inline_constraints:
                if table_name not in constraints:
                    constraints[table_name] = []
                constraints[table_name].extend(inline_constraints)
        
        return constraints

    def _parse_inline_constraints(self, table_body: str, table_name: str) -> List[Dict[str, Any]]:
        """Parse inline constraints from table body."""
        constraints = []
        
        # Find CONSTRAINT definitions within table body
        constraint_pattern = r"CONSTRAINT\s+(\w+)\s+([^,]+)"
        constraint_matches = re.finditer(constraint_pattern, table_body, re.IGNORECASE)
        
        for match in constraint_matches:
            constraint_name = match.group(1)
            constraint_def = match.group(2).strip()
            
            constraint_type = self._determine_constraint_type(constraint_def)
            
            constraints.append({
                'name': constraint_name,
                'type': constraint_type,
                'definition': constraint_def,
                'description': f"Constraint {constraint_name} on {table_name}"
            })
        
        return constraints

    def parse_ddl_directory(self, directory_path: str, project_name: str) -> List[Dict[str, Any]]:
        """
        Parse all DDL files in a directory.
        
        Args:
            directory_path: Path to the directory containing DDL files
            project_name: Name of the project
            
        Returns:
            List of database objects from all DDL files
        """
        all_objects = []
        
        if not os.path.exists(directory_path):
            self.logger.error(f"Directory {directory_path} does not exist")
            return all_objects
        
        # Find all .sql files in the directory
        sql_files = [f for f in os.listdir(directory_path) if f.endswith('.sql')]
        
        if not sql_files:
            self.logger.warning(f"No .sql files found in {directory_path}")
            return all_objects
        
        for sql_file in sql_files:
            file_path = os.path.join(directory_path, sql_file)
            try:
                self.logger.info(f"Parsing DDL file: {sql_file}")
                db_objects = self.parse_ddl_file(file_path, project_name)
                all_objects.append(db_objects)
            except Exception as e:
                self.logger.error(f"Error parsing {sql_file}: {str(e)}")
                continue
        
        return all_objects
