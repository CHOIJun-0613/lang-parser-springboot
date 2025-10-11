import json
import os
from datetime import datetime

import click
from neo4j import GraphDatabase

from csa.cli.core.lifecycle import with_command_lifecycle
from csa.cli.core.storage import _save_crud_matrix_as_excel, _save_crud_matrix_as_image
from csa.services.db_call_analysis import DBCallAnalysisService
from csa.services.graph_db import GraphDB


def _ensure_password() -> str | None:
    password = os.getenv("NEO4J_PASSWORD")
    if not password:
        click.echo("Error: NEO4J_PASSWORD environment variable is not set.")
        click.echo("Please set NEO4J_PASSWORD in your .env file or environment variables.")
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

    result = {"success": False, "message": "", "stats": {}, "error": None, "files": []}

    neo4j_password = _ensure_password()
    if not neo4j_password:
        result["error"] = "NEO4J_PASSWORD not set"
        return result

    try:
        neo4j_database = os.getenv("NEO4J_DATABASE", "neo4j")
        db = GraphDB(neo4j_uri, neo4j_user, neo4j_password, neo4j_database)

        click.echo("CRUD Matrix - Class to Table Operations")
        click.echo("=" * 80)

        matrix = db.get_crud_matrix(project_name)

        if not matrix and auto_create_relationships:
            click.echo("No CRUD operations found. Creating Method-SqlStatement relationships...")
            relationships_created = db.create_method_sql_relationships(project_name)
            if relationships_created:
                click.echo(f"Created {relationships_created} Method-SqlStatement relationships.")
                matrix = db.get_crud_matrix(project_name)
            else:
                click.echo("No relationships could be created.")

        if not matrix:
            result["error"] = "No CRUD operations found"
            click.echo("No CRUD operations found.")
            if not auto_create_relationships:
                click.echo(
                    "Tip: Use --auto-create-relationships to build Method-SqlStatement links before running again."
                )
            return result

        click.echo(f"{'Package':<35} {'Class Name':<30} {'Method':<25} {'Schema':<10} {'Table':<20} {'Operations':<15}")
        click.echo("-" * 135)

        for row in matrix:
            package_name = row["package_name"] or "N/A"
            class_name = row["class_name"]
            method_name = row["method_name"]
            schema = row["schema"] or "unknown"
            table_name = row["table_name"]
            operations = ", ".join(row["operations"]) if row["operations"] else "None"
            click.echo(
                f"{package_name:<35} {class_name:<30} {method_name:<25} {schema:<10} {table_name:<20} {operations:<15}"
            )

        click.echo(f"\nTotal: {len(matrix)} class-table relationships.")

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
        lines.append("")
        lines.append(f"**Total:** {len(matrix)} class-table relationships.")

        with open(md_filepath, "w", encoding="utf-8") as file:
            file.write("\n".join(lines))
        click.echo(f"\nCRUD matrix (Markdown) saved to: {md_filepath}")
        result["files"].append(md_filepath)

        fmt = output_format.lower()
        if fmt == "excel":
            excel_filename = f"CRUD_{project_name}_{timestamp}.xlsx"
            excel_filepath = os.path.join(output_dir, excel_filename)
            if _save_crud_matrix_as_excel(matrix, project_name, excel_filepath):
                click.echo(f"CRUD matrix (Excel) saved to: {excel_filepath}")
                result["files"].append(excel_filepath)
            else:
                click.echo("Failed to generate Excel file.")
        elif fmt in {"svg", "png"}:
            image_filename = f"CRUD_{project_name}_{timestamp}.{fmt}"
            image_filepath = os.path.join(output_dir, image_filename)
            if _save_crud_matrix_as_image(matrix, project_name, image_filepath, fmt):
                click.echo(f"CRUD matrix ({fmt.upper()}) saved to: {image_filepath}")
                result["files"].append(image_filepath)
            else:
                click.echo(f"Failed to generate {fmt.upper()} file.")

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
        click.echo(f"Error getting CRUD matrix: {exc}")

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

    neo4j_password = _ensure_password()
    if not neo4j_password:
        return

    driver = None
    try:
        neo4j_database = os.getenv("NEO4J_DATABASE", "neo4j")
        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        analysis_service = DBCallAnalysisService(driver)

        click.echo("Table Summary Analysis")
        click.echo("=" * 50)

        result = analysis_service.get_table_summary(project_name)

        if auto_create_relationships and ("error" in result or not result.get("table_summary")):
            click.echo("No table summary found. Creating Method-SqlStatement relationships...")
            graph_db = GraphDB(neo4j_uri, neo4j_user, neo4j_password, neo4j_database)
            relationships_created = graph_db.create_method_sql_relationships(project_name)
            if relationships_created:
                click.echo(f"Created {relationships_created} Method-SqlStatement relationships.")
                result = analysis_service.get_table_summary(project_name)
            else:
                click.echo("No relationships could be created.")

        if "error" in result:
            click.echo(f"Error: {result['error']}")
            return

        table_summary = result.get("table_summary", [])
        if not table_summary:
            click.echo("No table summary data available.")
            return

        click.echo(f"\nTable Summary for project: {project_name}")
        click.echo("-" * 80)
        click.echo(f"{'Table Name':<30} {'Classes':<10} {'Read Ops':<10} {'Write Ops':<10}")
        click.echo("-" * 80)

        for table in table_summary:
            click.echo(
                f"{table['table_name']:<30} "
                f"{table['classes_count']:<10} "
                f"{table['read_operations']:<10} "
                f"{table['write_operations']:<10}"
            )

        if output_file:
            with open(output_file, "w", encoding="utf-8") as file:
                json.dump(result, file, indent=2, ensure_ascii=False)
            click.echo(f"\nSummary saved to: {output_file}")
    except Exception as exc:  # pylint: disable=broad-except
        click.echo(f"Error generating table summary: {exc}")
    finally:
        if driver:
            driver.close()


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

    neo4j_password = _ensure_password()
    if not neo4j_password:
        return

    driver = None
    try:
        neo4j_database = os.getenv("NEO4J_DATABASE", "neo4j")
        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        db = GraphDB(neo4j_uri, neo4j_user, neo4j_password, neo4j_database)

        click.echo("Generating CRUD matrix analysis...")
        matrix = db.get_crud_matrix(project_name)

        if not matrix and auto_create_relationships:
            click.echo("No CRUD operations found. Creating Method-SqlStatement relationships...")
            relationships_created = db.create_method_sql_relationships(project_name)
            if relationships_created:
                click.echo(f"Created {relationships_created} Method-SqlStatement relationships.")
                matrix = db.get_crud_matrix(project_name)
            else:
                click.echo("No relationships could be created.")

        if not matrix:
            click.echo("No CRUD operations found.")
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

        click.echo(f"CRUD analysis summary saved to: {summary_file}")
    except Exception as exc:  # pylint: disable=broad-except
        click.echo(f"Error generating CRUD analysis: {exc}")
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

    neo4j_password = _ensure_password()
    if not neo4j_password:
        return

    driver = None
    try:
        neo4j_database = os.getenv("NEO4J_DATABASE", "neo4j")
        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        analysis_service = DBCallAnalysisService(driver)

        click.echo("CRUD Matrix Visualization")
        click.echo("=" * 50)
        click.echo(f"Generating {output_format.upper()} visualization for project: {project_name}")

        result = analysis_service.generate_crud_matrix(project_name)

        if auto_create_relationships and ("error" in result or not result.get("class_matrix")):
            click.echo("No CRUD data found. Creating Method-SqlStatement relationships...")
            graph_db = GraphDB(neo4j_uri, neo4j_user, neo4j_password, neo4j_database)
            relationships_created = graph_db.create_method_sql_relationships(project_name)
            if relationships_created:
                click.echo(f"Created {relationships_created} Method-SqlStatement relationships.")
                result = analysis_service.generate_crud_matrix(project_name)
            else:
                click.echo("No relationships could be created.")

        if "error" in result or not result.get("class_matrix"):
            click.echo(f"Error: {result.get('error', 'No CRUD data found')}")
            return

        output_dir = os.getenv("CRUD_MATRIX_OUTPUT_DIR", "./output/crud-matrix")
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

        fmt = output_format.lower()
        if fmt == "excel":
            excel_filename = f"CRUD_visualization_{project_name}_{timestamp}.xlsx"
            excel_filepath = os.path.join(output_dir, excel_filename)
            if _save_crud_matrix_as_excel(result, project_name, excel_filepath):
                click.echo(f"CRUD visualization (Excel) saved to: {excel_filepath}")
            else:
                click.echo("Failed to save Excel file.")
        else:
            image_filename = f"CRUD_visualization_{project_name}_{timestamp}.{fmt}"
            image_filepath = os.path.join(output_dir, image_filename)
            if _save_crud_matrix_as_image(result, project_name, image_filepath, fmt):
                click.echo(f"CRUD visualization ({fmt.upper()}) saved to: {image_filepath}")
            else:
                click.echo(f"Failed to save {fmt.upper()} file.")

        summary = result.get("summary", {})
        class_matrix = summary.get("class_matrix", [])
        table_matrix = summary.get("table_matrix", [])

        click.echo("=" * 50)
        click.echo("CRUD MATRIX SUMMARY")
        click.echo("=" * 50)
        click.echo(f"Total classes: {len(class_matrix)}")
        click.echo(f"Total tables: {len(table_matrix)}")

        if class_matrix:
            click.echo("\nClasses with database operations:")
            for class_data in class_matrix[:10]:
                class_name = class_data.get("class_name", "Unknown")
                tables = class_data.get("tables", [])
                table_count = len(tables) if isinstance(tables, list) else 0
                click.echo(f"  - {class_name}: {table_count} tables")
            if len(class_matrix) > 10:
                click.echo(f"  ... and {len(class_matrix) - 10} more classes")
    except Exception as exc:  # pylint: disable=broad-except
        click.echo(f"Error generating diagram: {exc}")
    finally:
        if driver:
            driver.close()


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

    neo4j_password = _ensure_password()
    if not neo4j_password:
        return

    driver = None
    try:
        neo4j_database = os.getenv("NEO4J_DATABASE", "neo4j")
        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        analysis_service = DBCallAnalysisService(driver)

        click.echo("Table Impact Analysis")
        click.echo("=" * 50)
        click.echo(f"Analyzing impact of changes to table: {table_name}")

        result = analysis_service.analyze_table_impact(project_name, table_name)

        if auto_create_relationships and ("error" in result or not result.get("impacted_classes")):
            click.echo("No impact analysis found. Creating Method-SqlStatement relationships...")
            graph_db = GraphDB(neo4j_uri, neo4j_user, neo4j_password, neo4j_database)
            relationships_created = graph_db.create_method_sql_relationships(project_name)
            if relationships_created:
                click.echo(f"Created {relationships_created} Method-SqlStatement relationships.")
                result = analysis_service.analyze_table_impact(project_name, table_name)
            else:
                click.echo("No relationships could be created.")

        if "error" in result:
            click.echo(f"Error: {result['error']}")
            return

        impacted_classes = result["impacted_classes"]
        summary = result["summary"]

        click.echo("\nImpact Summary:")
        click.echo(f"  Table: {summary['table_name']}")
        click.echo(f"  Impacted classes: {summary['total_impacted_classes']}")
        click.echo(f"  Impacted methods: {summary['total_impacted_methods']}")
        click.echo(f"  SQL statements: {summary['total_sql_statements']}")
        click.echo(f"  CRUD operations: {', '.join(summary['crud_operations'])}")

        if summary["high_complexity_sql"]:
            click.echo(f"  High complexity SQL: {len(summary['high_complexity_sql'])}")

        if impacted_classes:
            click.echo("\nImpacted Classes:")
            click.echo("-" * 80)
            click.echo(f"{'Class':<25} {'Method':<25} {'SQL Type':<10} {'Complexity':<12}")
            click.echo("-" * 80)
            for cls in impacted_classes:
                class_name = cls["class_name"]
                method_name = cls["method_name"] or "N/A"
                sql_type = cls["sql_type"] or "N/A"
                complexity = str(cls["complexity_score"]) if cls["complexity_score"] else "N/A"
                click.echo(f"{class_name:<25} {method_name:<25} {sql_type:<10} {complexity:<12}")

        if summary["high_complexity_sql"]:
            click.echo("\nHigh Complexity SQL Statements:")
            click.echo("-" * 60)
            for sql in summary["high_complexity_sql"]:
                click.echo(
                    f"  {sql['class_name']}.{sql['method_name']} - {sql['sql_type']} (complexity: {sql['complexity_score']})"
                )

        if output_file:
            with open(output_file, "w", encoding="utf-8") as file:
                json.dump(result, file, indent=2, ensure_ascii=False)
            click.echo(f"\nImpact analysis saved to: {output_file}")
    except Exception as exc:  # pylint: disable=broad-except
        click.echo(f"Error analyzing table impact: {exc}")
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
