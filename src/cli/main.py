import click
import sys
import os
from dotenv import load_dotenv

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.services.java_parser import parse_java_project
from src.services.graph_db import GraphDB
from src.services.sequence_diagram_generator import SequenceDiagramGenerator
from src.services.db_parser import DBParser
from neo4j import GraphDatabase
import subprocess
import tempfile

load_dotenv()

def convert_to_image(diagram_content, output_file, image_format, width, height):
    """Convert Mermaid diagram to image using mermaid-cli"""
    # Try different possible locations for mmdc
    mmdc_commands = ['mmdc', 'mmdc.cmd', r'C:\Users\cjony\AppData\Roaming\npm\mmdc', r'C:\Users\cjony\AppData\Roaming\npm\mmdc.cmd']
    
    mmdc_cmd = None
    for cmd in mmdc_commands:
        try:
            subprocess.run([cmd, '--version'], capture_output=True, check=True, timeout=5)
            mmdc_cmd = cmd
            break
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            continue
    
    if not mmdc_cmd:
        click.echo("Error: mermaid-cli is not installed or not found in PATH.")
        click.echo("Please install it with: npm install -g @mermaid-js/mermaid-cli")
        click.echo("Or check if it's installed at: C:\\Users\\cjony\\AppData\\Roaming\\npm\\")
        return
    
    try:
        # Create temporary file for mermaid content
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8', newline='') as temp_file:
            temp_file.write(diagram_content)
            temp_file_path = temp_file.name
        
        # Determine format from output file extension
        file_extension = output_file.split('.')[-1].lower()
        actual_format = file_extension if file_extension in ['png', 'svg', 'pdf'] else image_format
        
        # Convert to image using mermaid-cli
        cmd = [
            mmdc_cmd,
            '-i', temp_file_path,
            '-o', output_file,
            '-e', actual_format,
            '-w', str(width),
            '-H', str(height)
        ]
        
        # Add PDF-specific options
        if image_format.lower() == 'pdf':
            # Set background color for PDF
            cmd.extend(['-b', 'white'])
            # Add PDF fit option
            cmd.append('-f')
        
        click.echo(f"Running command: {' '.join(cmd)}")
        
        # Set environment variables for UTF-8 encoding
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        env['LANG'] = 'en_US.UTF-8'
        env['LC_ALL'] = 'en_US.UTF-8'
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, encoding='utf-8', errors='ignore', env=env)
        
        # Clean up temporary file
        os.unlink(temp_file_path)
        
        # Check if the expected output file was created
        if os.path.exists(output_file):
            actual_format = output_file.split('.')[-1].upper()
            click.echo(f"Image saved to: {output_file}")
            click.echo(f"Format: {actual_format}, Size: {width}x{height}")
        else:
            # Check for files with similar names (mermaid-cli sometimes adds numbers)
            import glob
            pattern = output_file.replace('.pdf', '-*.pdf').replace('.png', '-*.png').replace('.svg', '-*.svg')
            matching_files = glob.glob(pattern)
            if matching_files:
                actual_file = matching_files[0]
                actual_format = actual_file.split('.')[-1].upper()
                click.echo(f"Image saved to: {actual_file}")
                click.echo(f"Format: {actual_format}, Size: {width}x{height}")
                click.echo(f"Note: mermaid-cli created {actual_file} instead of {output_file}")
            else:
                click.echo(f"Warning: Expected file {output_file} not found")
        
        click.echo(f"Command output: {result.stdout}")
        
    except subprocess.CalledProcessError as e:
        click.echo(f"Error converting to image: {e}")
        click.echo(f"Error output: {e.stderr}")
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
    except Exception as e:
        click.echo(f"Unexpected error: {e}")
        if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)

@click.group()
def cli():
    pass

