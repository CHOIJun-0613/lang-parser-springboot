import click
import sys
import os
from datetime import datetime
from dotenv import load_dotenv

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from csa.services.java_parser import parse_java_project
from csa.services.graph_db import GraphDB
from csa.services.sequence_diagram_generator import SequenceDiagramGenerator
from csa.services.db_parser import DBParser
from csa.services.db_call_analysis import DBCallAnalysisService
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

def _save_crud_matrix_as_excel(matrix, project_name, output_path):
    """CRUD matrix 데이터를 Excel 파일로 저장"""
    try:
        import pandas as pd
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment
        
        # DataFrame 생성
        df_data = []
        for row in matrix:
            df_data.append({
                'Package': row['package_name'] or 'N/A',
                'Class Name': row['class_name'],
                'Method': row['method_name'],
                'Schema': row['schema'] or 'unknown',
                'Table': row['table_name'],
                'Operations': ', '.join(row['operations']) if row['operations'] else 'None'
            })
        
        df = pd.DataFrame(df_data)
        
        # Excel 파일 생성 및 스타일 적용
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='CRUD Matrix', index=False)
            
            # 워크시트 스타일 적용
            workbook = writer.book
            worksheet = writer.sheets['CRUD Matrix']
            
            # 헤더 스타일
            for cell in worksheet[1]:
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
                cell.alignment = Alignment(horizontal="center")
            
            # 컬럼 너비 자동 조정
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))
                worksheet.column_dimensions[column_letter].width = min(max_length + 2, 50)
        
        return True
        
    except ImportError as e:
        click.echo(f"Error: Required library not found: {e}")
        click.echo("Please install required libraries: pip install pandas openpyxl")
        return False
    except Exception as e:
        click.echo(f"Error creating Excel file: {e}")
        return False

