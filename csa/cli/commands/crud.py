import json
import os
from datetime import datetime

import click
from neo4j import GraphDatabase

from csa.cli.core.lifecycle import with_command_lifecycle
from csa.cli.core.storage import _save_crud_matrix_as_excel, _save_crud_matrix_as_image
from csa.services.db_call_analysis import DBCallAnalysisService
from csa.services.graph_db import GraphDB
from csa.utils.logger import set_command_context, get_logger


def _ensure_password() -> str | None:
    logger = get_logger(__name__)
    password = os.getenv("NEO4J_PASSWORD")
    if not password:
        logger.error("Error: NEO4J_PASSWORD environment variable is not set.")
        logger.error("Please set NEO4J_PASSWORD in your .env file or environment variables.")
    return password


@click.command(name="crud-matrix")
@click.option("--neo4j-uri", default=os.getenv("NEO4J_URI", "bolt://localhost:7687"), help="Neo4j URI")
@click.option("--neo4j-user", default=os.getenv("NEO4J_USER", "neo4j"), help="Neo4j username")
@click.option("--project-name", required=True, help="Project name to analyze")
@click.option(
    "--output-format",
    default="excel",
    type=click.Choice(["excel", "svg", "png"], case_sensitive=False),
    help="Output format (default: excel)",
)
@click.option(
    "--auto-create-relationships",
    is_flag=True,
    default=True,
    help="Automatically create Method-SqlStatement relationships if needed (default: True)",
)
@with_command_lifecycle("crud-matrix")
def crud_matrix_command(neo4j_uri, neo4j_user, project_name, output_format, auto_create_relationships):
    """Show CRUD matrix for classes and tables."""

    # 명령어 실행 직전에 컨텍스트 설정 (모든 로거가 같은 파일 사용)
    set_command_context("crud-matrix")
    logger = get_logger(__name__, command="crud-matrix")

    result = {"success": False, "message": "", "stats": {}, "error": None, "files": []}

    neo4j_password = _ensure_password()
    if not neo4j_password:
        result["error"] = "NEO4J_PASSWORD not set"
        return result

    try:
        neo4j_database = os.getenv("NEO4J_DATABASE", "neo4j")
        db = GraphDB(neo4j_uri, neo4j_user, neo4j_password, neo4j_database)

        logger.info("CRUD Matrix - Class to Table Operations")
        logger.info("=" * 80)

        matrix = db.get_crud_matrix(project_name)

        if not matrix and auto_create_relationships:
            logger.info("No CRUD operations found. Creating Method-SqlStatement relationships...")
            relationships_created = db.create_method_sql_relationships(project_name)
            if relationships_created:
                logger.info(f"Created {relationships_created} Method-SqlStatement relationships.")
                matrix = db.get_crud_matrix(project_name)
            else:
                logger.info("No relationships could be created.")

        if not matrix:
            result["error"] = "No CRUD operations found"
            logger.info("No CRUD operations found.")
            if not auto_create_relationships:
                logger.info(
                    "Tip: Use --auto-create-relationships to build Method-SqlStatement links before running again."
                )
            return result

        logger.info(f"{'Package':<35} {'Class Name':<30} {'Method':<25} {'Schema':<10} {'Table':<20} {'Operations':<15}")
        logger.info("-" * 135)

        for row in matrix:
            package_name = row["package_name"] or "N/A"
            class_name = row["class_name"]
            method_name = row["method_name"]
            schema = row["schema"] or "unknown"
            table_name = row["table_name"]
            operations = ", ".join(row["operations"]) if row["operations"] else "None"
            logger.info(
                f"{package_name:<35} {class_name:<30} {method_name:<25} {schema:<10} {table_name:<20} {operations:<15}"
            )

        logger.info(f"\nTotal: {len(matrix)} class-table relationships.")

        output_dir = os.getenv("CRUD_MATRIX_OUTPUT_DIR", "./output/crud-matrix")
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

        md_filename = f"CRUD_{project_name}_{timestamp}.md"
        md_filepath = os.path.join(output_dir, md_filename)

        lines = [
            f"# CRUD Matrix [Project : {project_name}]",
            "",
            f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            f"**Total:** {len(matrix)} class-table relationships.",
            "",
            "| Package | Class Name | Method | Schema | Table | Operations |",
            "|---------|------------|--------|--------|-------|------------|",
        ]
        for row in matrix:
            lines.append(
                "| {package} | {class_name} | {method} | {schema} | {table} | {ops} |".format(
                    package=row["package_name"] or "N/A",
                    class_name=row["class_name"],
                    method=row["method_name"],
                    schema=row["schema"] or "unknown",
                    table=row["table_name"],
                    ops=", ".join(row["operations"]) if row["operations"] else "None",
                )
            )

        with open(md_filepath, "w", encoding="utf-8") as file:
            file.write("\n".join(lines))
        logger.info(f"\nCRUD matrix (Markdown) saved to: {md_filepath}")
        result["files"].append(md_filepath)

        fmt = output_format.lower()
        if fmt == "excel":
            excel_filename = f"CRUD_{project_name}_{timestamp}.xlsx"
            excel_filepath = os.path.join(output_dir, excel_filename)
            if _save_crud_matrix_as_excel(matrix, project_name, excel_filepath):
                logger.info(f"CRUD matrix (Excel) saved to: {excel_filepath}")
                result["files"].append(excel_filepath)
            else:
                logger.info("Failed to generate Excel file.")
        elif fmt in {"svg", "png"}:
            image_filename = f"CRUD_{project_name}_{timestamp}.{fmt}"
            image_filepath = os.path.join(output_dir, image_filename)
            if _save_crud_matrix_as_image(matrix, project_name, image_filepath, fmt):
                logger.info(f"CRUD matrix ({fmt.upper()}) saved to: {image_filepath}")
                result["files"].append(image_filepath)
            else:
                logger.info(f"Failed to generate {fmt.upper()} file.")

        table_groups = {}
        for row in matrix:
            table_groups.setdefault(row["table_name"], []).append(row)

        result["success"] = True
        result["message"] = "CRUD matrix generated successfully"
        result["stats"] = {
            "total_relationships": len(matrix),
            "total_tables": len(table_groups),
            "output_format": output_format,
            "files_generated": len(result["files"]),
        }
    except Exception as exc:  # pylint: disable=broad-except
        result["error"] = str(exc)
        logger.error(f"Error getting CRUD matrix: {exc}")

    return result