@cli.command()
@click.option('--java-source-folder', default=os.getenv("JAVA_SOURCE_FOLDER"), help='Path to the Java source project folder.')
@click.option('--neo4j-uri', default=os.getenv("NEO4J_URI", "bolt://localhost:7687"), help='Neo4j URI')
@click.option('--neo4j-user', default=os.getenv("NEO4J_USER", "neo4j"), help='Neo4j username')
@click.option('--neo4j-password', default=os.getenv("NEO4J_PASSWORD"), help='Neo4j password')
@click.option('--clean', is_flag=True, help='Wipe the database before analysis.')
@click.option('--class-name', help='Analyze only a specific class (delete existing data for this class first)')
@click.option('--update', is_flag=True, help='Update all classes individually without clearing database')
@click.option('--db_object', is_flag=True, help='Analyze database objects from DDL scripts')
@click.option('--java_object', is_flag=True, help='Analyze Java objects from source code')
@click.option('--dry-run', is_flag=True, help='Parse Java files without connecting to database.')
def analyze(java_source_folder, neo4j_uri, neo4j_user, neo4j_password, clean, class_name, update, db_object, java_object, dry_run):
    """Analyzes a Java project and populates a Neo4j database."""
    if not java_source_folder:
        click.echo("Error: JAVA_SOURCE_FOLDER environment variable or --java-source-folder option is required.", err=True)
        exit(1)

    # Extract project name from directory path
    from pathlib import Path
    project_name = Path(java_source_folder).resolve().name

    # Handle Java object analysis
    if java_object:
        click.echo("Analyzing Java objects from source code...")
        
        if not java_source_folder:
            click.echo("Error: JAVA_SOURCE_FOLDER environment variable is required for --java_object option.", err=True)
            click.echo("Please set JAVA_SOURCE_FOLDER in your .env file or environment variables.")
            exit(1)
        
        if not os.path.exists(java_source_folder):
            click.echo(f"Error: Java source folder {java_source_folder} does not exist.", err=True)
            exit(1)
        
        try:
            # Parse Java project
            click.echo(f"Parsing Java project at: {java_source_folder}")
            packages_to_add, classes_to_add, class_to_package_map, beans, dependencies, endpoints, mybatis_mappers, jpa_entities, config_files, test_classes, sql_statements, project_name = parse_java_project(java_source_folder)
            
            click.echo(f"Project name: {project_name}")
            click.echo(f"Found {len(packages_to_add)} packages and {len(classes_to_add)} classes.")
            
            if dry_run:
                click.echo("Dry run mode - not connecting to database.")
                click.echo(f"Found {len(packages_to_add)} packages and {len(classes_to_add)} classes.")
                click.echo(f"Found {len(beans)} Spring Beans and {len(dependencies)} dependencies.")
                click.echo(f"Found {len(endpoints)} REST API endpoints.")
                click.echo(f"Found {len(mybatis_mappers)} MyBatis mappers.")
                click.echo(f"Found {len(jpa_entities)} JPA entities.")
                click.echo(f"Found {len(config_files)} configuration files.")
                click.echo(f"Found {len(test_classes)} test classes.")
                click.echo(f"Found {len(sql_statements)} SQL statements.")
                click.echo("Java object analysis complete (dry run).")
                return
            
            # Connect to database
            click.echo(f"Connecting to Neo4j at {neo4j_uri}...")
            db = GraphDB(uri=neo4j_uri, user=neo4j_user, password=neo4j_password)
            
            if clean:
                click.echo("Cleaning Java objects...")
                with db._driver.session() as session:
                    # Delete only Java-related nodes
                    session.run("MATCH (n:Package) DETACH DELETE n")
                    session.run("MATCH (n:Class) DETACH DELETE n")
                    session.run("MATCH (n:Method) DETACH DELETE n")
                    session.run("MATCH (n:Field) DETACH DELETE n")
                    session.run("MATCH (n:Bean) DETACH DELETE n")
                    session.run("MATCH (n:Endpoint) DETACH DELETE n")
                    session.run("MATCH (n:MyBatisMapper) DETACH DELETE n")
                    session.run("MATCH (n:JpaEntity) DETACH DELETE n")
                    session.run("MATCH (n:ConfigFile) DETACH DELETE n")
                    session.run("MATCH (n:TestClass) DETACH DELETE n")
                    session.run("MATCH (n:SqlStatement) DETACH DELETE n")
            
            # Add packages
            click.echo("Adding packages to database...")
            for package_node in packages_to_add:
                db.add_package(package_node, project_name)
            
            # Add classes
            click.echo("Adding classes to database...")
            for class_node in classes_to_add:
                # Find the package for this class using the mapping
                class_key = f"{class_to_package_map.get(class_node.name, '')}.{class_node.name}"
                package_name = class_to_package_map.get(class_key, None)
                
                if not package_name:
                    # Fallback: try to find package by class name
                    for key, pkg_name in class_to_package_map.items():
                        if key.endswith(f".{class_node.name}"):
                            package_name = pkg_name
                            break
                
                db.add_class(class_node, package_name, project_name)
            
            # Add Spring Boot analysis results
            if beans:
                click.echo(f"Adding {len(beans)} Spring Beans to database...")
                for bean in beans:
                    db.add_bean(bean, project_name)
            
            if dependencies:
                click.echo(f"Adding {len(dependencies)} Bean dependencies to database...")
                for dependency in dependencies:
                    db.add_bean_dependency(dependency, project_name)
            
            if endpoints:
                click.echo(f"Adding {len(endpoints)} REST API endpoints to database...")
                for endpoint in endpoints:
                    db.add_endpoint(endpoint, project_name)
            
            if mybatis_mappers:
                click.echo(f"Adding {len(mybatis_mappers)} MyBatis mappers to database...")
                for mapper in mybatis_mappers:
                    db.add_mybatis_mapper(mapper, project_name)
            
            if jpa_entities:
                click.echo(f"Adding {len(jpa_entities)} JPA entities to database...")
                for entity in jpa_entities:
                    db.add_jpa_entity(entity, project_name)
            
            if config_files:
                click.echo(f"Adding {len(config_files)} configuration files to database...")
                for config_file in config_files:
                    db.add_config_file(config_file, project_name)
            
            if test_classes:
                click.echo(f"Adding {len(test_classes)} test classes to database...")
                for test_class in test_classes:
                    db.add_test_class(test_class, project_name)
            
            if sql_statements:
                click.echo(f"Adding {len(sql_statements)} SQL statements to database...")
                for sql_statement in sql_statements:
                    db.add_sql_statement(sql_statement, project_name)
                    # Create relationship between mapper and SQL statement
                    with db._driver.session() as session:
                        session.execute_write(db._create_mapper_sql_relationship_tx, sql_statement.mapper_name, sql_statement.id, project_name)
            
            db.close()
            click.echo("Java object analysis complete.")
            return
            
        except Exception as e:
            click.echo(f"Error analyzing Java objects: {e}")
            click.echo("Use --dry-run flag to parse without database connection.")
            exit(1)

    # Handle DB object analysis
    if db_object:
        click.echo("Analyzing database objects from DDL scripts...")
        
        # Get DB script folder from environment variable
        db_script_folder = os.getenv("DB_SCRIPT_FOLDER")
        if not db_script_folder:
            click.echo("Error: DB_SCRIPT_FOLDER environment variable is required for --db_object option.", err=True)
            click.echo("Please set DB_SCRIPT_FOLDER in your .env file or environment variables.")
            exit(1)
        
        if not os.path.exists(db_script_folder):
            click.echo(f"Error: DB script folder {db_script_folder} does not exist.", err=True)
            exit(1)
        
        try:
            # Parse DDL files
            db_parser = DBParser()
            all_db_objects = db_parser.parse_ddl_directory(db_script_folder, project_name)
            
            if not all_db_objects:
                click.echo("No DDL files found or parsed successfully.")
                return
            
            click.echo(f"Found {len(all_db_objects)} DDL files to process.")
            
            if dry_run:
                click.echo("Dry run mode - not connecting to database.")
                for i, db_objects in enumerate(all_db_objects):
                    click.echo(f"DDL file {i+1}:")
                    click.echo(f"  Database: {db_objects['database'].name}")
                    click.echo(f"  Tables: {len(db_objects['tables'])}")
                    click.echo(f"  Columns: {len(db_objects['columns'])}")
                    click.echo(f"  Indexes: {len(db_objects['indexes'])}")
                    click.echo(f"  Constraints: {len(db_objects['constraints'])}")
                click.echo("DB object analysis complete (dry run).")
                return
            
            # Connect to database
            click.echo(f"Connecting to Neo4j at {neo4j_uri}...")
            db = GraphDB(uri=neo4j_uri, user=neo4j_user, password=neo4j_password)
            
            if clean:
                click.echo("Cleaning database objects...")
                with db._driver.session() as session:
                    # Delete only database-related nodes
                    session.run("MATCH (n:Database) DETACH DELETE n")
                    session.run("MATCH (n:Table) DETACH DELETE n")
                    session.run("MATCH (n:Column) DETACH DELETE n")
                    session.run("MATCH (n:Index) DETACH DELETE n")
                    session.run("MATCH (n:Constraint) DETACH DELETE n")
            
            # Process each DDL file's objects
            for i, db_objects in enumerate(all_db_objects):
                click.echo(f"Processing DDL file {i+1}...")
                
                # Add database
                click.echo(f"Adding database: {db_objects['database'].name}")
                db.add_database(db_objects['database'], project_name)
                
                # Add tables
                for table_obj in db_objects['tables']:
                    click.echo(f"Adding table: {table_obj.name}")
                    db.add_table(table_obj, db_objects['database'].name, project_name)
                
                # Add columns
                for column_obj in db_objects['columns']:
                    table_name = getattr(column_obj, 'table_name', 'unknown')
                    click.echo(f"Adding column: {column_obj.name} to table {table_name}")
                    db.add_column(column_obj, table_name, project_name)
                
                # Add indexes
                for index_obj, table_name in db_objects['indexes']:
                    click.echo(f"Adding index: {index_obj.name} to table {table_name}")
                    db.add_index(index_obj, table_name, project_name)
                
                # Add constraints
                for constraint_obj, table_name in db_objects['constraints']:
                    click.echo(f"Adding constraint: {constraint_obj.name} to table {table_name}")
                    db.add_constraint(constraint_obj, table_name, project_name)
            
            db.close()
            click.echo("DB object analysis complete.")
            return
            
        except Exception as e:
            click.echo(f"Error analyzing DB objects: {e}")
            click.echo("Use --dry-run flag to parse without database connection.")
            exit(1)

    # If analyzing a specific class
    if class_name:
        click.echo(f"Analyzing specific class: {class_name}")
        
        # Find the Java file for this class
        java_file_path = None
        for root, _, files in os.walk(java_source_folder):
            for file in files:
                if file.endswith(".java") and file.replace(".java", "") == class_name:
                    java_file_path = os.path.join(root, file)
                    break
            if java_file_path:
                break
        
        if not java_file_path:
            click.echo(f"Error: Could not find Java file for class '{class_name}'", err=True)
            exit(1)
        
        click.echo(f"Found Java file: {java_file_path}")
        
        try:
            # Parse the single Java file
            from src.services.java_parser import parse_single_java_file, extract_beans_from_classes, analyze_bean_dependencies, extract_endpoints_from_classes, extract_mybatis_mappers_from_classes, extract_jpa_entities_from_classes, extract_test_classes_from_classes, extract_sql_statements_from_mappers
            
            package_node, class_node, package_name = parse_single_java_file(java_file_path, project_name)
            
            click.echo(f"Parsed class: {class_node.name}")
            click.echo(f"Package: {package_name}")
            click.echo(f"Methods: {len(class_node.methods)}")
            click.echo(f"Properties: {len(class_node.properties)}")
            click.echo(f"Method calls: {len(class_node.calls)}")
            
            if dry_run:
                click.echo("Dry run mode - not connecting to database.")
                click.echo("Analysis complete (dry run).")
                return
            
            # Connect to database
            click.echo(f"Connecting to Neo4j at {neo4j_uri}...")
            db = GraphDB(uri=neo4j_uri, user=neo4j_user, password=neo4j_password)
            
            # Delete existing data for this class
            click.echo(f"Deleting existing data for class '{class_name}'...")
            db.delete_class_and_related_data(class_name, project_name)
            
            # Add package
            click.echo("Adding package to database...")
            db.add_package(package_node, project_name)
            
            # Add class
            click.echo("Adding class to database...")
            db.add_class(class_node, package_name, project_name)
            
            # Extract and add related Spring Boot analysis results for this class only
            classes_list = [class_node]
            beans = extract_beans_from_classes(classes_list)
            dependencies = analyze_bean_dependencies(classes_list, beans)
            endpoints = extract_endpoints_from_classes(classes_list)
            mybatis_mappers = extract_mybatis_mappers_from_classes(classes_list)
            jpa_entities = extract_jpa_entities_from_classes(classes_list)
            test_classes = extract_test_classes_from_classes(classes_list)
            
            # Extract SQL statements from MyBatis mappers
            sql_statements = extract_sql_statements_from_mappers(mybatis_mappers, project_name)
            
            # Add Spring Boot analysis results
            if beans:
                click.echo(f"Adding {len(beans)} Spring Beans to database...")
                for bean in beans:
                    db.add_bean(bean, project_name)
            
            if dependencies:
                click.echo(f"Adding {len(dependencies)} Bean dependencies to database...")
                for dependency in dependencies:
                    db.add_bean_dependency(dependency, project_name)
            
            if endpoints:
                click.echo(f"Adding {len(endpoints)} REST API endpoints to database...")
                for endpoint in endpoints:
                    db.add_endpoint(endpoint, project_name)
            
            if mybatis_mappers:
                click.echo(f"Adding {len(mybatis_mappers)} MyBatis mappers to database...")
                for mapper in mybatis_mappers:
                    db.add_mybatis_mapper(mapper, project_name)
            
            if jpa_entities:
                click.echo(f"Adding {len(jpa_entities)} JPA entities to database...")
                for entity in jpa_entities:
                    db.add_jpa_entity(entity, project_name)
            
            if test_classes:
                click.echo(f"Adding {len(test_classes)} test classes to database...")
                for test_class in test_classes:
                    db.add_test_class(test_class, project_name)
            
            if sql_statements:
                click.echo(f"Adding {len(sql_statements)} SQL statements to database...")
                for sql_statement in sql_statements:
                    db.add_sql_statement(sql_statement, project_name)
                    # Create relationship between mapper and SQL statement
                    with db._driver.session() as session:
                        session.execute_write(db._create_mapper_sql_relationship_tx, sql_statement.mapper_name, sql_statement.id, project_name)
            
            db.close()
            click.echo("Class analysis complete.")
            
        except Exception as e:
            click.echo(f"Error analyzing class: {e}")
            click.echo("Use --dry-run flag to parse without database connection.")
            exit(1)
        
        return

    # If updating all classes individually
    if update:
        click.echo("Updating all classes individually...")
        
        # Find all Java files
        java_files = []
        for root, _, files in os.walk(java_source_folder):
            for file in files:
                if file.endswith(".java"):
                    java_files.append(os.path.join(root, file))
        
        if not java_files:
            click.echo("No Java files found in the specified directory.", err=True)
            exit(1)
        
        click.echo(f"Found {len(java_files)} Java files to process.")
        
        if dry_run:
            click.echo("Dry run mode - not connecting to database.")
            for java_file in java_files:
                try:
                    from src.services.java_parser import parse_single_java_file
                    package_node, class_node, package_name = parse_single_java_file(java_file, project_name)
                    click.echo(f"  {class_node.name} ({package_name}) - Methods: {len(class_node.methods)}, Properties: {len(class_node.properties)}")
                except Exception as e:
                    click.echo(f"  Error parsing {java_file}: {e}")
            click.echo("Update analysis complete (dry run).")
            return
        
        try:
            # Connect to database
            click.echo(f"Connecting to Neo4j at {neo4j_uri}...")
            db = GraphDB(uri=neo4j_uri, user=neo4j_user, password=neo4j_password)
            
            processed_count = 0
            error_count = 0
            
            for java_file in java_files:
                try:
                    click.echo(f"Processing: {java_file}")
                    
                    # Parse the single Java file
                    from src.services.java_parser import parse_single_java_file, extract_beans_from_classes, analyze_bean_dependencies, extract_endpoints_from_classes, extract_mybatis_mappers_from_classes, extract_jpa_entities_from_classes, extract_test_classes_from_classes, extract_sql_statements_from_mappers
                    
                    package_node, class_node, package_name = parse_single_java_file(java_file, project_name)
                    
                    click.echo(f"  Parsed class: {class_node.name} (Package: {package_name})")
                    
                    # Delete existing data for this class
                    click.echo(f"  Deleting existing data for class '{class_node.name}'...")
                    db.delete_class_and_related_data(class_node.name, project_name)
                    
                    # Add package
                    db.add_package(package_node, project_name)
                    
                    # Add class
                    db.add_class(class_node, package_name, project_name)
                    
                    # Extract and add related Spring Boot analysis results for this class only
                    classes_list = [class_node]
                    beans = extract_beans_from_classes(classes_list)
                    dependencies = analyze_bean_dependencies(classes_list, beans)
                    endpoints = extract_endpoints_from_classes(classes_list)
                    mybatis_mappers = extract_mybatis_mappers_from_classes(classes_list)
                    jpa_entities = extract_jpa_entities_from_classes(classes_list)
                    test_classes = extract_test_classes_from_classes(classes_list)
                    
                    # Extract SQL statements from MyBatis mappers
                    sql_statements = extract_sql_statements_from_mappers(mybatis_mappers, project_name)
                    
                    # Add Spring Boot analysis results
                    if beans:
                        for bean in beans:
                            db.add_bean(bean, project_name)
                    
                    if dependencies:
                        for dependency in dependencies:
                            db.add_bean_dependency(dependency, project_name)
                    
                    if endpoints:
                        for endpoint in endpoints:
                            db.add_endpoint(endpoint, project_name)
                    
                    if mybatis_mappers:
                        for mapper in mybatis_mappers:
                            db.add_mybatis_mapper(mapper, project_name)
                    
                    if jpa_entities:
                        for entity in jpa_entities:
                            db.add_jpa_entity(entity, project_name)
                    
                    if test_classes:
                        for test_class in test_classes:
                            db.add_test_class(test_class, project_name)
                    
                    if sql_statements:
                        for sql_statement in sql_statements:
                            db.add_sql_statement(sql_statement, project_name)
                            # Create relationship between mapper and SQL statement
                            with db._driver.session() as session:
                                session.execute_write(db._create_mapper_sql_relationship_tx, sql_statement.mapper_name, sql_statement.id, project_name)
                    
                    processed_count += 1
                    click.echo(f"  [OK] Successfully processed {class_node.name}")
                    
                except Exception as e:
                    error_count += 1
                    click.echo(f"  [ERROR] Error processing {java_file}: {e}")
                    continue
            
            db.close()
            click.echo(f"Update complete. Processed: {processed_count}, Errors: {error_count}")
            
        except Exception as e:
            click.echo(f"Error during update: {e}")
            click.echo("Use --dry-run flag to parse without database connection.")
            exit(1)
        
        return

    # Original full project analysis (when no specific object type is specified)
    if not java_object and not db_object:
        click.echo(f"Parsing Java project at: {java_source_folder}")
        packages_to_add, classes_to_add, class_to_package_map, beans, dependencies, endpoints, mybatis_mappers, jpa_entities, config_files, test_classes, sql_statements, project_name = parse_java_project(java_source_folder)
    
        click.echo(f"Project name: {project_name}")
        
        click.echo(f"Found {len(packages_to_add)} packages and {len(classes_to_add)} classes.")
        
        if dry_run:
            click.echo("Dry run mode - not connecting to database.")
            click.echo(f"Found {len(packages_to_add)} packages and {len(classes_to_add)} classes.")
            click.echo(f"Found {len(beans)} Spring Beans and {len(dependencies)} dependencies.")
            click.echo(f"Found {len(endpoints)} REST API endpoints.")
            click.echo(f"Found {len(mybatis_mappers)} MyBatis mappers.")
            click.echo(f"Found {len(jpa_entities)} JPA entities.")
            click.echo(f"Found {len(config_files)} configuration files.")
            click.echo(f"Found {len(test_classes)} test classes.")
            click.echo(f"Found {len(sql_statements)} SQL statements.")
            
            for package_node in packages_to_add:
                click.echo(f"Package: {package_node.name}")
            for class_node in classes_to_add:
                click.echo(f"Class: {class_node.name}")
                click.echo(f"  Methods: {len(class_node.methods)}")
                click.echo(f"  Properties: {len(class_node.properties)}")
                click.echo(f"  Method calls: {len(class_node.calls)}")
            click.echo("Analysis complete (dry run).")
            return

        try:
            click.echo(f"Connecting to Neo4j at {neo4j_uri}...")
            db = GraphDB(uri=neo4j_uri, user=neo4j_user, password=neo4j_password)

            if clean:
                click.echo("Cleaning database...")
                with db._driver.session() as session:
                    session.run("MATCH (n) DETACH DELETE n")

            click.echo("Adding packages to database...")
            for package_node in packages_to_add:
                db.add_package(package_node, project_name)
        
            click.echo("Adding classes to database...")
            for class_node in classes_to_add:
                # Find the package for this class using the mapping
                class_key = f"{class_to_package_map.get(class_node.name, '')}.{class_node.name}"
                package_name = class_to_package_map.get(class_key, None)
                
                if not package_name:
                    # Fallback: try to find package by class name
                    for key, pkg_name in class_to_package_map.items():
                        if key.endswith(f".{class_node.name}"):
                            package_name = pkg_name
                            break
                
                db.add_class(class_node, package_name, project_name)
        
            # Add Spring Boot analysis results
            if beans:
                click.echo(f"Adding {len(beans)} Spring Beans to database...")
                for bean in beans:
                    db.add_bean(bean, project_name)
        
            if dependencies:
                click.echo(f"Adding {len(dependencies)} Bean dependencies to database...")
                for dependency in dependencies:
                    db.add_bean_dependency(dependency, project_name)
        
            if endpoints:
                click.echo(f"Adding {len(endpoints)} REST API endpoints to database...")
                for endpoint in endpoints:
                    db.add_endpoint(endpoint, project_name)
        
            if mybatis_mappers:
                click.echo(f"Adding {len(mybatis_mappers)} MyBatis mappers to database...")
                for mapper in mybatis_mappers:
                    db.add_mybatis_mapper(mapper, project_name)
        
            if jpa_entities:
                click.echo(f"Adding {len(jpa_entities)} JPA entities to database...")
                for entity in jpa_entities:
                    db.add_jpa_entity(entity, project_name)
        
            if config_files:
                click.echo(f"Adding {len(config_files)} configuration files to database...")
                for config_file in config_files:
                    db.add_config_file(config_file, project_name)
        
            if test_classes:
                click.echo(f"Adding {len(test_classes)} test classes to database...")
                for test_class in test_classes:
                    db.add_test_class(test_class, project_name)
        
            if sql_statements:
                click.echo(f"Adding {len(sql_statements)} SQL statements to database...")
                for sql_statement in sql_statements:
                    db.add_sql_statement(sql_statement, project_name)
                    # Create relationship between mapper and SQL statement
                    with db._driver.session() as session:
                        session.execute_write(db._create_mapper_sql_relationship_tx, sql_statement.mapper_name, sql_statement.id, project_name)
        
            db.close()
            click.echo("Analysis complete.")
        except Exception as e:
            click.echo(f"Error connecting to database: {e}")
            click.echo("Use --dry-run flag to parse without database connection.")
            exit(1)

