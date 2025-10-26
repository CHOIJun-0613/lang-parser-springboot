import json
import os

import click
from neo4j import GraphDatabase

from csa.cli.core.lifecycle import with_command_lifecycle
from csa.cli.core.storage import convert_to_image
from csa.services.db_call_analysis import DBCallAnalysisService
from csa.services.graph_db import GraphDB
from csa.utils.logger import get_logger, set_command_context


def _ensure_password() -> str | None:
    logger = get_logger(__name__)
    password = os.getenv("NEO4J_PASSWORD")
    if not password:
        logger.error("Error: NEO4J_PASSWORD environment variable is not set.")
        logger.error("Please set NEO4J_PASSWORD in your .env file or environment variables.")
    return password


@click.command(name="db-analysis")
@click.option("--neo4j-uri", default=os.getenv("NEO4J_URI", "bolt://localhost:7687"), help="Neo4j URI")
@click.option("--neo4j-user", default=os.getenv("NEO4J_USER", "neo4j"), help="Neo4j username")
@click.option("--project-name", required=True, help="Project name to analyze")
@click.option(
    "--auto-create-relationships",
    is_flag=True,
    default=True,
    help="Automatically create Method-SqlStatement relationships if needed (default: True)",
)
@with_command_lifecycle("db-analysis")
def db_analysis_command(neo4j_uri, neo4j_user, project_name, auto_create_relationships):
    """Show database call relationship statistics."""

    set_command_context("db-analysis")
    logger = get_logger(__name__, command="db-analysis")

    neo4j_password = _ensure_password()
    if not neo4j_password:
        return

    driver = None
    try:
        neo4j_database = os.getenv("NEO4J_DATABASE", "neo4j")
        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        db = GraphDB(neo4j_uri, neo4j_user, neo4j_password, neo4j_database)

        logger.info("Database Call Relationship Analysis")
        logger.info("=" * 80)

        sql_stats = db.get_sql_statistics(project_name)
        if not sql_stats and auto_create_relationships:
            logger.info("No SQL statistics found. Creating Method-SqlStatement relationships...")
            relationships_created = db.create_method_sql_relationships(project_name)
            if relationships_created:
                logger.info(f"Created {relationships_created} Method-SqlStatement relationships.")
                sql_stats = db.get_sql_statistics(project_name)
            else:
                logger.info("No relationships could be created.")

        if sql_stats:
            logger.info("\nSQL Statistics:")
            logger.info(f"  Total SQL statements: {sql_stats['total_sql']}")
            logger.info(f"  SELECT statements: {sql_stats.get('SELECT', 0)}")
            logger.info(f"  INSERT statements: {sql_stats.get('INSERT', 0)}")
            logger.info(f"  UPDATE statements: {sql_stats.get('UPDATE', 0)}")
            logger.info(f"  DELETE statements: {sql_stats.get('DELETE', 0)}")

        table_stats = db.get_table_usage_statistics(project_name)
        if table_stats:
            logger.info("\nTable Usage Statistics:")
            logger.info(f"{'Table Name':<30} {'Access Count':<15} {'Operations':<20}")
            logger.info("-" * 65)
            for table in table_stats:
                logger.info(
                    f"{table['table_name']:<30} {table['access_count']:<15} {', '.join(table['operations']):<20}"
                )

        complexity_stats = db.get_sql_complexity_statistics(project_name)
        if complexity_stats:
            logger.info("\nSQL Complexity Analysis:")
            logger.info(f"  Simple queries: {complexity_stats.get('simple', 0)}")
            logger.info(f"  Medium queries: {complexity_stats.get('medium', 0)}")
            logger.info(f"  Complex queries: {complexity_stats.get('complex', 0)}")
            logger.info(f"  Very complex queries: {complexity_stats.get('very_complex', 0)}")

        mapper_stats = db.get_mapper_sql_distribution(project_name)
        if mapper_stats:
            logger.info("\nMapper SQL Distribution:")
            logger.info(f"{'Mapper Name':<30} {'SQL Count':<15} {'SQL Types':<20}")
            logger.info("-" * 65)
            for mapper in mapper_stats:
                logger.info(
                    f"{mapper['mapper_name']:<30} {mapper['sql_count']:<15} {', '.join(mapper['sql_types']):<20}"
                )
    except Exception as exc:  # pylint: disable=broad-except
        logger.error(f"Error getting database analysis: {exc}")
    finally:
        if driver:
            driver.close()