def _save_crud_matrix_as_image(matrix, project_name, output_path, image_format):
    """CRUD matrix 데이터를 SVG/PNG 이미지로 저장 (Enhanced classDiagram 형식)"""
    try:
        # Mermaid classDiagram 형식으로 변경
        diagram_lines = ["```mermaid", "classDiagram"]
        
        # 클래스별 데이터 구조화
        class_data = {}
        for row in matrix:
            class_name = row['class_name']
            if class_name not in class_data:
                class_data[class_name] = {
                    'package_name': row['package_name'],
                    'methods': []
                }
            
            # 메서드-테이블-CRUD 정보 저장
            schema = row['schema'] if row['schema'] and row['schema'] != 'unknown' else None
            table_display = f"{schema}.{row['table_name']}" if schema else row['table_name']
            operations = ', '.join(row['operations']) if row['operations'] else 'None'
            
            class_data[class_name]['methods'].append({
                'method_name': row['method_name'],
                'table': table_display,
                'operations': operations
            })
        
        # 각 클래스에 대해 classDiagram 노드 생성
        for class_name, data in class_data.items():
            # 패키지명 정리
            package_name = data['package_name'] or 'N/A'
            clean_class_name = class_name.replace('.', '_').replace('-', '_').replace(' ', '_')
            
            # 클래스 정의 시작
            diagram_lines.append(f"    class {clean_class_name} {{")
            diagram_lines.append(f"        <<{package_name}>>")
            
            # 메서드 목록 추가 (최대 10개)
            methods = data['methods'][:10]  # 최대 10개로 제한
            for method_info in methods:
                method_line = f"        +{method_info['method_name']}() {method_info['table']} [{method_info['operations']}]"
                diagram_lines.append(method_line)
            
            # 10개 이상이면 생략 표시
            if len(data['methods']) > 10:
                diagram_lines.append(f"        ... ({len(data['methods']) - 10} more)")
            
            diagram_lines.append("    }")
        
        # 테이블 노드 생성
        table_nodes = set()
        for row in matrix:
            schema = row['schema'] if row['schema'] and row['schema'] != 'unknown' else None
            table_display = f"{schema}.{row['table_name']}" if schema else row['table_name']
            table_key = table_display.replace('.', '_').replace('-', '_').replace(' ', '_')
            
            if table_key not in table_nodes:
                diagram_lines.append(f"    class {table_key} {{")
                diagram_lines.append(f"        <<Database Table>>")
                diagram_lines.append(f"        {table_display}")
                diagram_lines.append("    }")
                table_nodes.add(table_key)
        
        # 클래스-테이블 관계 생성
        for class_name, data in class_data.items():
            clean_class_name = class_name.replace('.', '_').replace('-', '_').replace(' ', '_')
            for method_info in data['methods'][:10]:  # 최대 10개 관계만 표시
                table_key = method_info['table'].replace('.', '_').replace('-', '_').replace(' ', '_')
                diagram_lines.append(f"    {clean_class_name} --> {table_key}")
        
        diagram_lines.append("```")
        diagram = "\n".join(diagram_lines)
        
        # 이미지로 변환 (크기 증가)
        convert_to_image(diagram, output_path, image_format, 2400, 1800)
        return True
        
    except Exception as e:
        click.echo(f"Error creating image file: {e}")
        return False

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
@click.option('--db-object', 'db_object', is_flag=True, help='Analyze database objects from DDL scripts (requires DB_SCRIPT_FOLDER env var)')
@click.option('--java-object', 'java_object', is_flag=True, help='Analyze Java objects from source code (requires JAVA_SOURCE_FOLDER env var)')
@click.option('--all-objects', 'all_objects', is_flag=True, help='Analyze both Java objects and database objects (equivalent to --java-object --db-object)')
@click.option('--dry-run', is_flag=True, help='Parse Java files without connecting to database.')
@click.option('--project-name', help='Project name for analysis (overrides auto-detected project name)')
def analyze(java_source_folder, neo4j_uri, neo4j_user, neo4j_password, clean, class_name, update, db_object, java_object, all_objects, dry_run, project_name):
    """
    Analyzes Java projects and/or database objects and populates a Neo4j database.
    
    This command can analyze:
    - Java objects from source code (--java-object)
    - Database objects from DDL scripts (--db-object)
    - Specific classes (--class-name)
    - Update existing classes (--update)
    
    Examples:
      # Analyze only database objects
      python -m csa.cli.main analyze --db-object
      
      # Analyze only Java objects
      python -m csa.cli.main analyze --java-object
      
      # Analyze both database and Java objects
      python -m csa.cli.main analyze --all-objects
      
      # Alternative way to analyze both
      python -m csa.cli.main analyze --db-object --java-object
      
      # Dry run (parse without database connection)
      python -m csa.cli.main analyze --db-object --dry-run
    """
    # Handle --all-objects option
    if all_objects:
        db_object = True
        java_object = True
        click.echo("--all-objects option detected: Analyzing both Java objects and database objects")
    
    # Check if at least one analysis type is specified
    if not db_object and not java_object and not class_name and not update:
        # Default to full analysis (Java + DB) if no flags are specified
        java_object = True
        db_object = True
        click.echo("No analysis type specified. Defaulting to full analysis (Java + DB objects).")
        click.echo("Use --db-object, --java-object, --all-objects, --class-name, or --update to specify analysis type.")
    
    # Check java_source_folder requirement for Java-related operations
    if java_object or class_name or update or (not db_object):
        if not java_source_folder:
            click.echo("Error: JAVA_SOURCE_FOLDER environment variable or --java-source-folder option is required for Java object analysis.", err=True)
            exit(1)

    # Determine project name with priority:
    # 1. --project-name option (highest priority)
    # 2. parse_java_project function result (if java_object)
    # 3. Previous analysis project name or default (lowest priority)
    
    final_project_name = None
    
    # Handle Java object analysis (only when db_object is False)
    if java_object and not db_object:
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
            packages_to_add, classes_to_add, class_to_package_map, beans, dependencies, endpoints, mybatis_mappers, jpa_entities, jpa_repositories, jpa_queries, config_files, test_classes, sql_statements, detected_project_name = parse_java_project(java_source_folder)
            
            # Priority 1: Use --project-name if provided
            if project_name:
                final_project_name = project_name
                click.echo(f"Using provided project name: {final_project_name}")
            # Priority 2: Use detected project name from parse_java_project
            else:
                final_project_name = detected_project_name
                click.echo(f"Using detected project name: {final_project_name}")
            
            click.echo(f"Project name: {final_project_name}")
            click.echo(f"Found {len(packages_to_add)} packages and {len(classes_to_add)} classes.")
            
            if dry_run:
                click.echo("Dry run mode - not connecting to database.")
                click.echo(f"Found {len(packages_to_add)} packages and {len(classes_to_add)} classes.")
                click.echo(f"Found {len(beans)} Spring Beans and {len(dependencies)} dependencies.")
                click.echo(f"Found {len(endpoints)} REST API endpoints.")
                click.echo(f"Found {len(mybatis_mappers)} MyBatis mappers.")
                click.echo(f"Found {len(jpa_entities)} JPA entities.")
                click.echo(f"Found {len(jpa_repositories)} JPA repositories.")
                click.echo(f"Found {len(jpa_queries)} JPA queries.")
                click.echo(f"Found {len(config_files)} configuration files.")
                click.echo(f"Found {len(test_classes)} test classes.")
                click.echo(f"Found {len(sql_statements)} SQL statements.")
                click.echo("Java object analysis complete (dry run).")
                return
            
            # Connect to database
            click.echo(f"Connecting to Neo4j at {neo4j_uri}...")
            db = GraphDB(uri=neo4j_uri, user=neo4j_user, password=neo4j_password)
            
            # Create or update Project node
            from csa.models.graph_entities import Project
            project_node = Project(
                name=final_project_name,
                display_name=final_project_name,
                language="Java",
            )
            db.add_project(project_node)
            click.echo(f"Project node created/updated: {final_project_name}")
            
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
                db.add_package(package_node, final_project_name)
            
            # Add classes
            click.echo("Adding classes to database...")
            click.echo(f"Total classes to add: {len(classes_to_add)}")
            
            import time
            start_time = time.time()
            
            for i, class_node in enumerate(classes_to_add):
                try:
                    # Find the package for this class using the mapping
                    # class_to_package_map의 키는 "package_name.class_name" 형식
                    class_key = f"{class_node.package_name}.{class_node.name}"
                    package_name = class_to_package_map.get(class_key, class_node.package_name)
                    
                    if not package_name:
                        # Fallback: use the package_name from the class node itself
                        package_name = class_node.package_name
                    
                    class_start_time = time.time()
                    click.echo(f"Adding class {i+1}/{len(classes_to_add)}: {class_node.name} (package: {package_name})")
                    db.add_class(class_node, package_name, final_project_name)
                    
                    class_elapsed = time.time() - class_start_time
                    if class_elapsed > 1.0:  # 1초 이상 걸린 경우에만 시간 표시
                        click.echo(f"  ✓ Completed in {class_elapsed:.2f}s")
                    
                    # 10개마다 전체 진행상태 표시
                    if (i + 1) % 10 == 0:
                        elapsed = time.time() - start_time
                        remaining = (elapsed / (i + 1)) * (len(classes_to_add) - i - 1)
                        click.echo(f"  Progress: {i+1}/{len(classes_to_add)} classes processed ({elapsed:.1f}s elapsed, ~{remaining:.1f}s remaining)")
                    
                except Exception as e:
                    click.echo(f"Error adding class {class_node.name}: {e}")
                    continue
            
            total_elapsed = time.time() - start_time
            click.echo(f"✓ All {len(classes_to_add)} classes added successfully in {total_elapsed:.2f}s")
            
            # Add Spring Boot analysis results
            if beans:
                click.echo(f"Adding {len(beans)} Spring Beans to database...")
                start_time = time.time()
                for i, bean in enumerate(beans):
                    db.add_bean(bean, final_project_name)
                    if (i + 1) % 20 == 0:
                        click.echo(f"  Progress: {i+1}/{len(beans)} beans processed")
                click.echo(f"✓ Added {len(beans)} Spring Beans in {time.time() - start_time:.2f}s")
            
            if dependencies:
                click.echo(f"Adding {len(dependencies)} Bean dependencies to database...")
                start_time = time.time()
                for dependency in dependencies:
                    db.add_bean_dependency(dependency, final_project_name)
                click.echo(f"✓ Added {len(dependencies)} Bean dependencies in {time.time() - start_time:.2f}s")
            
            if endpoints:
                click.echo(f"Adding {len(endpoints)} REST API endpoints to database...")
                start_time = time.time()
                for i, endpoint in enumerate(endpoints):
                    db.add_endpoint(endpoint, final_project_name)
                    if (i + 1) % 50 == 0:
                        click.echo(f"  Progress: {i+1}/{len(endpoints)} endpoints processed")
                click.echo(f"✓ Added {len(endpoints)} REST API endpoints in {time.time() - start_time:.2f}s")
            
            if mybatis_mappers:
                click.echo(f"Adding {len(mybatis_mappers)} MyBatis mappers to database...")
                start_time = time.time()
                for mapper in mybatis_mappers:
                    db.add_mybatis_mapper(mapper, final_project_name)
                click.echo(f"✓ Added {len(mybatis_mappers)} MyBatis mappers in {time.time() - start_time:.2f}s")
            
            if jpa_entities:
                click.echo(f"Adding {len(jpa_entities)} JPA entities to database...")
                start_time = time.time()
                for entity in jpa_entities:
                    db.add_jpa_entity(entity, final_project_name)
                click.echo(f"✓ Added {len(jpa_entities)} JPA entities in {time.time() - start_time:.2f}s")
            
            if jpa_repositories:
                click.echo(f"Adding {len(jpa_repositories)} JPA repositories to database...")
                start_time = time.time()
                for repository in jpa_repositories:
                    db.add_jpa_repository(repository, final_project_name)
                click.echo(f"✓ Added {len(jpa_repositories)} JPA repositories in {time.time() - start_time:.2f}s")
            
            if jpa_queries:
                click.echo(f"Adding {len(jpa_queries)} JPA queries to database...")
                start_time = time.time()
                for i, query in enumerate(jpa_queries):
                    db.add_jpa_query(query, final_project_name)
                    if (i + 1) % 50 == 0:
                        click.echo(f"  Progress: {i+1}/{len(jpa_queries)} queries processed")
                click.echo(f"✓ Added {len(jpa_queries)} JPA queries in {time.time() - start_time:.2f}s")
            
            if config_files:
                click.echo(f"Adding {len(config_files)} configuration files to database...")
                start_time = time.time()
                for config_file in config_files:
                    db.add_config_file(config_file, final_project_name)
                click.echo(f"✓ Added {len(config_files)} configuration files in {time.time() - start_time:.2f}s")
            
            if test_classes:
                click.echo(f"Adding {len(test_classes)} test classes to database...")
                start_time = time.time()
                for test_class in test_classes:
                    db.add_test_class(test_class, final_project_name)
                click.echo(f"✓ Added {len(test_classes)} test classes in {time.time() - start_time:.2f}s")
            
            if sql_statements:
                click.echo(f"Adding {len(sql_statements)} SQL statements to database...")
                start_time = time.time()
                for i, sql_statement in enumerate(sql_statements):
                    db.add_sql_statement(sql_statement, final_project_name)
                    # Create relationship between mapper and SQL statement
                    with db._driver.session() as session:
                        session.execute_write(db._create_mapper_sql_relationship_tx, sql_statement.mapper_name, sql_statement.id, final_project_name)
                    if (i + 1) % 100 == 0:
                        click.echo(f"  Progress: {i+1}/{len(sql_statements)} SQL statements processed")
                click.echo(f"✓ Added {len(sql_statements)} SQL statements in {time.time() - start_time:.2f}s")
            
            db.close()
            click.echo("Java object analysis complete.")
            return
            
        except Exception as e:
            import traceback
            click.echo(f"Error analyzing Java objects: {e}")
            click.echo(f"\nFull traceback:")
            traceback.print_exc()
            click.echo("Use --dry-run flag to parse without database connection.")
            exit(1)

    # Handle DB object analysis (only when java_object is False)
    if db_object and not java_object:
        click.echo("Analyzing database objects from DDL scripts...")
        
        # Determine project name for DB analysis
        if not final_project_name:
            # Priority 1: Use --project-name if provided
            if project_name:
                final_project_name = project_name
                click.echo(f"Using provided project name: {final_project_name}")
            # Priority 3: Use previous analysis project name or default
            else:
                from pathlib import Path
                if java_source_folder:
                    final_project_name = Path(java_source_folder).resolve().name
                else:
                    final_project_name = os.getenv("PROJECT_NAME", "default_project")
                click.echo(f"Using fallback project name: {final_project_name}")
        
        click.echo(f"Project name: {final_project_name}")
        
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
            all_db_objects = db_parser.parse_ddl_directory(db_script_folder, None)
            
            if not all_db_objects:
                click.echo("No DDL files found or parsed successfully.")
                return
            
            click.echo(f"Found {len(all_db_objects)} DDL files to process.")
            
            # Show summary of what will be processed
            total_tables = sum(len(db_objects['tables']) for db_objects in all_db_objects)
            total_columns = sum(len(db_objects['columns']) for db_objects in all_db_objects)
            total_indexes = sum(len(db_objects['indexes']) for db_objects in all_db_objects)
            total_constraints = sum(len(db_objects['constraints']) for db_objects in all_db_objects)
            
            click.echo(f"Summary:")
            click.echo(f"  Total databases: {len(all_db_objects)}")
            click.echo(f"  Total tables: {total_tables}")
            click.echo(f"  Total columns: {total_columns}")
            click.echo(f"  Total indexes: {total_indexes}")
            click.echo(f"  Total constraints: {total_constraints}")
            
            if dry_run:
                click.echo("\nDry run mode - not connecting to database.")
                for i, db_objects in enumerate(all_db_objects):
                    click.echo(f"\nDDL file {i+1}:")
                    click.echo(f"  Database: {db_objects['database'].name}")
                    click.echo(f"  Environment: {db_objects['database'].environment}")
                    click.echo(f"  Tables: {len(db_objects['tables'])}")
                    click.echo(f"  Columns: {len(db_objects['columns'])}")
                    click.echo(f"  Indexes: {len(db_objects['indexes'])}")
                    click.echo(f"  Constraints: {len(db_objects['constraints'])}")
                click.echo("\nDB object analysis complete (dry run).")
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
                db.add_database(db_objects['database'], None)
                
                # Add tables
                for table_obj in db_objects['tables']:
                    click.echo(f"Adding table: {table_obj.name}")
                    db.add_table(table_obj, db_objects['database'].name, None)
                
                # Add columns
                for column_obj in db_objects['columns']:
                    table_name = getattr(column_obj, 'table_name', 'unknown')
                    click.echo(f"Adding column: {column_obj.name} to table {table_name}")
                    db.add_column(column_obj, table_name, None)
                
                # Add indexes
                for index_obj, table_name in db_objects['indexes']:
                    click.echo(f"Adding index: {index_obj.name} to table {table_name}")
                    db.add_index(index_obj, table_name, None)
                
                # Add constraints
                for constraint_obj, table_name in db_objects['constraints']:
                    click.echo(f"Adding constraint: {constraint_obj.name} to table {table_name}")
                    db.add_constraint(constraint_obj, table_name, None)
            
            db.close()
            click.echo(f"\nDB object analysis complete!")
            click.echo(f"Successfully processed {len(all_db_objects)} DDL files.")
            click.echo(f"Added {total_tables} tables, {total_columns} columns, {total_indexes} indexes, and {total_constraints} constraints to the database.")
            return
            
        except Exception as e:
            click.echo(f"Error analyzing DB objects: {e}")
            click.echo("Use --dry-run flag to parse without database connection.")
            exit(1)

    # If analyzing a specific class
    if class_name:
        click.echo(f"Analyzing specific class: {class_name}")
        
        # Determine project name for class analysis
        if not final_project_name:
            # Priority 1: Use --project-name if provided
            if project_name:
                final_project_name = project_name
                click.echo(f"Using provided project name: {final_project_name}")
            # Priority 3: Use previous analysis project name or default
            else:
                from pathlib import Path
                if java_source_folder:
                    final_project_name = Path(java_source_folder).resolve().name
                else:
                    final_project_name = os.getenv("PROJECT_NAME", "default_project")
                click.echo(f"Using fallback project name: {final_project_name}")
        
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
            from csa.services.java_parser import parse_single_java_file, extract_beans_from_classes, analyze_bean_dependencies, extract_endpoints_from_classes, extract_mybatis_mappers_from_classes, extract_jpa_entities_from_classes, extract_test_classes_from_classes, extract_sql_statements_from_mappers
            
            package_node, class_node, package_name = parse_single_java_file(java_file_path, final_project_name)
            
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
            db.delete_class_and_related_data(class_name, final_project_name)
            
            # Add package
            click.echo("Adding package to database...")
            db.add_package(package_node, final_project_name)
            
            # Add class
            click.echo("Adding class to database...")
            db.add_class(class_node, package_name, final_project_name)
            
            # Extract and add related Spring Boot analysis results for this class only
            classes_list = [class_node]
            beans = extract_beans_from_classes(classes_list)
            dependencies = analyze_bean_dependencies(classes_list, beans)
            endpoints = extract_endpoints_from_classes(classes_list)
            mybatis_mappers = extract_mybatis_mappers_from_classes(classes_list)
            jpa_entities = extract_jpa_entities_from_classes(classes_list)
            test_classes = extract_test_classes_from_classes(classes_list)
            
            # Extract SQL statements from MyBatis mappers
            sql_statements = extract_sql_statements_from_mappers(mybatis_mappers, final_project_name)
            
            # Add Spring Boot analysis results
            if beans:
                click.echo(f"Adding {len(beans)} Spring Beans to database...")
                for bean in beans:
                    db.add_bean(bean, final_project_name)
            
            if dependencies:
                click.echo(f"Adding {len(dependencies)} Bean dependencies to database...")
                for dependency in dependencies:
                    db.add_bean_dependency(dependency, final_project_name)
            
            if endpoints:
                click.echo(f"Adding {len(endpoints)} REST API endpoints to database...")
                for endpoint in endpoints:
                    db.add_endpoint(endpoint, final_project_name)
            
            if mybatis_mappers:
                click.echo(f"Adding {len(mybatis_mappers)} MyBatis mappers to database...")
                for mapper in mybatis_mappers:
                    db.add_mybatis_mapper(mapper, final_project_name)
            
            if jpa_entities:
                click.echo(f"Adding {len(jpa_entities)} JPA entities to database...")
                for entity in jpa_entities:
                    db.add_jpa_entity(entity, final_project_name)
            
            if test_classes:
                click.echo(f"Adding {len(test_classes)} test classes to database...")
                for test_class in test_classes:
                    db.add_test_class(test_class, final_project_name)
            
            if sql_statements:
                click.echo(f"Adding {len(sql_statements)} SQL statements to database...")
                for sql_statement in sql_statements:
                    db.add_sql_statement(sql_statement, final_project_name)
                    # Create relationship between mapper and SQL statement
                    with db._driver.session() as session:
                        session.execute_write(db._create_mapper_sql_relationship_tx, sql_statement.mapper_name, sql_statement.id, final_project_name)
            
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
        
        # Determine project name for update analysis
        if not final_project_name:
            # Priority 1: Use --project-name if provided
            if project_name:
                final_project_name = project_name
                click.echo(f"Using provided project name: {final_project_name}")
            # Priority 3: Use previous analysis project name or default
            else:
                from pathlib import Path
                if java_source_folder:
                    final_project_name = Path(java_source_folder).resolve().name
                else:
                    final_project_name = os.getenv("PROJECT_NAME", "default_project")
                click.echo(f"Using fallback project name: {final_project_name}")
        
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
                    from csa.services.java_parser import parse_single_java_file
                    package_node, class_node, package_name = parse_single_java_file(java_file, final_project_name)
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
                    from csa.services.java_parser import parse_single_java_file, extract_beans_from_classes, analyze_bean_dependencies, extract_endpoints_from_classes, extract_mybatis_mappers_from_classes, extract_jpa_entities_from_classes, extract_test_classes_from_classes, extract_sql_statements_from_mappers
                    
                    package_node, class_node, package_name = parse_single_java_file(java_file, final_project_name)
                    
                    click.echo(f"  Parsed class: {class_node.name} (Package: {package_name})")
                    
                    # Delete existing data for this class
                    click.echo(f"  Deleting existing data for class '{class_node.name}'...")
                    db.delete_class_and_related_data(class_node.name, final_project_name)
                    
                    # Add package
                    db.add_package(package_node, final_project_name)
                    
                    # Add class
                    db.add_class(class_node, package_name, final_project_name)
                    
                    # Extract and add related Spring Boot analysis results for this class only
                    classes_list = [class_node]
                    beans = extract_beans_from_classes(classes_list)
                    dependencies = analyze_bean_dependencies(classes_list, beans)
                    endpoints = extract_endpoints_from_classes(classes_list)
                    mybatis_mappers = extract_mybatis_mappers_from_classes(classes_list)
                    jpa_entities = extract_jpa_entities_from_classes(classes_list)
                    test_classes = extract_test_classes_from_classes(classes_list)
                    
                    # Extract SQL statements from MyBatis mappers
                    sql_statements = extract_sql_statements_from_mappers(mybatis_mappers, final_project_name)
                    
                    # Add Spring Boot analysis results
                    if beans:
                        for bean in beans:
                            db.add_bean(bean, final_project_name)
                    
                    if dependencies:
                        for dependency in dependencies:
                            db.add_bean_dependency(dependency, final_project_name)
                    
                    if endpoints:
                        for endpoint in endpoints:
                            db.add_endpoint(endpoint, final_project_name)
                    
                    if mybatis_mappers:
                        for mapper in mybatis_mappers:
                            db.add_mybatis_mapper(mapper, final_project_name)
                    
                    if jpa_entities:
                        for entity in jpa_entities:
                            db.add_jpa_entity(entity, final_project_name)
                    
                    if test_classes:
                        for test_class in test_classes:
                            db.add_test_class(test_class, final_project_name)
                    
                    if sql_statements:
                        for sql_statement in sql_statements:
                            db.add_sql_statement(sql_statement, final_project_name)
                            # Create relationship between mapper and SQL statement
                            with db._driver.session() as session:
                                session.execute_write(db._create_mapper_sql_relationship_tx, sql_statement.mapper_name, sql_statement.id, final_project_name)
                    
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

    # Original full project analysis (when both java_object and db_object are True)
    if java_object and db_object and not class_name and not update:
        click.echo(f"Parsing Java project at: {java_source_folder}")
        packages_to_add, classes_to_add, class_to_package_map, beans, dependencies, endpoints, mybatis_mappers, jpa_entities, jpa_repositories, jpa_queries, config_files, test_classes, sql_statements, detected_project_name = parse_java_project(java_source_folder)
    
        # Determine project name for full analysis
        if not final_project_name:
            # Priority 1: Use --project-name if provided
            if project_name:
                final_project_name = project_name
                click.echo(f"Using provided project name: {final_project_name}")
            # Priority 2: Use detected project name from parse_java_project
            else:
                final_project_name = detected_project_name
                click.echo(f"Using detected project name: {final_project_name}")
        
        click.echo(f"Project name: {final_project_name}")
        
        click.echo(f"Found {len(packages_to_add)} packages and {len(classes_to_add)} classes.")
        
        if dry_run:
            click.echo("Dry run mode - not connecting to database.")
            click.echo(f"Found {len(packages_to_add)} packages and {len(classes_to_add)} classes.")
            click.echo(f"Found {len(beans)} Spring Beans and {len(dependencies)} dependencies.")
            click.echo(f"Found {len(endpoints)} REST API endpoints.")
            click.echo(f"Found {len(mybatis_mappers)} MyBatis mappers.")
            click.echo(f"Found {len(jpa_entities)} JPA entities.")
            click.echo(f"Found {len(jpa_repositories)} JPA repositories.")
            click.echo(f"Found {len(jpa_queries)} JPA queries.")
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
            click.echo("Java object analysis complete (dry run).")
            
            # Also analyze DB objects if DB_SCRIPT_FOLDER is set
            db_script_folder = os.getenv("DB_SCRIPT_FOLDER")
            if db_script_folder and os.path.exists(db_script_folder):
                click.echo("\nAlso analyzing database objects from DDL scripts...")
                
                try:
                    db_parser = DBParser()
                    all_db_objects = db_parser.parse_ddl_directory(db_script_folder, None)
                    
                    if all_db_objects:
                        click.echo(f"Found {len(all_db_objects)} DDL files to process.")
                        
                        # Show summary of what will be processed
                        total_tables = sum(len(db_objects['tables']) for db_objects in all_db_objects)
                        total_columns = sum(len(db_objects['columns']) for db_objects in all_db_objects)
                        total_indexes = sum(len(db_objects['indexes']) for db_objects in all_db_objects)
                        total_constraints = sum(len(db_objects['constraints']) for db_objects in all_db_objects)
                        
                        click.echo(f"Summary:")
                        click.echo(f"  Total databases: {len(all_db_objects)}")
                        click.echo(f"  Total tables: {total_tables}")
                        click.echo(f"  Total columns: {total_columns}")
                        click.echo(f"  Total indexes: {total_indexes}")
                        click.echo(f"  Total constraints: {total_constraints}")
                        
                        for i, db_objects in enumerate(all_db_objects):
                            click.echo(f"\nDDL file {i+1}:")
                            click.echo(f"  Database: {db_objects['database'].name}")
                            click.echo(f"  Environment: {db_objects['database'].environment}")
                            click.echo(f"  Tables: {len(db_objects['tables'])}")
                            click.echo(f"  Columns: {len(db_objects['columns'])}")
                            click.echo(f"  Indexes: {len(db_objects['indexes'])}")
                            click.echo(f"  Constraints: {len(db_objects['constraints'])}")
                    else:
                        click.echo("No DDL files found or parsed successfully.")
                except Exception as e:
                    click.echo(f"Warning: Could not analyze DB objects: {e}")
            
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
                db.add_package(package_node, final_project_name)
        
            click.echo("Adding classes to database...")
            click.echo(f"Total classes to add: {len(classes_to_add)}")
            
            import time
            start_time = time.time()
            
            for i, class_node in enumerate(classes_to_add):
                # Find the package for this class using the mapping
                class_key = f"{class_to_package_map.get(class_node.name, '')}.{class_node.name}"
                package_name = class_to_package_map.get(class_key, None)
                
                if not package_name:
                    # Fallback: try to find package by class name
                    for key, pkg_name in class_to_package_map.items():
                        if key.endswith(f".{class_node.name}"):
                            package_name = pkg_name
                            break
                
                class_start_time = time.time()
                click.echo(f"Adding class {i+1}/{len(classes_to_add)}: {class_node.name} (package: {package_name})")
                db.add_class(class_node, package_name, final_project_name)
                
                class_elapsed = time.time() - class_start_time
                if class_elapsed > 1.0:  # 1초 이상 걸린 경우에만 시간 표시
                    click.echo(f"  ✓ Completed in {class_elapsed:.2f}s")
                
                # 10개마다 전체 진행상태 표시
                if (i + 1) % 10 == 0:
                    elapsed = time.time() - start_time
                    remaining = (elapsed / (i + 1)) * (len(classes_to_add) - i - 1)
                    click.echo(f"  Progress: {i+1}/{len(classes_to_add)} classes processed ({elapsed:.1f}s elapsed, ~{remaining:.1f}s remaining)")
            
            total_elapsed = time.time() - start_time
            click.echo(f"✓ All {len(classes_to_add)} classes added successfully in {total_elapsed:.2f}s")
        
            # Add Spring Boot analysis results
            if beans:
                click.echo(f"Adding {len(beans)} Spring Beans to database...")
                start_time = time.time()
                for i, bean in enumerate(beans):
                    db.add_bean(bean, final_project_name)
                    if (i + 1) % 20 == 0:
                        click.echo(f"  Progress: {i+1}/{len(beans)} beans processed")
                click.echo(f"✓ Added {len(beans)} Spring Beans in {time.time() - start_time:.2f}s")
        
            if dependencies:
                click.echo(f"Adding {len(dependencies)} Bean dependencies to database...")
                start_time = time.time()
                for dependency in dependencies:
                    db.add_bean_dependency(dependency, final_project_name)
                click.echo(f"✓ Added {len(dependencies)} Bean dependencies in {time.time() - start_time:.2f}s")
        
            if endpoints:
                click.echo(f"Adding {len(endpoints)} REST API endpoints to database...")
                start_time = time.time()
                for i, endpoint in enumerate(endpoints):
                    db.add_endpoint(endpoint, final_project_name)
                    if (i + 1) % 50 == 0:
                        click.echo(f"  Progress: {i+1}/{len(endpoints)} endpoints processed")
                click.echo(f"✓ Added {len(endpoints)} REST API endpoints in {time.time() - start_time:.2f}s")
        
            if mybatis_mappers:
                click.echo(f"Adding {len(mybatis_mappers)} MyBatis mappers to database...")
                start_time = time.time()
                for mapper in mybatis_mappers:
                    db.add_mybatis_mapper(mapper, final_project_name)
                click.echo(f"✓ Added {len(mybatis_mappers)} MyBatis mappers in {time.time() - start_time:.2f}s")
            
            if jpa_entities:
                click.echo(f"Adding {len(jpa_entities)} JPA entities to database...")
                start_time = time.time()
                for entity in jpa_entities:
                    db.add_jpa_entity(entity, final_project_name)
                click.echo(f"✓ Added {len(jpa_entities)} JPA entities in {time.time() - start_time:.2f}s")
            
            if jpa_repositories:
                click.echo(f"Adding {len(jpa_repositories)} JPA repositories to database...")
                start_time = time.time()
                for repository in jpa_repositories:
                    db.add_jpa_repository(repository, final_project_name)
                click.echo(f"✓ Added {len(jpa_repositories)} JPA repositories in {time.time() - start_time:.2f}s")
            
            if jpa_queries:
                click.echo(f"Adding {len(jpa_queries)} JPA queries to database...")
                start_time = time.time()
                for i, query in enumerate(jpa_queries):
                    db.add_jpa_query(query, final_project_name)
                    if (i + 1) % 50 == 0:
                        click.echo(f"  Progress: {i+1}/{len(jpa_queries)} queries processed")
                click.echo(f"✓ Added {len(jpa_queries)} JPA queries in {time.time() - start_time:.2f}s")
            
            if config_files:
                click.echo(f"Adding {len(config_files)} configuration files to database...")
                start_time = time.time()
                for config_file in config_files:
                    db.add_config_file(config_file, final_project_name)
                click.echo(f"✓ Added {len(config_files)} configuration files in {time.time() - start_time:.2f}s")
        
            if test_classes:
                click.echo(f"Adding {len(test_classes)} test classes to database...")
                start_time = time.time()
                for test_class in test_classes:
                    db.add_test_class(test_class, final_project_name)
                click.echo(f"✓ Added {len(test_classes)} test classes in {time.time() - start_time:.2f}s")
        
            if sql_statements:
                click.echo(f"Adding {len(sql_statements)} SQL statements to database...")
                start_time = time.time()
                for i, sql_statement in enumerate(sql_statements):
                    db.add_sql_statement(sql_statement, final_project_name)
                    # Create relationship between mapper and SQL statement
                    with db._driver.session() as session:
                        session.execute_write(db._create_mapper_sql_relationship_tx, sql_statement.mapper_name, sql_statement.id, final_project_name)
                    if (i + 1) % 100 == 0:
                        click.echo(f"  Progress: {i+1}/{len(sql_statements)} SQL statements processed")
                click.echo(f"✓ Added {len(sql_statements)} SQL statements in {time.time() - start_time:.2f}s")
        
            db.close()
            
            # Also analyze DB objects if DB_SCRIPT_FOLDER is set
            db_script_folder = os.getenv("DB_SCRIPT_FOLDER")
            if db_script_folder and os.path.exists(db_script_folder):
                click.echo("\nAlso analyzing database objects from DDL scripts...")
                
                try:
                    db_parser = DBParser()
                    all_db_objects = db_parser.parse_ddl_directory(db_script_folder, None)
                    
                    if all_db_objects:
                        # Reconnect to database for DB objects
                        db = GraphDB(uri=neo4j_uri, user=neo4j_user, password=neo4j_password)
                        
                        for i, db_objects in enumerate(all_db_objects):
                            click.echo(f"Processing DDL file {i+1}...")
                            db.add_database(db_objects['database'], None)
                            
                            for table_obj in db_objects['tables']:
                                db.add_table(table_obj, db_objects['database'].name, None)
                            
                            for column_obj in db_objects['columns']:
                                table_name = getattr(column_obj, 'table_name', 'unknown')
                                db.add_column(column_obj, table_name, None)
                            
                            for index_obj, table_name in db_objects['indexes']:
                                db.add_index(index_obj, table_name, None)
                            
                            for constraint_obj, table_name in db_objects['constraints']:
                                db.add_constraint(constraint_obj, table_name, None)
                        
                        db.close()
                        click.echo(f"Added {len(all_db_objects)} database schemas.")
                    else:
                        click.echo("No DDL files found or parsed successfully.")
                except Exception as e:
                    click.echo(f"Warning: Could not analyze DB objects: {e}")
            
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
@click.option('--max-depth', default=10, help='Maximum depth of call chain to follow (default: 10)')
@click.option('--include-external', is_flag=True, help='Include calls to external libraries')
@click.option('--project-name', help='Project name for database analysis (optional, will auto-detect if not provided)')
@click.option('--image-format', default='none', type=click.Choice(['none', 'png', 'svg', 'pdf']), help='Image format (default: none - no image generation)')
@click.option('--image-width', default=1200, help='Image width in pixels (default: 1200)')
@click.option('--image-height', default=800, help='Image height in pixels (default: 800)')
@click.option('--format', default='plantuml', type=click.Choice(['mermaid', 'plantuml']), help='Diagram format (default: plantuml)')
@click.option('--output-dir', default=os.getenv("SEQUENCE_DIAGRAM_OUTPUT_DIR", "output/sequence-diagram"), help='Output directory for sequence diagrams (default: output/sequence-diagram)')
def sequence(neo4j_uri, neo4j_user, class_name, method_name, max_depth, include_external, project_name, image_format, image_width, image_height, format, output_dir):
    """Generate sequence diagram for a specific class and optionally a method."""
    
    try:
        neo4j_password = os.getenv("NEO4J_PASSWORD")
        if not neo4j_password:
            click.echo("Error: NEO4J_PASSWORD environment variable is not set.")
            click.echo("Please set NEO4J_PASSWORD in your .env file or environment variables.")
            return
        
        click.echo(f"Connecting to Neo4j at {neo4j_uri}...")
        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        
        # Create generator with specified format
        generator = SequenceDiagramGenerator(driver, format=format)
        
        # Generate the sequence diagram
        click.echo(f"Generating {format} sequence diagram for class: {class_name}")
        if method_name:
            click.echo(f"Focusing on method: {method_name}")
        if project_name:
            click.echo(f"Using project: {project_name}")
        else:
            click.echo("Auto-detecting project name...")
        
        diagram = generator.generate_sequence_diagram(
            class_name=class_name,
            method_name=method_name,
            max_depth=max_depth,
            include_external_calls=include_external,
            project_name=project_name,
            output_dir=output_dir,
            image_format=image_format,
            image_width=image_width,
            image_height=image_height
        )
        
        # Check if diagram contains error message
        if isinstance(diagram, str) and diagram.startswith("Error:"):
            click.echo(f"Error: {diagram}")
            return
        
        # Handle different return types
        if isinstance(diagram, dict):
            if diagram.get("type") == "class":
                click.echo(f"Generated {len(diagram['files'])} sequence diagram files for class '{class_name}':")
                click.echo("")
                
                for file_info in diagram['files']:
                    click.echo(f"- Diagram: {os.path.basename(file_info['diagram_path'])}")
                    if file_info['image_path']:
                        click.echo(f"  Image: {os.path.basename(file_info['image_path'])}")
                
                click.echo(f"\nFiles saved in: {diagram['output_dir']}/ directory")
                
            elif diagram.get("type") == "method":
                click.echo(f"Generated sequence diagram for method '{method_name}':")
                click.echo(f"- Diagram: {os.path.basename(diagram['diagram_path'])}")
                if diagram['image_path']:
                    click.echo(f"- Image: {os.path.basename(diagram['image_path'])}")
        else:
            # Fallback for string return (should not happen with new implementation)
            click.echo(f"Diagram generated (length: {len(diagram)})")
            click.echo(diagram)
        
    except Exception as e:
        click.echo(f"Error generating sequence diagram: {e}")
        import traceback
        click.echo(f"Traceback: {traceback.format_exc()}")
        return
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
            return
        
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
            package_name = cls.get('package_name') or 'N/A'
            class_type = cls.get('type') or 'N/A'
            click.echo(f"{cls['name']:<30} {package_name:<30} {class_type:<10}")
        
        click.echo(f"\nTotal: {len(classes)} classes found.")
        
    except Exception as e:
        click.echo(f"Error listing classes: {e}")
        return
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
            return
        
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
        return
    finally:
        driver.close()