@cli.command()
@click.option('--neo4j-uri', default=os.getenv("NEO4J_URI", "bolt://localhost:7687"), help='Neo4j URI')
@click.option('--neo4j-user', default=os.getenv("NEO4J_USER", "neo4j"), help='Neo4j username')
@click.option('--neo4j-password', default=os.getenv("NEO4J_PASSWORD"), help='Neo4j password')
@click.option('--query', help='Custom Cypher query to execute')
@click.option('--basic', is_flag=True, help='Run basic class query')
@click.option('--detailed', is_flag=True, help='Run detailed class query with methods and properties')
@click.option('--inheritance', is_flag=True, help='Run inheritance relationship query')
@click.option('--package', is_flag=True, help='Run package-based class query')
def query(neo4j_uri, neo4j_user, neo4j_password, query, basic, detailed, inheritance, package):
    """Execute queries against the Neo4j database."""
    
    # 미리 정의된 쿼리들
    queries = {
        'basic': """
        MATCH (c:Class)
        RETURN 
            c.name AS name,
            c.logical_name AS logical_name,
            c.file_path AS file_path,
            c.type AS type,
            c.source AS source
        ORDER BY c.name
        """,
        'detailed': """
        MATCH (c:Class)
        OPTIONAL MATCH (c)-[:HAS_METHOD]->(m:Method)
        OPTIONAL MATCH (c)-[:HAS_FIELD]->(p:Field)
        OPTIONAL MATCH (pkg:Package)-[:CONTAINS]->(c)
        RETURN 
            c.name AS class_name,
            c.logical_name AS class_logical_name,
            c.file_path AS file_path,
            c.type AS class_type,
            pkg.name AS package_name,
            collect(DISTINCT m.name) AS methods,
            collect(DISTINCT p.name) AS properties
        ORDER BY c.name
        """,
        'inheritance': """
        MATCH (c:Class)
        OPTIONAL MATCH (c)-[:EXTENDS]->(super:Class)
        OPTIONAL MATCH (c)-[:IMPLEMENTS]->(impl:Class)
        RETURN 
            c.name AS class_name,
            c.logical_name AS class_logical_name,
            c.type AS class_type,
            collect(DISTINCT super.name) AS extends,
            collect(DISTINCT impl.name) AS implements
        ORDER BY c.name
        """,
        'package': """
        MATCH (pkg:Package)-[:CONTAINS]->(c:Class)
        OPTIONAL MATCH (c)-[:HAS_METHOD]->(m:Method)
        OPTIONAL MATCH (c)-[:HAS_FIELD]->(p:Field)
        RETURN 
            pkg.name AS package_name,
            pkg.logical_name AS package_logical_name,
            collect(DISTINCT c.name) AS classes,
            count(DISTINCT m) AS total_methods,
            count(DISTINCT p) AS total_properties
        ORDER BY pkg.name
        """
    }
    
    # 실행할 쿼리 결정
    if query:
        cypher_query = query
        description = "Custom Query"
    elif basic:
        cypher_query = queries['basic']
        description = "Basic Class Query"
    elif detailed:
        cypher_query = queries['detailed']
        description = "Detailed Class Query"
    elif inheritance:
        cypher_query = queries['inheritance']
        description = "Inheritance Query"
    elif package:
        cypher_query = queries['package']
        description = "Package Query"
    else:
        click.echo("Error: Please specify a query type or provide a custom query.")
        click.echo("Available options: --basic, --detailed, --inheritance, --package, or --query")
        return
    
    try:
        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        
        with driver.session() as session:
            click.echo(f"Executing: {description}")
            click.echo("=" * 50)
            
            result = session.run(cypher_query)
            records = list(result)
            
            if not records:
                click.echo("No results found.")
                return
            
            # 첫 번째 레코드의 키들을 헤더로 사용
            headers = list(records[0].keys())
            
            # 헤더 출력
            click.echo(" | ".join(f"{header:20}" for header in headers))
            click.echo("-" * (len(headers) * 23))
            
            # 데이터 출력
            for record in records:
                row = []
                for header in headers:
                    value = record[header]
                    if value is None:
                        row.append("None")
                    elif isinstance(value, (list, dict)):
                        row.append(str(value)[:50] + "..." if len(str(value)) > 50 else str(value))
                    else:
                        row.append(str(value)[:20])
                click.echo(" | ".join(f"{cell:20}" for cell in row))
            
            click.echo(f"\nTotal: {len(records)} results found.")
            
    except Exception as e:
        click.echo(f"Error executing query: {e}")
    finally:
        driver.close()