@click.command(name="db-call-chain")
@click.option("--neo4j-uri", default=os.getenv("NEO4J_URI", "bolt://localhost:7687"), help="Neo4j URI")
@click.option("--neo4j-user", default=os.getenv("NEO4J_USER", "neo4j"), help="Neo4j username")
@click.option("--project-name", required=True, help="Project name to analyze")
@click.option("--start-class", help="Class name to start the call chain from")
@click.option("--start-method", help="Method name to start the call chain from")
@click.option("--output-file", help="Output file to save the call chain diagram (Markdown)")
@click.option("--output-image", help="Optional image path to export the diagram")
@click.option("--image-format", default="png", help="Image format when exporting (default: png)")
@click.option("--image-width", default=1200, help="Image width in pixels (default: 1200)")
@click.option("--image-height", default=800, help="Image height in pixels (default: 800)")
@click.option(
    "--auto-create-relationships",
    is_flag=True,
    default=True,
    help="Automatically create Method-SqlStatement relationships if needed (default: True)",
)
@with_command_lifecycle("db-call-chain")
def db_call_chain_command(
    neo4j_uri,
    neo4j_user,
    project_name,
    start_class,
    start_method,
    output_file,
    output_image,
    image_format,
    image_width,
    image_height,
    auto_create_relationships,
):
    """Analyze database call chain relationships."""

    set_command_context("db-call-chain")
    logger = get_logger(__name__, command="db-call-chain")

    neo4j_password = _ensure_password()
    if not neo4j_password:
        return

    driver = None
    try:
        neo4j_database = os.getenv("NEO4J_DATABASE", "neo4j")
        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        analysis_service = DBCallAnalysisService(driver)

        logger.info("Database Call Chain Analysis")
        logger.info("=" * 50)
        if start_class and start_method:
            logger.info(f"Analyzing call chain from {start_class}.{start_method}")
        elif start_class:
            logger.info(f"Analyzing call chain from class {start_class}")
        else:
            logger.info(f"Analyzing call chain for project {project_name}")

        result = analysis_service.analyze_call_chain(project_name, start_class, start_method)

        if auto_create_relationships and ("error" in result or not result.get("diagram")):
            logger.info("No call chain found. Creating Method-SqlStatement relationships...")
            graph_db = GraphDB(neo4j_uri, neo4j_user, neo4j_password, neo4j_database)
            relationships_created = graph_db.create_method_sql_relationships(project_name)
            if relationships_created:
                logger.info(f"Created {relationships_created} Method-SqlStatement relationships.")
                result = analysis_service.analyze_call_chain(project_name, start_class, start_method)
            else:
                logger.info("No relationships could be created.")

        if "error" in result or not result.get("diagram"):
            logger.error(f"Error: {result.get('error', 'No call chain data found')}")
            return

        diagram = result["diagram"]
        if output_file:
            with open(output_file, "w", encoding="utf-8") as file:
                file.write(diagram)
            logger.info(f"Diagram saved to: {output_file}")
        else:
            default_filename = f"db_call_chain_{project_name}.md"
            with open(default_filename, "w", encoding="utf-8") as file:
                file.write(diagram)
            logger.info(f"Diagram saved to: {default_filename}")

        if output_image:
            convert_to_image(diagram, output_image, image_format, image_width, image_height)

        logger.info("\n" + "=" * 50)
        logger.info("DATABASE CALL CHAIN DIAGRAM")
        logger.info("=" * 50)
        logger.info(diagram)
        logger.info("=" * 50)
    except Exception as exc:  # pylint: disable=broad-except
        logger.error(f"Error generating diagram: {exc}")
    finally:
        if driver:
            driver.close()


@click.command(name="db-call-diagram")
@click.option("--neo4j-uri", default=os.getenv("NEO4J_URI", "bolt://localhost:7687"), help="Neo4j URI")
@click.option("--neo4j-user", default=os.getenv("NEO4J_USER", "neo4j"), help="Neo4j username")
@click.option("--project-name", required=True, help="Project name to analyze")
@click.option("--output-file", help="Output file to save the diagram (Markdown)")
@click.option("--output-image", help="Optional image path to export the diagram")
@click.option("--image-format", default="png", help="Image format when exporting (default: png)")
@click.option("--image-width", default=1200, help="Image width in pixels (default: 1200)")
@click.option("--image-height", default=800, help="Image height in pixels (default: 800)")
@with_command_lifecycle("db-call-diagram")
def db_call_diagram_command(
    neo4j_uri,
    neo4j_user,
    project_name,
    output_file,
    output_image,
    image_format,
    image_width,
    image_height,
):
    """Generate database call chain diagram for the project."""

    set_command_context("db-call-diagram")
    logger = get_logger(__name__, command="db-call-diagram")

    neo4j_password = _ensure_password()
    if not neo4j_password:
        return

    driver = None
    try:
        neo4j_database = os.getenv("NEO4J_DATABASE", "neo4j")
        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        analysis_service = DBCallAnalysisService(driver)

        logger.info("Generating database call chain diagram...")
        diagram = analysis_service.generate_db_call_diagram(project_name)

        if output_file:
            with open(output_file, "w", encoding="utf-8") as file:
                file.write(diagram)
            logger.info(f"Diagram saved to: {output_file}")
        else:
            default_filename = f"db_call_diagram_{project_name}.md"
            with open(default_filename, "w", encoding="utf-8") as file:
                file.write(diagram)
            logger.info(f"Diagram saved to: {default_filename}")

        if output_image:
            convert_to_image(diagram, output_image, image_format, image_width, image_height)

        logger.info("\n" + "=" * 50)
        logger.info("DATABASE CALL DIAGRAM")
        logger.info("=" * 50)
        logger.info(diagram)
        logger.info("=" * 50)
    except Exception as exc:  # pylint: disable=broad-except
        logger.error(f"Error generating call diagram: {exc}")
    finally:
        if driver:
            driver.close()


