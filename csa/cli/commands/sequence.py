import os
import traceback

import click

from csa.cli.core.lifecycle import with_command_lifecycle
from csa.dbwork.connection_pool import get_connection_pool
from csa.diagrams.sequence.generator import SequenceDiagramGenerator
from csa.utils.logger import set_command_context


@click.command(name="sequence")
@click.option("--neo4j-uri", default=os.getenv("NEO4J_URI", "bolt://localhost:7687"), help="Neo4j URI")
@click.option("--neo4j-user", default=os.getenv("NEO4J_USER", "neo4j"), help="Neo4j username")
@click.option("--neo4j-database", default=os.getenv("NEO4J_DATABASE", "neo4j"), help="Neo4j database name")
@click.option("--class-name", required=True, help="Name of the class to analyze")
@click.option("--method-name", help="Specific method to analyze (optional)")
@click.option("--max-depth", default=10, help="Maximum depth of call chain to follow (default: 10)")
@click.option("--include-external", is_flag=True, help="Include calls to external libraries")
@click.option("--project-name", help="Project name for database analysis (optional, auto-detected if omitted)")
@click.option(
    "--image-format",
    default="none",
    type=click.Choice(["none", "png", "svg", "pdf"]),
    help="Image format (default: none - no image generation)",
)
@click.option("--image-width", default=1200, help="Image width in pixels (default: 1200)")
@click.option("--image-height", default=800, help="Image height in pixels (default: 800)")
@click.option("--format", default="plantuml", type=click.Choice(["mermaid", "plantuml"]), help="Diagram format")
@click.option(
    "--output-dir",
    default=os.getenv("SEQUENCE_DIAGRAM_OUTPUT_DIR", "output/sequence-diagram"),
    help="Output directory for sequence diagrams",
)
@with_command_lifecycle("sequence")
def sequence_command(
    neo4j_uri,
    neo4j_user,
    neo4j_database,
    class_name,
    method_name,
    max_depth,
    include_external,
    project_name,
    image_format,
    image_width,
    image_height,
    format,  # pylint: disable=redefined-builtin
    output_dir,
):
    """Generate sequence diagram for a specific class and optionally a method."""
    # 명령어 실행 직전에 컨텍스트 설정 (모든 로거가 같은 파일 사용)
    set_command_context("sequence")

    result = {
        "success": False,
        "message": "",
        "stats": {},
        "error": None,
        "files": [],
    }

    neo4j_password = os.getenv("NEO4J_PASSWORD")
    if not neo4j_password:
        result["error"] = "NEO4J_PASSWORD environment variable is not set"
        click.echo("Error: NEO4J_PASSWORD environment variable is not set.")
        click.echo("Please set NEO4J_PASSWORD in your .env file or environment variables.")
        return result

    click.echo(f"Connecting to Neo4j at {neo4j_uri} (database: {neo4j_database})...")

    pool = get_connection_pool()
    if not pool.is_initialized():
        pool_size = int(os.getenv("NEO4J_POOL_SIZE", "10"))
        pool.initialize(neo4j_uri, neo4j_user, neo4j_password, neo4j_database, pool_size)

    generated_files: list[str] = []
    try:
        with pool.connection() as conn:
            generator = SequenceDiagramGenerator(conn.driver, format=format, database=conn.database)

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
                image_height=image_height,
            )

            if isinstance(diagram, str) and diagram.startswith("Error:"):
                click.echo(f"Error: {diagram}")
                result["error"] = diagram
                return result

            if isinstance(diagram, dict):
                if diagram.get("type") == "class":
                    click.echo(f"Generated {len(diagram['files'])} sequence diagram files for class '{class_name}':\n")
                    for file_info in diagram["files"]:
                        click.echo(f"- Diagram: {os.path.basename(file_info['diagram_path'])}")
                        if file_info["image_path"]:
                            click.echo(f"  Image: {os.path.basename(file_info['image_path'])}")

                    click.echo(f"\nFiles saved in: {diagram['output_dir']}/ directory")

                    for file_info in diagram["files"]:
                        generated_files.append(file_info["diagram_path"])
                        if file_info["image_path"]:
                            generated_files.append(file_info["image_path"])

                elif diagram.get("type") == "method":
                    click.echo(f"Generated sequence diagram for method '{method_name}':")
                    click.echo(f"- Diagram: {os.path.basename(diagram['diagram_path'])}")
                    if diagram["image_path"]:
                        click.echo(f"- Image: {os.path.basename(diagram['image_path'])}")

                    generated_files.append(diagram["diagram_path"])
                    if diagram["image_path"]:
                        generated_files.append(diagram["image_path"])
            else:
                click.echo(f"Diagram generated (length: {len(diagram)})")
                click.echo(diagram)

            result["success"] = True
            result["message"] = "Sequence diagram generated successfully"
            result["files"] = generated_files
            result["stats"] = {
                "class_name": class_name,
                "method_name": method_name,
                "max_depth": max_depth,
                "include_external": include_external,
                "format": format,
                "files_generated": len(generated_files),
            }
    except Exception as exc:  # pylint: disable=broad-except
        result["error"] = str(exc)
        click.echo(f"Error generating sequence diagram: {exc}")
        click.echo(f"Traceback: {traceback.format_exc()}")

    return result


def register(cli: click.Group) -> None:
    """Attach the sequence command to the given CLI group."""
    cli.add_command(sequence_command)


__all__ = ["register"]