@cli.command()
@click.option('--neo4j-uri', default=os.getenv("NEO4J_URI", "bolt://localhost:7687"), help='Neo4j URI')
@click.option('--neo4j-user', default=os.getenv("NEO4J_USER", "neo4j"), help='Neo4j username')
@click.option('--class-name', required=True, help='Name of the class to analyze')
@click.option('--method-name', help='Specific method to analyze (optional)')
@click.option('--max-depth', default=3, help='Maximum depth of call chain to follow (default: 3)')
@click.option('--include-external', is_flag=True, help='Include calls to external libraries')
@click.option('--method-focused', is_flag=True, help='Generate method-focused diagram (shows only the specified method and its direct calls)')
@click.option('--output-file', help='Output file to save the diagram (optional)')
@click.option('--output-image', help='Output image file (PNG/SVG/PDF) - requires mermaid-cli')
@click.option('--image-format', default='png', type=click.Choice(['png', 'svg', 'pdf']), help='Image format (default: png)')
@click.option('--image-width', default=1200, help='Image width in pixels (default: 1200)')
@click.option('--image-height', default=800, help='Image height in pixels (default: 800)')
def sequence(neo4j_uri, neo4j_user, class_name, method_name, max_depth, include_external, method_focused, output_file, output_image, image_format, image_width, image_height):
    """Generate sequence diagram for a specific class and optionally a method."""
    
    try:
        neo4j_password = os.getenv("NEO4J_PASSWORD")
        if not neo4j_password:
            click.echo("Error: NEO4J_PASSWORD environment variable is not set.")
            click.echo("Please set NEO4J_PASSWORD in your .env file or environment variables.")
            exit(1)
        
        click.echo(f"Connecting to Neo4j at {neo4j_uri}...")
        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        generator = SequenceDiagramGenerator(driver)
        
        # Generate the sequence diagram
        click.echo(f"Generating sequence diagram for class: {class_name}")
        if method_name:
            click.echo(f"Focusing on method: {method_name}")
        if method_focused:
            click.echo("Method-focused mode: showing only direct calls from the specified method")
        
        diagram = generator.generate_sequence_diagram(
            class_name=class_name,
            method_name=method_name,
            max_depth=max_depth if not method_focused else 1,  # Method-focused uses depth 1
            include_external_calls=include_external,
            method_focused=method_focused
        )
        
        click.echo(f"Diagram generated (length: {len(diagram)})")
        
        # Check if diagram contains error message
        if diagram.startswith("Error:"):
            click.echo(f"Error: {diagram}")
            return
        
        # Output the diagram
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(diagram)
            click.echo(f"Sequence diagram saved to: {output_file}")
        else:
            # Default: save to {class_name}.md
            default_filename = f"{class_name}.md"
            with open(default_filename, 'w', encoding='utf-8') as f:
                f.write(diagram)
            click.echo(f"Sequence diagram saved to: {default_filename}")
            
            click.echo("\n" + "="*50)
            click.echo("SEQUENCE DIAGRAM")
            click.echo("="*50)
            click.echo(diagram)
            click.echo("="*50)
        
        # Convert to image if requested
        if output_image:
            convert_to_image(diagram, output_image, image_format, image_width, image_height)
        
    except Exception as e:
        click.echo(f"Error generating sequence diagram: {e}")
        import traceback
        click.echo(f"Traceback: {traceback.format_exc()}")
        exit(1)
    finally:
        if 'driver' in locals():
            driver.close()