@click.command(name="table-summary")
@click.option("--neo4j-uri", default=os.getenv("NEO4J_URI", "bolt://localhost:7687"), help="Neo4j URI")
@click.option("--neo4j-user", default=os.getenv("NEO4J_USER", "neo4j"), help="Neo4j username")
@click.option("--project-name", required=True, help="Project name to analyze")
@click.option("--output-file", help="Output file to save the summary (optional)")
@click.option(
    "--auto-create-relationships",
    is_flag=True,
    default=True,
    help="Automatically create Method-SqlStatement relationships if needed (default: True)",
)
@with_command_lifecycle("table-summary")
def table_summary_command(neo4j_uri, neo4j_user, project_name, output_file, auto_create_relationships):
    """Show CRUD summary for each table."""

    set_command_context("table-summary")
    logger = get_logger(__name__, command="table-summary")
    neo4j_password = _ensure_password()
    if not neo4j_password:
        return

    try:
        neo4j_database = os.getenv("NEO4J_DATABASE", "neo4j")
        db = GraphDB(neo4j_uri, neo4j_user, neo4j_password, neo4j_database)

        logger.info("Table Summary Analysis")
        logger.info("=" * 50)

        table_summary = db.get_table_crud_summary(project_name)

        if auto_create_relationships and not table_summary:
            logger.info("No table summary found. Creating Method-SqlStatement relationships...")
            relationships_created = db.create_method_sql_relationships(project_name)
            if relationships_created:
                logger.info(f"Created {relationships_created} Method-SqlStatement relationships.")
                table_summary = db.get_table_crud_summary(project_name)
            else:
                logger.info("No relationships could be created.")

        if not table_summary:
            logger.info("No table summary data available.")
            return

        logger.info(f"\nTable Summary for project: {project_name}")
        logger.info("-" * 80)
        logger.info(f"{'Table Name':<30} {'Classes':<10} {'Read Ops':<10} {'Write Ops':<10}")
        logger.info("-" * 80)

        for table in table_summary:
            logger.info(
                f"{table['table_name']:<30} "
                f"{table['classes_count']:<10} "
                f"{table['read_operations']:<10} "
                f"{table['write_operations']:<10}"
            )

        if output_file:
            result = {"project_name": project_name, "table_summary": table_summary}
            with open(output_file, "w", encoding="utf-8") as file:
                json.dump(result, file, indent=2, ensure_ascii=False)
            logger.info(f"\nSummary saved to: {output_file}")
    except Exception as exc:  # pylint: disable=broad-except
        logger.error(f"Error generating table summary: {exc}")