@click.command(name="db-statistics")
@click.option("--neo4j-uri", default=os.getenv("NEO4J_URI", "bolt://localhost:7687"), help="Neo4j URI")
@click.option("--neo4j-user", default=os.getenv("NEO4J_USER", "neo4j"), help="Neo4j username")
@click.option("--project-name", required=True, help="Project name to analyze")
@click.option("--output-file", help="Output file to save the statistics (optional)")
@click.option(
    "--auto-create-relationships",
    is_flag=True,
    default=True,
    help="Automatically create Method-SqlStatement relationships if needed (default: True)",
)
@with_command_lifecycle("db-statistics")
def db_statistics_command(neo4j_uri, neo4j_user, project_name, output_file, auto_create_relationships):
    """Show database usage statistics."""

    set_command_context("db-statistics")
    logger = get_logger(__name__, command="db-statistics")

    neo4j_password = _ensure_password()
    if not neo4j_password:
        return

    driver = None
    try:
        neo4j_database = os.getenv("NEO4J_DATABASE", "neo4j")
        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        analysis_service = DBCallAnalysisService(driver)

        logger.info("Database Usage Statistics")
        logger.info("=" * 50)

        result = analysis_service.get_database_usage_statistics(project_name)

        if auto_create_relationships and ("error" in result or not result.get("sql_statistics")):
            logger.info("No database statistics found. Creating Method-SqlStatement relationships...")
            graph_db = GraphDB(neo4j_uri, neo4j_user, neo4j_password, neo4j_database)
            relationships_created = graph_db.create_method_sql_relationships(project_name)
            if relationships_created:
                logger.info(f"Created {relationships_created} Method-SqlStatement relationships.")
                result = analysis_service.get_database_usage_statistics(project_name)
            else:
                logger.info("No relationships could be created.")

        if "error" in result:
            logger.error(f"Error: {result['error']}")
            return

        sql_stats = result.get("sql_statistics")
        table_usage = result.get("table_usage")
        complexity_stats = result.get("complexity_statistics")

        if sql_stats:
            logger.info("\nSQL Statistics:")
            logger.info(f"  Total SQL statements: {sql_stats['total_sql']}")
            logger.info(f"  SELECT statements: {sql_stats.get('SELECT', 0)}")
            logger.info(f"  INSERT statements: {sql_stats.get('INSERT', 0)}")
            logger.info(f"  UPDATE statements: {sql_stats.get('UPDATE', 0)}")
            logger.info(f"  DELETE statements: {sql_stats.get('DELETE', 0)}")

        if table_usage:
            logger.info("\nTable Usage Statistics:")
            logger.info("-" * 60)
            logger.info(f"{'Table Name':<30} {'Access Count':<15} {'Operations':<20}")
            logger.info("-" * 60)
            for table in table_usage:
                logger.info(
                    f"{table['table_name']:<30} {table['access_count']:<15} {', '.join(table['operations']):<20}"
                )

        if complexity_stats:
            logger.info("\nSQL Complexity Statistics:")
            logger.info(f"  Simple queries: {complexity_stats.get('simple', 0)}")
            logger.info(f"  Medium queries: {complexity_stats.get('medium', 0)}")
            logger.info(f"  Complex queries: {complexity_stats.get('complex', 0)}")
            logger.info(f"  Very complex queries: {complexity_stats.get('very_complex', 0)}")

        if output_file:
            with open(output_file, "w", encoding="utf-8") as file:
                json.dump(result, file, indent=2, ensure_ascii=False)
            logger.info(f"\nStatistics saved to: {output_file}")
    except Exception as exc:  # pylint: disable=broad-except
        logger.error(f"Error getting database statistics: {exc}")
    finally:
        if driver:
            driver.close()


def register(cli: click.Group) -> None:
    """Attach DB-call related commands to the given CLI group."""

    cli.add_command(db_analysis_command)
    cli.add_command(db_call_chain_command)
    cli.add_command(db_call_diagram_command)
    cli.add_command(db_statistics_command)


__all__ = ["register"]