@cli.command()
@click.option('--neo4j-uri', default=os.getenv("NEO4J_URI", "bolt://localhost:7687"), help='Neo4j URI')
@click.option('--neo4j-user', default=os.getenv("NEO4J_USER", "neo4j"), help='Neo4j username')
def list_classes(neo4j_uri, neo4j_user):
    """List all available classes in the database."""
    
    try:
        neo4j_password = os.getenv("NEO4J_PASSWORD")
        if not neo4j_password:
            click.echo("Error: NEO4J_PASSWORD environment variable is not set.")
            click.echo("Please set NEO4J_PASSWORD in your .env file or environment variables.")
            exit(1)
        
        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        generator = SequenceDiagramGenerator(driver)
        
        classes = generator.get_available_classes()
        
        if not classes:
            click.echo("No classes found in the database.")
            return
        
        click.echo("Available classes:")
        click.echo("=" * 80)
        click.echo(f"{'Class Name':<30} {'Package':<30} {'Type':<10}")
        click.echo("-" * 80)
        
        for cls in classes:
            click.echo(f"{cls['name']:<30} {cls['package_name']:<30} {cls['type']:<10}")
        
        click.echo(f"\nTotal: {len(classes)} classes found.")
        
    except Exception as e:
        click.echo(f"Error listing classes: {e}")
        exit(1)
    finally:
        driver.close()