@click.command(name="crud-analysis")
@click.option("--neo4j-uri", default=os.getenv("NEO4J_URI", "bolt://localhost:7687"), help="Neo4j URI")
@click.option("--neo4j-user", default=os.getenv("NEO4J_USER", "neo4j"), help="Neo4j username")
@click.option("--project-name", required=True, help="Project name to analyze")
@click.option("--output-dir", default=os.getenv("CRUD_MATRIX_OUTPUT_DIR", "./output/crud-matrix"), help="Output directory")
@click.option(
    "--auto-create-relationships",
    is_flag=True,
    default=True,
    help="Automatically create Method-SqlStatement relationships if needed (default: True)",
)
@with_command_lifecycle("crud-analysis")
def crud_analysis_command(neo4j_uri, neo4j_user, project_name, output_dir, auto_create_relationships):
    """Generate CRUD matrix analysis summary."""

    set_command_context("crud-analysis")
    logger = get_logger(__name__, command="crud-analysis")
    neo4j_password = _ensure_password()
    if not neo4j_password:
        return

    driver = None
    try:
        neo4j_database = os.getenv("NEO4J_DATABASE", "neo4j")
        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        db = GraphDB(neo4j_uri, neo4j_user, neo4j_password, neo4j_database)

        logger.info("Generating CRUD matrix analysis...")
        matrix = db.get_crud_matrix(project_name)

        if not matrix and auto_create_relationships:
            logger.info("No CRUD operations found. Creating Method-SqlStatement relationships...")
            relationships_created = db.create_method_sql_relationships(project_name)
            if relationships_created:
                logger.info(f"Created {relationships_created} Method-SqlStatement relationships.")
                matrix = db.get_crud_matrix(project_name)
            else:
                logger.info("No relationships could be created.")

        if not matrix:
            logger.info("No CRUD operations found.")
            return

        os.makedirs(output_dir, exist_ok=True)
        summary_file = os.path.join(output_dir, f"crud_analysis_{project_name}.md")

        with open(summary_file, "w", encoding="utf-8") as file:
            file.write(f"# CRUD Analysis Summary [{project_name}]\n\n")
            file.write(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            file.write("## Class to Table Mapping\n\n")
            file.write("| Class | Table | Operations |\n")
            file.write("|-------|-------|------------|\n")

            for entry in matrix:
                operations = ", ".join(entry["operations"]) if entry["operations"] else "None"
                file.write(f"| {entry['class_name']} | {entry['table_name']} | {operations} |\n")

        logger.info(f"CRUD analysis summary saved to: {summary_file}")
    except Exception as exc:  # pylint: disable=broad-except
        logger.error(f"Error generating CRUD analysis: {exc}")
    finally:
        if driver:
            driver.close()


@click.command(name="crud-visualization")
@click.option("--neo4j-uri", default=os.getenv("NEO4J_URI", "bolt://localhost:7687"), help="Neo4j URI")
@click.option("--neo4j-user", default=os.getenv("NEO4J_USER", "neo4j"), help="Neo4j username")
@click.option("--project-name", required=True, help="Project name to analyze")
@click.option(
    "--output-format",
    default="excel",
    type=click.Choice(["excel", "svg", "png"], case_sensitive=False),
    help="Output format for visualization (default: excel)",
)
@click.option("--image-width", default=1200, help="Image width in pixels when exporting images")
@click.option("--image-height", default=800, help="Image height in pixels when exporting images")
@click.option(
    "--auto-create-relationships",
    is_flag=True,
    default=True,
    help="Automatically create Method-SqlStatement relationships if needed (default: True)",
)
@with_command_lifecycle("crud-visualization")
def crud_visualization_command(
    neo4j_uri,
    neo4j_user,
    project_name,
    output_format,
    image_width,
    image_height,
    auto_create_relationships,
):
    """Generate CRUD matrix visualization diagram showing class-table relationships."""
    set_command_context("crud-visualization")
    logger = get_logger(__name__, command="crud-visualization")
    neo4j_password = _ensure_password()
    if not neo4j_password:
        return

    try:
        neo4j_database = os.getenv("NEO4J_DATABASE", "neo4j")
        db = GraphDB(neo4j_uri, neo4j_user, neo4j_password, neo4j_database)

        logger.info("CRUD Matrix Visualization")
        logger.info("=" * 50)
        logger.info(f"Generating {output_format.upper()} visualization for project: {project_name}")

        matrix = db.get_crud_matrix(project_name)

        if auto_create_relationships and not matrix:
            logger.info("No CRUD data found. Creating Method-SqlStatement relationships...")
            relationships_created = db.create_method_sql_relationships(project_name)
            if relationships_created:
                logger.info(f"Created {relationships_created} Method-SqlStatement relationships.")
                matrix = db.get_crud_matrix(project_name)
            else:
                logger.info("No relationships could be created.")

        if not matrix:
            logger.error("Error: No CRUD data found")
            return

        output_dir = os.getenv("CRUD_MATRIX_OUTPUT_DIR", "./output/crud-matrix")
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

        fmt = output_format.lower()
        if fmt == "excel":
            excel_filename = f"CRUD_visualization_{project_name}_{timestamp}.xlsx"
            excel_filepath = os.path.join(output_dir, excel_filename)
            if _save_crud_matrix_as_excel(matrix, project_name, excel_filepath):
                logger.info(f"CRUD visualization (Excel) saved to: {excel_filepath}")
            else:
                logger.info("Failed to save Excel file.")
        else:
            image_filename = f"CRUD_visualization_{project_name}_{timestamp}.{fmt}"
            image_filepath = os.path.join(output_dir, image_filename)
            if _save_crud_matrix_as_image(matrix, project_name, image_filepath, fmt):
                logger.info(f"CRUD visualization ({fmt.upper()}) saved to: {image_filepath}")
            else:
                logger.info(f"Failed to save {fmt.upper()} file.")

        # 요약 정보 계산
        class_names = set()
        table_names = set()
        for row in matrix:
            if row.get("class_name"):
                class_names.add(row["class_name"])
            if row.get("table_name"):
                table_names.add(row["table_name"])

        logger.info("=" * 50)
        logger.info("CRUD MATRIX SUMMARY")
        logger.info("=" * 50)
        logger.info(f"Total classes: {len(class_names)}")
        logger.info(f"Total tables: {len(table_names)}")
        logger.info(f"Total relationships: {len(matrix)}")

        if class_names:
            logger.info("\nClasses with database operations:")
            # 클래스별 테이블 수 계산
            class_table_count = {}
            for row in matrix:
                class_name = row.get("class_name")
                table_name = row.get("table_name")
                if class_name and table_name:
                    if class_name not in class_table_count:
                        class_table_count[class_name] = set()
                    class_table_count[class_name].add(table_name)

            # 상위 10개 출력
            sorted_classes = sorted(class_table_count.items(), key=lambda x: len(x[1]), reverse=True)
            for class_name, tables in sorted_classes[:10]:
                logger.info(f"  - {class_name}: {len(tables)} tables")
            if len(sorted_classes) > 10:
                logger.info(f"  ... and {len(sorted_classes) - 10} more classes")
    except Exception as exc:  # pylint: disable=broad-except
        logger.error(f"Error generating diagram: {exc}")


@click.command(name="table-impact")
@click.option("--neo4j-uri", default=os.getenv("NEO4J_URI", "bolt://localhost:7687"), help="Neo4j URI")
@click.option("--neo4j-user", default=os.getenv("NEO4J_USER", "neo4j"), help="Neo4j username")
@click.option("--project-name", required=True, help="Project name to analyze")
@click.option("--table-name", required=True, help="Table name to analyze impact for")
@click.option("--output-file", help="Output file to save the impact analysis (optional)")
@click.option(
    "--auto-create-relationships",
    is_flag=True,
    default=True,
    help="Automatically create Method-SqlStatement relationships if needed (default: True)",
)
@with_command_lifecycle("table-impact")
def table_impact_command(neo4j_uri, neo4j_user, project_name, table_name, output_file, auto_create_relationships):
    """Analyze impact of table changes on application code."""

    set_command_context("table-impact")
    logger = get_logger(__name__, command="table-impact")
    neo4j_password = _ensure_password()
    if not neo4j_password:
        return

    driver = None
    try:
        neo4j_database = os.getenv("NEO4J_DATABASE", "neo4j")
        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        analysis_service = DBCallAnalysisService(driver)

        logger.info("Table Impact Analysis")
        logger.info("=" * 50)
        logger.info(f"Analyzing impact of changes to table: {table_name}")

        result = analysis_service.analyze_table_impact(project_name, table_name)

        if auto_create_relationships and ("error" in result or not result.get("impacted_classes")):
            logger.info("No impact analysis found. Creating Method-SqlStatement relationships...")
            graph_db = GraphDB(neo4j_uri, neo4j_user, neo4j_password, neo4j_database)
            relationships_created = graph_db.create_method_sql_relationships(project_name)
            if relationships_created:
                logger.info(f"Created {relationships_created} Method-SqlStatement relationships.")
                result = analysis_service.analyze_table_impact(project_name, table_name)
            else:
                logger.info("No relationships could be created.")

        if "error" in result:
            logger.error(f"Error: {result['error']}")
            return

        impacted_classes = result["impacted_classes"]
        summary = result["summary"]

        logger.info("\nImpact Summary:")
        logger.info(f"  Table: {summary['table_name']}")
        logger.info(f"  Impacted classes: {summary['total_impacted_classes']}")
        logger.info(f"  Impacted methods: {summary['total_impacted_methods']}")
        logger.info(f"  SQL statements: {summary['total_sql_statements']}")
        logger.info(f"  CRUD operations: {', '.join(summary['crud_operations'])}")

        if summary["high_complexity_sql"]:
            logger.info(f"  High complexity SQL: {len(summary['high_complexity_sql'])}")

        if impacted_classes:
            logger.info("\nImpacted Classes:")
            logger.info("-" * 80)
            logger.info(f"{'Class':<25} {'Method':<25} {'SQL Type':<10} {'Complexity':<12}")
            logger.info("-" * 80)
            for cls in impacted_classes:
                class_name = cls["class_name"]
                method_name = cls["method_name"] or "N/A"
                sql_type = cls["sql_type"] or "N/A"
                complexity = str(cls["complexity_score"]) if cls["complexity_score"] else "N/A"
                logger.info(f"{class_name:<25} {method_name:<25} {sql_type:<10} {complexity:<12}")

        if summary["high_complexity_sql"]:
            logger.info("\nHigh Complexity SQL Statements:")
            logger.info("-" * 60)
            for sql in summary["high_complexity_sql"]:
                logger.info(
                    f"  {sql['class_name']}.{sql['method_name']} - {sql['sql_type']} (complexity: {sql['complexity_score']})"
                )

        if output_file:
            with open(output_file, "w", encoding="utf-8") as file:
                json.dump(result, file, indent=2, ensure_ascii=False)
            logger.info(f"\nImpact analysis saved to: {output_file}")
    except Exception as exc:  # pylint: disable=broad-except
        logger.error(f"Error analyzing table impact: {exc}")
    finally:
        if driver:
            driver.close()


def register(cli: click.Group) -> None:
    """Attach CRUD-related commands to the given CLI group."""

    cli.add_command(crud_matrix_command)
    cli.add_command(table_summary_command)
    cli.add_command(crud_analysis_command)
    cli.add_command(crud_visualization_command)
    cli.add_command(table_impact_command)


__all__ = ["register"]