@cli.command()
@click.option('--neo4j-uri', default=os.getenv("NEO4J_URI", "bolt://localhost:7687"), help='Neo4j URI')
@click.option('--neo4j-user', default=os.getenv("NEO4J_USER", "neo4j"), help='Neo4j username')
@click.option('--project-name', help='Project name to filter by (optional)')
@click.option('--output-format', type=click.Choice(['excel', 'svg', 'png'], case_sensitive=False), 
              help='Additional output format: excel (*.xlsx), svg (*.svg), or png (*.png)')
@click.option('--auto-create-relationships', is_flag=True, default=True, help='Automatically create Method-SqlStatement relationships if needed (default: True)')
def crud_matrix(neo4j_uri, neo4j_user, project_name, output_format, auto_create_relationships):
    """Show CRUD matrix for classes and tables."""
    
    try:
        neo4j_password = os.getenv("NEO4J_PASSWORD")
        if not neo4j_password:
            click.echo("Error: NEO4J_PASSWORD environment variable is not set.")
            click.echo("Please set NEO4J_PASSWORD in your .env file or environment variables.")
            return
        
        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        db = GraphDB(neo4j_uri, neo4j_user, neo4j_password)
        
        click.echo("CRUD Matrix - Class to Table Operations")
        click.echo("=" * 80)
        
        # 먼저 CRUD 매트릭스 확인
        matrix = db.get_crud_matrix(project_name)
        
        # CRUD 매트릭스가 없고 자동 생성 옵션이 활성화된 경우 관계 생성
        if not matrix and auto_create_relationships:
            click.echo("No CRUD operations found. Creating Method-SqlStatement relationships...")
            relationships_created = db.create_method_sql_relationships(project_name)
            if relationships_created:
                click.echo(f"Created {relationships_created} Method-SqlStatement relationships.")
                # 관계 생성 후 다시 CRUD 매트릭스 확인
                matrix = db.get_crud_matrix(project_name)
            else:
                click.echo("No relationships could be created.")
        
        if not matrix:
            click.echo("No CRUD operations found.")
            if not auto_create_relationships:
                click.echo("Tip: Use --auto-create-relationships flag to automatically create Method-SqlStatement relationships.")
            return
        
        click.echo(f"{'Package':<35} {'Class Name':<30} {'Method':<25} {'Schema':<10} {'Table':<20} {'Operations':<15}")
        click.echo("-" * 135)
        
        for row in matrix:
            package_name = row['package_name'] or 'N/A'
            class_name = row['class_name']
            method_name = row['method_name']
            schema = row['schema'] or 'unknown'
            table_name = row['table_name']
            operations = ', '.join(row['operations']) if row['operations'] else 'None'
            
            click.echo(f"{package_name:<35} {class_name:<30} {method_name:<25} {schema:<10} {table_name:<20} {operations:<15}")
        
        click.echo(f"\nTotal: {len(matrix)} class-table relationships.")
        
        # 출력 디렉토리 및 타임스탬프 준비
        output_dir = os.getenv("CRUD_MATRIX_OUTPUT_DIR", "./output/crud-matrix")
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        
        # 마크다운 파일 생성 (항상 실행)
        md_filename = f"CRUD_{project_name}_{timestamp}.md"
        md_filepath = os.path.join(output_dir, md_filename)
        
        # 마크다운 내용 생성
        markdown_content = f"# CRUD Matrix [Project : {project_name}]\n\n"
        markdown_content += f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        markdown_content += "| Package | Class Name | Method | Schema | Table | Operations |\n"
        markdown_content += "|---------|------------|--------|--------|-------|------------|\n"
        
        for row in matrix:
            package_name = row['package_name'] or 'N/A'
            class_name = row['class_name']
            method_name = row['method_name']
            schema = row['schema'] or 'unknown'
            table_name = row['table_name']
            operations = ', '.join(row['operations']) if row['operations'] else 'None'
            
            markdown_content += f"| {package_name} | {class_name} | {method_name} | {schema} | {table_name} | {operations} |\n"
        
        markdown_content += f"\n**Total:** {len(matrix)} class-table relationships.\n"
        
        # 마크다운 파일 저장
        with open(md_filepath, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        click.echo(f"\nCRUD matrix (Markdown) saved to: {md_filepath}")
        
        # 추가 형식 파일 생성 (output_format이 지정된 경우)
        if output_format:
            if output_format.lower() == 'excel':
                excel_filename = f"CRUD_{project_name}_{timestamp}.xlsx"
                excel_filepath = os.path.join(output_dir, excel_filename)
                success = _save_crud_matrix_as_excel(matrix, project_name, excel_filepath)
                if success:
                    click.echo(f"CRUD matrix (Excel) saved to: {excel_filepath}")
                else:
                    click.echo("Failed to generate Excel file. Check logs for details.")
            
            elif output_format.lower() in ['svg', 'png']:
                image_filename = f"CRUD_{project_name}_{timestamp}.{output_format.lower()}"
                image_filepath = os.path.join(output_dir, image_filename)
                success = _save_crud_matrix_as_image(matrix, project_name, image_filepath, output_format.lower())
                if success:
                    click.echo(f"CRUD matrix ({output_format.upper()}) saved to: {image_filepath}")
                else:
                    click.echo(f"Failed to generate {output_format.upper()} file. Check logs for details.")
        
    except Exception as e:
        click.echo(f"Error getting CRUD matrix: {e}")
        return
    finally:
        driver.close()

@cli.command()
@click.option('--neo4j-uri', default=os.getenv("NEO4J_URI", "bolt://localhost:7687"), help='Neo4j URI')
@click.option('--neo4j-user', default=os.getenv("NEO4J_USER", "neo4j"), help='Neo4j username')
@click.option('--project-name', help='Project name to filter by (optional)')
@click.option('--auto-create-relationships', is_flag=True, default=True, help='Automatically create Method-SqlStatement relationships if needed (default: True)')
def db_analysis(neo4j_uri, neo4j_user, project_name, auto_create_relationships):
    """Show database call relationship analysis."""
    
    try:
        neo4j_password = os.getenv("NEO4J_PASSWORD")
        if not neo4j_password:
            click.echo("Error: NEO4J_PASSWORD environment variable is not set.")
            click.echo("Please set NEO4J_PASSWORD in your .env file or environment variables.")
            return
        
        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        db = GraphDB(neo4j_uri, neo4j_user, neo4j_password)
        
        click.echo("Database Call Relationship Analysis")
        click.echo("=" * 80)
        
        # 먼저 SQL 문 통계 확인
        sql_stats = db.get_sql_statistics(project_name)
        
        # 통계가 없고 자동 생성 옵션이 활성화된 경우 관계 생성
        if not sql_stats and auto_create_relationships:
            click.echo("No SQL statistics found. Creating Method-SqlStatement relationships...")
            relationships_created = db.create_method_sql_relationships(project_name)
            if relationships_created:
                click.echo(f"Created {relationships_created} Method-SqlStatement relationships.")
                # 관계 생성 후 다시 SQL 통계 확인
                sql_stats = db.get_sql_statistics(project_name)
            else:
                click.echo("No relationships could be created.")
        if sql_stats:
            click.echo(f"\nSQL Statistics:")
            click.echo(f"  Total SQL statements: {sql_stats['total_sql']}")
            click.echo(f"  SELECT statements: {sql_stats.get('SELECT', 0)}")
            click.echo(f"  INSERT statements: {sql_stats.get('INSERT', 0)}")
            click.echo(f"  UPDATE statements: {sql_stats.get('UPDATE', 0)}")
            click.echo(f"  DELETE statements: {sql_stats.get('DELETE', 0)}")
        
        # 테이블 사용 통계
        table_stats = db.get_table_usage_statistics(project_name)
        if table_stats:
            click.echo(f"\nTable Usage Statistics:")
            click.echo(f"{'Table Name':<30} {'Access Count':<15} {'Operations':<20}")
            click.echo("-" * 65)
            for table in table_stats:
                table_name = table['table_name']
                access_count = table['access_count']
                operations = ', '.join(table['operations'])
                click.echo(f"{table_name:<30} {access_count:<15} {operations:<20}")
        
        # 복잡도 분석
        complexity_stats = db.get_sql_complexity_statistics(project_name)
        if complexity_stats:
            click.echo(f"\nSQL Complexity Analysis:")
            click.echo(f"  Simple queries: {complexity_stats.get('simple', 0)}")
            click.echo(f"  Medium queries: {complexity_stats.get('medium', 0)}")
            click.echo(f"  Complex queries: {complexity_stats.get('complex', 0)}")
            click.echo(f"  Very complex queries: {complexity_stats.get('very_complex', 0)}")
        
        # 매퍼별 SQL 분포
        mapper_stats = db.get_mapper_sql_distribution(project_name)
        if mapper_stats:
            click.echo(f"\nMapper SQL Distribution:")
            click.echo(f"{'Mapper Name':<30} {'SQL Count':<15} {'SQL Types':<20}")
            click.echo("-" * 65)
            for mapper in mapper_stats:
                mapper_name = mapper['mapper_name']
                sql_count = mapper['sql_count']
                sql_types = ', '.join(mapper['sql_types'])
                click.echo(f"{mapper_name:<30} {sql_count:<15} {sql_types:<20}")
        
    except Exception as e:
        click.echo(f"Error getting database analysis: {e}")
        return
    finally:
        driver.close()

@cli.command()
@click.option('--neo4j-uri', default=os.getenv("NEO4J_URI", "bolt://localhost:7687"), help='Neo4j URI')
@click.option('--neo4j-user', default=os.getenv("NEO4J_USER", "neo4j"), help='Neo4j username')
@click.option('--project-name', help='Project name to filter by (optional)')
@click.option('--auto-create-relationships', is_flag=True, default=True, help='Automatically create Method-SqlStatement relationships if needed (default: True)')
def table_summary(neo4j_uri, neo4j_user, project_name, auto_create_relationships):
    """Show CRUD summary for each table."""
    
    try:
        neo4j_password = os.getenv("NEO4J_PASSWORD")
        if not neo4j_password:
            click.echo("Error: NEO4J_PASSWORD environment variable is not set.")
            click.echo("Please set NEO4J_PASSWORD in your .env file or environment variables.")
            return
        
        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        db = GraphDB(neo4j_uri, neo4j_user, neo4j_password)
        
        click.echo("Table CRUD Summary")
        click.echo("=" * 60)
        
        # 먼저 테이블 요약 확인
        summary = db.get_table_crud_summary(project_name)
        
        # 요약이 없고 자동 생성 옵션이 활성화된 경우 관계 생성
        if not summary and auto_create_relationships:
            click.echo("No table CRUD operations found. Creating Method-SqlStatement relationships...")
            relationships_created = db.create_method_sql_relationships(project_name)
            if relationships_created:
                click.echo(f"Created {relationships_created} Method-SqlStatement relationships.")
                # 관계 생성 후 다시 테이블 요약 확인
                summary = db.get_table_crud_summary(project_name)
            else:
                click.echo("No relationships could be created.")
        
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
        return
    finally:
        driver.close()

@cli.command()
@click.option('--neo4j-uri', default=os.getenv("NEO4J_URI", "bolt://localhost:7687"), help='Neo4j URI')
@click.option('--neo4j-user', default=os.getenv("NEO4J_USER", "neo4j"), help='Neo4j username')
@click.option('--project-name', required=True, help='Project name to analyze')
@click.option('--start-class', help='Starting class for call chain analysis (optional)')
@click.option('--start-method', help='Starting method for call chain analysis (optional)')
@click.option('--output-file', help='Output file to save the analysis results (optional)')
@click.option('--auto-create-relationships', is_flag=True, default=True, help='Automatically create Method-SqlStatement relationships if needed (default: True)')
def db_call_chain(neo4j_uri, neo4j_user, project_name, start_class, start_method, output_file, auto_create_relationships):
    """Analyze database call chain relationships."""
    
    try:
        neo4j_password = os.getenv("NEO4J_PASSWORD")
        if not neo4j_password:
            click.echo("Error: NEO4J_PASSWORD environment variable is not set.")
            click.echo("Please set NEO4J_PASSWORD in your .env file or environment variables.")
            return
        
        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        analysis_service = DBCallAnalysisService(driver)
        
        click.echo("Database Call Chain Analysis")
        click.echo("=" * 50)
        
        if start_class and start_method:
            click.echo(f"Analyzing call chain from {start_class}.{start_method}")
        elif start_class:
            click.echo(f"Analyzing call chain from class {start_class}")
        else:
            click.echo(f"Analyzing call chain for project {project_name}")
        
        # 먼저 분석 실행
        result = analysis_service.analyze_call_chain(project_name, start_class, start_method)
        
        # 분석 결과가 없고 자동 생성 옵션이 활성화된 경우 관계 생성
        if auto_create_relationships and ('error' in result or not result.get('call_chain')):
            click.echo("No call chain analysis found. Creating Method-SqlStatement relationships...")
            graph_db = GraphDB(neo4j_uri, neo4j_user, neo4j_password)
            relationships_created = graph_db.create_method_sql_relationships(project_name)
            if relationships_created:
                click.echo(f"Created {relationships_created} Method-SqlStatement relationships.")
                # 관계 생성 후 다시 분석 실행
                result = analysis_service.analyze_call_chain(project_name, start_class, start_method)
            else:
                click.echo("No relationships could be created.")
        
        if 'error' in result:
            click.echo(f"Error: {result['error']}")
            return
        
        # 결과 출력
        call_chain = result['call_chain']
        missing_nodes = result['missing_nodes']
        summary = result['analysis_summary']
        
        click.echo(f"\nAnalysis Summary:")
        click.echo(f"  Total calls: {summary['total_calls']}")
        click.echo(f"  Unique classes: {summary['unique_classes']}")
        click.echo(f"  Unique methods: {summary['unique_methods']}")
        click.echo(f"  Unique SQL statements: {summary['unique_sql_statements']}")
        click.echo(f"  Unique tables: {summary['unique_tables']}")
        click.echo(f"  Unique columns: {summary['unique_columns']}")
        click.echo(f"  Missing tables: {summary['missing_tables_count']}")
        click.echo(f"  Missing columns: {summary['missing_columns_count']}")
        
        if missing_nodes['missing_tables']:
            click.echo(f"\nMissing Tables (❌):")
            for table in missing_nodes['missing_tables']:
                click.echo(f"  - {table}")
        
        if missing_nodes['missing_columns']:
            click.echo(f"\nMissing Columns (❌):")
            for column in missing_nodes['missing_columns']:
                click.echo(f"  - {column}")
        
        # 호출 체인 상세 정보
        if call_chain:
            click.echo(f"\nCall Chain Details:")
            click.echo("-" * 80)
            click.echo(f"{'Source':<25} {'Target':<25} {'SQL Type':<10} {'Table':<20}")
            click.echo("-" * 80)
            
            for call in call_chain[:20]:  # 처음 20개만 표시
                source = f"{call['source_class']}.{call['source_method']}" if call['source_method'] else call['source_class']
                target = f"{call['target_class']}.{call['target_method']}" if call['target_method'] else call['target_class']
                sql_type = call['sql_type'] or 'N/A'
                table = call['table_name'] or 'N/A'
                
                click.echo(f"{source:<25} {target:<25} {sql_type:<10} {table:<20}")
            
            if len(call_chain) > 20:
                click.echo(f"... and {len(call_chain) - 20} more calls")
        
        # 파일로 저장
        if output_file:
            import json
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            click.echo(f"\nAnalysis results saved to: {output_file}")
        
    except Exception as e:
        click.echo(f"Error analyzing call chain: {e}")
        return
    finally:
        driver.close()

@cli.command()
@click.option('--neo4j-uri', default=os.getenv("NEO4J_URI", "bolt://localhost:7687"), help='Neo4j URI')
@click.option('--neo4j-user', default=os.getenv("NEO4J_USER", "neo4j"), help='Neo4j username')
@click.option('--project-name', required=True, help='Project name to analyze')
@click.option('--output-file', help='Output file to save the CRUD matrix (optional)')
@click.option('--output-excel', help='Output Excel file to save the CRUD matrix (optional)')
@click.option('--auto-create-relationships', is_flag=True, default=True, help='Automatically create Method-SqlStatement relationships if needed (default: True)')
def crud_analysis(neo4j_uri, neo4j_user, project_name, output_file, output_excel, auto_create_relationships):
    """Generate CRUD matrix analysis."""
    
    try:
        neo4j_password = os.getenv("NEO4J_PASSWORD")
        if not neo4j_password:
            click.echo("Error: NEO4J_PASSWORD environment variable is not set.")
            click.echo("Please set NEO4J_PASSWORD in your .env file or environment variables.")
            return
        
        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        analysis_service = DBCallAnalysisService(driver)
        
        click.echo("CRUD Matrix Analysis (SQL 호출 클래스만)")
        click.echo("=" * 50)
        
        # 먼저 CRUD 매트릭스 생성 시도
        result = analysis_service.generate_crud_table_matrix(project_name)
        
        # CRUD 매트릭스가 없고 자동 생성 옵션이 활성화된 경우 관계 생성
        if auto_create_relationships and ('error' in result or not result.get('table_matrix')):
            click.echo("No CRUD operations found. Creating Method-SqlStatement relationships...")
            graph_db = GraphDB(neo4j_uri, neo4j_user, neo4j_password)
            relationships_created = graph_db.create_method_sql_relationships(project_name)
            if relationships_created:
                click.echo(f"Created {relationships_created} Method-SqlStatement relationships.")
                # 관계 생성 후 다시 CRUD 매트릭스 생성
                result = analysis_service.generate_crud_table_matrix(project_name)
            else:
                click.echo("No relationships could be created.")
        
        if 'error' in result:
            click.echo(f"Error: {result['error']}")
            return
        
        table_matrix = result['table_matrix']
        class_names = result['class_names']
        table_names = result['table_names']
        summary = result['summary']
        
        click.echo(f"\nCRUD Summary:")
        click.echo(f"  Total classes: {summary['total_classes']}")
        click.echo(f"  Total tables: {summary['total_tables']}")
        click.echo(f"  Create operations: {summary['crud_stats']['C']}")
        click.echo(f"  Read operations: {summary['crud_stats']['R']}")
        click.echo(f"  Update operations: {summary['crud_stats']['U']}")
        click.echo(f"  Delete operations: {summary['crud_stats']['D']}")
        click.echo(f"  Other operations: {summary['crud_stats']['O']}")
        
        if summary['most_active_class']:
            click.echo(f"  Most active class: {summary['most_active_class']}")
        if summary['most_used_table']:
            click.echo(f"  Most used table: {summary['most_used_table']}")
        
        # CRUD 매트릭스 표 출력
        if table_matrix and table_names:
            click.echo(f"\nCRUD Matrix (Class vs Table):")
            
            # 테이블 헤더 계산
            class_name_width = max(len("Class (Package)"), max(len(f"{row['class_name']} ({row['package_name']})") for row in table_matrix)) if table_matrix else 20
            table_width = 18  # 각 테이블 컬럼 너비 (스키마 정보 포함으로 더 넓게)
            
            # 헤더 출력
            header = f"{'Class (Package)':<{class_name_width}}"
            for table_name in table_names:
                # 테이블 이름을 12자로 제한
                short_name = table_name[:12] if len(table_name) > 12 else table_name
                header += f" {short_name:<{table_width}}"
            click.echo(header)
            
            # 구분선 출력
            separator = "-" * class_name_width
            for _ in table_names:
                separator += " " + "-" * table_width
            click.echo(separator)
            
            # 데이터 행 출력
            for row in table_matrix:
                class_name = row['class_name']
                package_name = row.get('package_name', 'N/A')
                class_display = f"{class_name} ({package_name})"
                line = f"{class_display:<{class_name_width}}"
                for table_name in table_names:
                    operations = row.get(table_name, '-')
                    line += f" {operations:<{table_width}}"
                click.echo(line)
        else:
            click.echo(f"\nSQL을 직접 호출하는 클래스가 없습니다.")
            click.echo(f"다음을 확인해주세요:")
            click.echo(f"  1. Java 객체 분석이 완료되었는지 확인")
            click.echo(f"  2. MyBatis Mapper와 SQL 문이 분석되었는지 확인")
            click.echo(f"  3. 프로젝트 이름이 올바른지 확인")
        
        # 파일로 저장
        if output_file:
            import json
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            click.echo(f"\nCRUD matrix saved to: {output_file}")
        
        # Excel 파일로 저장
        if output_excel:
            success = analysis_service.generate_crud_excel(project_name, output_excel)
            if success:
                click.echo(f"CRUD matrix Excel file saved to: {output_excel}")
            else:
                click.echo("Failed to generate Excel file. Check logs for details.")
        
    except Exception as e:
        click.echo(f"Error generating CRUD matrix: {e}")
        return
    finally:
        driver.close()

@cli.command()
@click.option('--neo4j-uri', default=os.getenv("NEO4J_URI", "bolt://localhost:7687"), help='Neo4j URI')
@click.option('--neo4j-user', default=os.getenv("NEO4J_USER", "neo4j"), help='Neo4j username')
@click.option('--project-name', required=True, help='Project name to analyze')
@click.option('--start-class', help='Starting class for diagram (optional)')
@click.option('--start-method', help='Starting method for diagram (optional)')
@click.option('--output-file', help='Output file to save the diagram (optional)')
@click.option('--output-image', help='Output image file (PNG/SVG/PDF) - requires mermaid-cli')
@click.option('--image-format', default='png', type=click.Choice(['png', 'svg', 'pdf']), help='Image format (default: png)')
@click.option('--image-width', default=1200, help='Image width in pixels (default: 1200)')
@click.option('--image-height', default=800, help='Image height in pixels (default: 800)')
@click.option('--auto-create-relationships', is_flag=True, default=True, help='Automatically create Method-SqlStatement relationships if needed (default: True)')
def db_call_diagram(neo4j_uri, neo4j_user, project_name, start_class, start_method, output_file, output_image, image_format, image_width, image_height, auto_create_relationships):
    """Generate database call chain diagram."""
    
    try:
        neo4j_password = os.getenv("NEO4J_PASSWORD")
        if not neo4j_password:
            click.echo("Error: NEO4J_PASSWORD environment variable is not set.")
            click.echo("Please set NEO4J_PASSWORD in your .env file or environment variables.")
            return
        
        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        analysis_service = DBCallAnalysisService(driver)
        
        click.echo("Database Call Chain Diagram")
        click.echo("=" * 50)
        
        if start_class and start_method:
            click.echo(f"Generating diagram from {start_class}.{start_method}")
        elif start_class:
            click.echo(f"Generating diagram from class {start_class}")
        else:
            click.echo(f"Generating diagram for project {project_name}")
        
        # 먼저 다이어그램 생성 시도
        diagram = analysis_service.generate_call_chain_diagram(project_name, start_class, start_method)
        
        # 다이어그램이 오류이고 자동 생성 옵션이 활성화된 경우 관계 생성
        if auto_create_relationships and diagram.startswith("오류:"):
            click.echo("No call chain diagram found. Creating Method-SqlStatement relationships...")
            graph_db = GraphDB(neo4j_uri, neo4j_user, neo4j_password)
            relationships_created = graph_db.create_method_sql_relationships(project_name)
            if relationships_created:
                click.echo(f"Created {relationships_created} Method-SqlStatement relationships.")
                # 관계 생성 후 다시 다이어그램 생성
                diagram = analysis_service.generate_call_chain_diagram(project_name, start_class, start_method)
            else:
                click.echo("No relationships could be created.")
        
        if diagram.startswith("오류:"):
            click.echo(f"Error: {diagram}")
            return
        
        # 파일로 저장
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(diagram)
            click.echo(f"Diagram saved to: {output_file}")
        else:
            # 기본 파일명으로 저장
            default_filename = f"db_call_chain_{project_name}.md"
            with open(default_filename, 'w', encoding='utf-8') as f:
                f.write(diagram)
            click.echo(f"Diagram saved to: {default_filename}")
        
        # 이미지로 변환
        if output_image:
            convert_to_image(diagram, output_image, image_format, image_width, image_height)
        
        # 다이어그램 미리보기
        click.echo("\n" + "="*50)
        click.echo("DATABASE CALL CHAIN DIAGRAM")
        click.echo("="*50)
        click.echo(diagram)
        click.echo("="*50)
        
    except Exception as e:
        click.echo(f"Error generating diagram: {e}")
        return
    finally:
        driver.close()

@cli.command()
@click.option('--neo4j-uri', default=os.getenv("NEO4J_URI", "bolt://localhost:7687"), help='Neo4j URI')
@click.option('--neo4j-user', default=os.getenv("NEO4J_USER", "neo4j"), help='Neo4j username')
@click.option('--project-name', required=True, help='Project name to analyze')
@click.option('--output-file', help='Output file to save the diagram (optional)')
@click.option('--output-image', help='Output image file (PNG/SVG/PDF) - requires mermaid-cli')
@click.option('--image-format', default='png', type=click.Choice(['png', 'svg', 'pdf']), help='Image format (default: png)')
@click.option('--image-width', default=1200, help='Image width in pixels (default: 1200)')
@click.option('--image-height', default=800, help='Image height in pixels (default: 800)')
@click.option('--auto-create-relationships', is_flag=True, default=True, help='Automatically create Method-SqlStatement relationships if needed (default: True)')
def crud_visualization(neo4j_uri, neo4j_user, project_name, output_file, output_image, image_format, image_width, image_height, auto_create_relationships):
    """Generate CRUD matrix visualization diagram showing class-table relationships."""
    
    try:
        neo4j_password = os.getenv("NEO4J_PASSWORD")
        if not neo4j_password:
            click.echo("Error: NEO4J_PASSWORD environment variable is not set.")
            click.echo("Please set NEO4J_PASSWORD in your .env file or environment variables.")
            return
        
        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        analysis_service = DBCallAnalysisService(driver)
        
        click.echo("CRUD Matrix Visualization Diagram")
        click.echo("=" * 50)
        click.echo(f"Generating diagram for project: {project_name}")
        
        # 먼저 다이어그램 생성 시도
        diagram = analysis_service.generate_crud_visualization_diagram(project_name)
        
        # 다이어그램이 오류이고 자동 생성 옵션이 활성화된 경우 관계 생성
        if auto_create_relationships and diagram.startswith("Error:"):
            click.echo("No CRUD visualization found. Creating Method-SqlStatement relationships...")
            graph_db = GraphDB(neo4j_uri, neo4j_user, neo4j_password)
            relationships_created = graph_db.create_method_sql_relationships(project_name)
            if relationships_created:
                click.echo(f"Created {relationships_created} Method-SqlStatement relationships.")
                # 관계 생성 후 다시 다이어그램 생성
                diagram = analysis_service.generate_crud_visualization_diagram(project_name)
            else:
                click.echo("No relationships could be created.")
        
        if diagram.startswith("Error:"):
            click.echo(f"Error: {diagram}")
            return
        
        # 파일로 저장
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(diagram)
            click.echo(f"Diagram saved to: {output_file}")
        else:
            # 기본 파일명으로 저장
            default_filename = f"crud_visualization_{project_name}.md"
            with open(default_filename, 'w', encoding='utf-8') as f:
                f.write(diagram)
            click.echo(f"Diagram saved to: {default_filename}")
        
        # 이미지로 변환
        if output_image:
            convert_to_image(diagram, output_image, image_format, image_width, image_height)
        
        # 다이어그램 미리보기
        click.echo("\n" + "="*50)
        click.echo("CRUD MATRIX VISUALIZATION DIAGRAM")
        click.echo("="*50)
        click.echo(diagram)
        click.echo("="*50)
        
    except Exception as e:
        click.echo(f"Error generating diagram: {e}")
        return
    finally:
        driver.close()

@cli.command()
@click.option('--neo4j-uri', default=os.getenv("NEO4J_URI", "bolt://localhost:7687"), help='Neo4j URI')
@click.option('--neo4j-user', default=os.getenv("NEO4J_USER", "neo4j"), help='Neo4j username')
@click.option('--project-name', required=True, help='Project name to analyze')
@click.option('--table-name', required=True, help='Table name to analyze impact for')
@click.option('--output-file', help='Output file to save the impact analysis (optional)')
@click.option('--auto-create-relationships', is_flag=True, default=True, help='Automatically create Method-SqlStatement relationships if needed (default: True)')
def table_impact(neo4j_uri, neo4j_user, project_name, table_name, output_file, auto_create_relationships):
    """Analyze impact of table changes on application code."""
    
    try:
        neo4j_password = os.getenv("NEO4J_PASSWORD")
        if not neo4j_password:
            click.echo("Error: NEO4J_PASSWORD environment variable is not set.")
            click.echo("Please set NEO4J_PASSWORD in your .env file or environment variables.")
            return
        
        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        analysis_service = DBCallAnalysisService(driver)
        
        click.echo("Table Impact Analysis")
        click.echo("=" * 50)
        click.echo(f"Analyzing impact of changes to table: {table_name}")
        
        # 먼저 영향도 분석 시도
        result = analysis_service.analyze_table_impact(project_name, table_name)
        
        # 분석 결과가 없고 자동 생성 옵션이 활성화된 경우 관계 생성
        if auto_create_relationships and ('error' in result or not result.get('impacted_classes')):
            click.echo("No impact analysis found. Creating Method-SqlStatement relationships...")
            graph_db = GraphDB(neo4j_uri, neo4j_user, neo4j_password)
            relationships_created = graph_db.create_method_sql_relationships(project_name)
            if relationships_created:
                click.echo(f"Created {relationships_created} Method-SqlStatement relationships.")
                # 관계 생성 후 다시 영향도 분석
                result = analysis_service.analyze_table_impact(project_name, table_name)
            else:
                click.echo("No relationships could be created.")
        
        if 'error' in result:
            click.echo(f"Error: {result['error']}")
            return
        
        impacted_classes = result['impacted_classes']
        summary = result['summary']
        
        click.echo(f"\nImpact Summary:")
        click.echo(f"  Table: {summary['table_name']}")
        click.echo(f"  Impacted classes: {summary['total_impacted_classes']}")
        click.echo(f"  Impacted methods: {summary['total_impacted_methods']}")
        click.echo(f"  SQL statements: {summary['total_sql_statements']}")
        click.echo(f"  CRUD operations: {', '.join(summary['crud_operations'])}")
        
        if summary['high_complexity_sql']:
            click.echo(f"  High complexity SQL: {len(summary['high_complexity_sql'])}")
        
        # 영향받는 클래스 상세 정보
        if impacted_classes:
            click.echo(f"\nImpacted Classes:")
            click.echo("-" * 80)
            click.echo(f"{'Class':<25} {'Method':<25} {'SQL Type':<10} {'Complexity':<12}")
            click.echo("-" * 80)
            
            for cls in impacted_classes:
                class_name = cls['class_name']
                method_name = cls['method_name'] or 'N/A'
                sql_type = cls['sql_type'] or 'N/A'
                complexity = str(cls['complexity_score']) if cls['complexity_score'] else 'N/A'
                
                click.echo(f"{class_name:<25} {method_name:<25} {sql_type:<10} {complexity:<12}")
        
        # 고복잡도 SQL 상세 정보
        if summary['high_complexity_sql']:
            click.echo(f"\nHigh Complexity SQL Statements:")
            click.echo("-" * 60)
            for sql in summary['high_complexity_sql']:
                click.echo(f"  {sql['class_name']}.{sql['method_name']} - {sql['sql_type']} (complexity: {sql['complexity_score']})")
        
        # 파일로 저장
        if output_file:
            import json
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            click.echo(f"\nImpact analysis saved to: {output_file}")
        
    except Exception as e:
        click.echo(f"Error analyzing table impact: {e}")
        return
    finally:
        driver.close()

@cli.command()
@click.option('--neo4j-uri', default=os.getenv("NEO4J_URI", "bolt://localhost:7687"), help='Neo4j URI')
@click.option('--neo4j-user', default=os.getenv("NEO4J_USER", "neo4j"), help='Neo4j username')
@click.option('--project-name', required=True, help='Project name to analyze')
@click.option('--output-file', help='Output file to save the statistics (optional)')
@click.option('--auto-create-relationships', is_flag=True, default=True, help='Automatically create Method-SqlStatement relationships if needed (default: True)')
def db_statistics(neo4j_uri, neo4j_user, project_name, output_file, auto_create_relationships):
    """Show database usage statistics."""
    
    try:
        neo4j_password = os.getenv("NEO4J_PASSWORD")
        if not neo4j_password:
            click.echo("Error: NEO4J_PASSWORD environment variable is not set.")
            click.echo("Please set NEO4J_PASSWORD in your .env file or environment variables.")
            return
        
        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        analysis_service = DBCallAnalysisService(driver)
        
        click.echo("Database Usage Statistics")
        click.echo("=" * 50)
        
        # 먼저 통계 조회 시도
        result = analysis_service.get_database_usage_statistics(project_name)
        
        # 통계가 없고 자동 생성 옵션이 활성화된 경우 관계 생성
        if auto_create_relationships and ('error' in result or not result.get('sql_statistics')):
            click.echo("No database statistics found. Creating Method-SqlStatement relationships...")
            graph_db = GraphDB(neo4j_uri, neo4j_user, neo4j_password)
            relationships_created = graph_db.create_method_sql_relationships(project_name)
            if relationships_created:
                click.echo(f"Created {relationships_created} Method-SqlStatement relationships.")
                # 관계 생성 후 다시 통계 조회
                result = analysis_service.get_database_usage_statistics(project_name)
            else:
                click.echo("No relationships could be created.")
        
        if 'error' in result:
            click.echo(f"Error: {result['error']}")
            return
        
        sql_stats = result['sql_statistics']
        table_usage = result['table_usage']
        complexity_stats = result['complexity_statistics']
        
        # SQL 통계
        if sql_stats:
            click.echo(f"\nSQL Statistics:")
            click.echo(f"  Total SQL statements: {sql_stats['total_sql']}")
            click.echo(f"  SELECT statements: {sql_stats.get('SELECT', 0)}")
            click.echo(f"  INSERT statements: {sql_stats.get('INSERT', 0)}")
            click.echo(f"  UPDATE statements: {sql_stats.get('UPDATE', 0)}")
            click.echo(f"  DELETE statements: {sql_stats.get('DELETE', 0)}")
        
        # 테이블 사용 통계
        if table_usage:
            click.echo(f"\nTable Usage Statistics:")
            click.echo("-" * 60)
            click.echo(f"{'Table Name':<30} {'Access Count':<15} {'Operations':<20}")
            click.echo("-" * 60)
            
            for table in table_usage:
                table_name = table['table_name']
                access_count = table['access_count']
                operations = ', '.join(table['operations'])
                click.echo(f"{table_name:<30} {access_count:<15} {operations:<20}")
        
        # 복잡도 통계
        if complexity_stats:
            click.echo(f"\nSQL Complexity Statistics:")
            click.echo(f"  Simple queries: {complexity_stats.get('simple', 0)}")
            click.echo(f"  Medium queries: {complexity_stats.get('medium', 0)}")
            click.echo(f"  Complex queries: {complexity_stats.get('complex', 0)}")
            click.echo(f"  Very complex queries: {complexity_stats.get('very_complex', 0)}")
        
        # 파일로 저장
        if output_file:
            import json
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            click.echo(f"\nStatistics saved to: {output_file}")
        
    except Exception as e:
        click.echo(f"Error getting database statistics: {e}")
        return
    finally:
        driver.close()

if __name__ == '__main__':
    cli()