@cli.command()
@click.option('--neo4j-uri', default=os.getenv("NEO4J_URI", "bolt://localhost:7687"), help='Neo4j URI')
@click.option('--neo4j-user', default=os.getenv("NEO4J_USER", "neo4j"), help='Neo4j username')
@click.option('--class-name', required=True, help='Name of the class to list methods for')
def list_methods(neo4j_uri, neo4j_user, class_name):
    """List all methods for a specific class."""
    
    try:
        neo4j_password = os.getenv("NEO4J_PASSWORD")
        if not neo4j_password:
            click.echo("Error: NEO4J_PASSWORD environment variable is not set.")
            click.echo("Please set NEO4J_PASSWORD in your .env file or environment variables.")
            exit(1)
        
        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        generator = SequenceDiagramGenerator(driver)
        
        methods = generator.get_class_methods(class_name)
        
        if not methods:
            click.echo(f"No methods found for class '{class_name}'.")
            return
        
        click.echo(f"Methods for class '{class_name}':")
        click.echo("=" * 80)
        click.echo(f"{'Method Name':<30} {'Return Type':<20} {'Logical Name':<30}")
        click.echo("-" * 80)
        
        for method in methods:
            click.echo(f"{method['name']:<30} {method['return_type']:<20} {method['logical_name']:<30}")
        
        click.echo(f"\nTotal: {len(methods)} methods found.")
        
    except Exception as e:
        click.echo(f"Error listing methods: {e}")
        exit(1)
    finally:
        driver.close()

