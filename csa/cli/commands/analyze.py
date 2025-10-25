import os
 
import click

from csa.cli.core.lifecycle import with_command_lifecycle
from csa.services.analyze_service import (
    analyze_project,
    get_or_determine_project_name,
    validate_analyze_options,
)
from csa.services.java_parser import extract_project_name
from csa.utils.logger import get_logger, set_command_context


@click.command(name="analyze")
@with_command_lifecycle("analyze")
@click.option("--java-source-folder", help="Path to Java source folder (default: current directory)")
@click.option("--project-name", help="Project name (if not provided, extracted from folder name)")
@click.option("--application-name", help="Application name for the project (optional)")
@click.option("--db-script-folder", help="Path to database script folder")
@click.option("--neo4j-uri", default=os.getenv("NEO4J_URI", "bolt://localhost:7687"), help="Neo4j URI")
@click.option("--neo4j-user", default=os.getenv("NEO4J_USER", "neo4j"), help="Neo4j username")
@click.option("--neo4j-password", default=os.getenv("NEO4J_PASSWORD"), help="Neo4j password")
@click.option("--neo4j-database", default=os.getenv("NEO4J_DATABASE", "neo4j"), help="Neo4j database name")
@click.option("--clean", is_flag=True, help="Clean database before analysis")
@click.option("--dry-run", is_flag=True, help="Parse without database connection")
@click.option("--java-object", is_flag=True, help="Analyze Java objects only")
@click.option("--db-object", is_flag=True, help="Analyze database objects only")
@click.option("--all-objects", is_flag=True, help="Analyze both Java and database objects")
@click.option("--class-name", help="Analyze specific class only")
@click.option("--update", is_flag=True, help="Update existing classes")
@click.option("--skip-ai", is_flag=True, help="Skip AI description generation (faster parsing)")
def analyze_command(
    java_source_folder,
    project_name,
    application_name,
    db_script_folder,
    neo4j_uri,
    neo4j_user,
    neo4j_password,
    neo4j_database,
    clean,
    dry_run,
    java_object,
    db_object,
    all_objects,
    class_name,
    update,
    skip_ai,
):
    """Analyze Java project and database objects."""

    # 명령어 실행 직전에 컨텍스트 설정 (모든 로거가 같은 파일 사용)
    set_command_context("analyze")

    logger = get_logger(__name__, command="analyze")

    if not java_source_folder:
        java_source_folder = os.getenv("JAVA_SOURCE_FOLDER", ".")
        logger.info(f"Using default Java source folder: {java_source_folder}")

    try:
        db_object, java_object, default_to_full = validate_analyze_options(
            db_object,
            java_object,
            class_name,
            update,
            java_source_folder,
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc

    if default_to_full:
        all_objects = True
        click.echo("No analysis type specified. Defaulting to full analysis (Java + DB objects).")
        click.echo("Use --db-object, --java-object, --all-objects, --class-name, or --update to specify analysis type.")

    detected_project_name = extract_project_name(java_source_folder)
    final_project_name = get_or_determine_project_name(
        project_name,
        detected_project_name,
        java_source_folder,
        logger,
    )

    # skip-ai 옵션 로깅 및 환경 변수 설정
    if skip_ai:
        os.environ["SKIP_AI_ANALYSIS"] = "true"
        logger.info("AI description generation is skipped (--skip-ai)")
    else:
        # 명시적으로 false로 설정 (기본값 보장)
        os.environ["SKIP_AI_ANALYSIS"] = "false"

    try:
        result = analyze_project(
            java_source_folder=java_source_folder,
            project_name=final_project_name,
            application_name=application_name,
            db_script_folder=db_script_folder,
            neo4j_uri=neo4j_uri,
            neo4j_user=neo4j_user,
            neo4j_password=neo4j_password,
            neo4j_database=neo4j_database,
            clean=clean,
            dry_run=dry_run,
            java_object=java_object,
            db_object=db_object,
            all_objects=all_objects,
            class_name=class_name,
            update=update,
            skip_ai=skip_ai,
            logger=logger,
        )
    except Exception as exc:  # pylint: disable=broad-except
        raise click.ClickException(str(exc)) from exc

    if not result.get("success", False):
        error_message = result.get("error") or "Analysis failed without error details."
        raise click.ClickException(error_message)

    return result


def register(cli: click.Group) -> None:
    """Attach the analyze command to the given CLI group."""
    cli.add_command(analyze_command)


__all__ = ["register"]