@cli.command()
@click.option('--neo4j-uri', default=os.getenv("NEO4J_URI", "bolt://localhost:7687"), help='Neo4j URI')
@click.option('--neo4j-user', default=os.getenv("NEO4J_USER", "neo4j"), help='Neo4j username')
@click.option('--project-name', help='Project name to filter by (optional)')
def crud_matrix(neo4j_uri, neo4j_user, project_name):
    """Show CRUD matrix for classes and tables."""
    
    try:
        neo4j_password = os.getenv("NEO4J_PASSWORD")
        if not neo4j_password:
            click.echo("Error: NEO4J_PASSWORD environment variable is not set.")
            click.echo("Please set NEO4J_PASSWORD in your .env file or environment variables.")
            exit(1)
        
        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        db = GraphDB(neo4j_uri, neo4j_user, neo4j_password)
        
        click.echo("CRUD Matrix - Class to Table Operations")
        click.echo("=" * 80)
        
        matrix = db.get_crud_matrix(project_name)
        
        if not matrix:
            click.echo("No CRUD operations found.")
            return
        
        click.echo(f"{'Class Name':<30} {'Package':<25} {'Tables':<20} {'Operations':<15}")
        click.echo("-" * 80)
        
        for row in matrix:
            class_name = row['class_name']
            package_name = row['package_name'] or 'N/A'
            tables = ', '.join(row['tables']) if row['tables'] else 'None'
            operations = ', '.join(row['operations']) if row['operations'] else 'None'
            
            click.echo(f"{class_name:<30} {package_name:<25} {tables:<20} {operations:<15}")
        
        click.echo(f"\nTotal: {len(matrix)} classes with CRUD operations.")
        
    except Exception as e:
        click.echo(f"Error getting CRUD matrix: {e}")
        exit(1)
    finally:
        driver.close()

@cli.command()
@click.option('--neo4j-uri', default=os.getenv("NEO4J_URI", "bolt://localhost:7687"), help='Neo4j URI')
@click.option('--neo4j-user', default=os.getenv("NEO4J_USER", "neo4j"), help='Neo4j username')
@click.option('--project-name', help='Project name to filter by (optional)')
def table_summary(neo4j_uri, neo4j_user, project_name):
    """Show CRUD summary for each table."""
    
    try:
        neo4j_password = os.getenv("NEO4J_PASSWORD")
        if not neo4j_password:
            click.echo("Error: NEO4J_PASSWORD environment variable is not set.")
            click.echo("Please set NEO4J_PASSWORD in your .env file or environment variables.")
            exit(1)
        
        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        db = GraphDB(neo4j_uri, neo4j_user, neo4j_password)
        
        click.echo("Table CRUD Summary")
        click.echo("=" * 60)
        
        summary = db.get_table_crud_summary(project_name)
        
        if not summary:
            click.echo("No tables found.")
            return
        
        for row in summary:
            table_name = row['table_name']
            operations = row['operations']
            
            click.echo(f"\nTable: {table_name}")
            click.echo("-" * 40)
            
            for op in operations:
                operation = op['operation']
                count = op['count']
                click.echo(f"  {operation}: {count} statements")
        
        click.echo(f"\nTotal: {len(summary)} tables.")
        
    except Exception as e:
        click.echo(f"Error getting table summary: {e}")
        exit(1)
    finally:
        driver.close()

if __name__ == '__main__':
    cli()
