"""
클래스 명세서 생성 CLI 명령어
"""
import os

import click

from csa.cli.core.lifecycle import with_command_lifecycle
from csa.dbwork.connection_pool import get_connection_pool
from csa.models.class_spec import ClassSpecOptions
from csa.services.class_spec.generator import ClassSpecGenerator
from csa.utils.logger import set_command_context


@click.command(name="class-spec")
@click.option("--neo4j-uri", default=os.getenv("NEO4J_URI", "bolt://localhost:7687"), help="Neo4j URI")
@click.option("--neo4j-user", default=os.getenv("NEO4J_USER", "neo4j"), help="Neo4j username")
@click.option("--neo4j-database", default=os.getenv("NEO4J_DATABASE", "neo4j"), help="Neo4j database name")
@click.option("--project-name", required=True, help="Project name for database analysis")
@click.option("--class-name", required=True, help="Name of the class to generate specification (simple name or FQCN)")
@click.option(
    "--output-dir",
    default=os.getenv("CLASS_SPEC_OUTPUT_DIR", "output/class-spec"),
    help="Output directory for class specifications",
)
@click.option("--include-diagram", is_flag=True, default=False, help="Include class diagram (not implemented yet)")
@click.option("--include-crud-info", is_flag=True, default=True, help="Include CRUD information (default: True)")
@with_command_lifecycle("class-spec")
def class_spec_command(
    neo4j_uri,
    neo4j_user,
    neo4j_database,
    project_name,
    class_name,
    output_dir,
    include_diagram,
    include_crud_info,
):
    """Generate class specification document."""
    # 명령어 실행 직전에 컨텍스트 설정 (모든 로거가 같은 파일 사용)
    set_command_context("class-spec")

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

    try:
        with pool.connection() as conn:
            generator = ClassSpecGenerator(conn.driver, database=conn.database)

            click.echo("=" * 80)
            click.echo("Class Specification Generator")
            click.echo("=" * 80)
            click.echo(f"Project: {project_name}")
            click.echo(f"Class: {class_name}")
            click.echo(f"Output Directory: {output_dir}")
            click.echo(f"Include CRUD Info: {include_crud_info}")
            click.echo("")

            # 옵션 구성
            options = ClassSpecOptions(
                project_name=project_name,
                class_name=class_name,
                output_dir=output_dir,
                include_diagram=include_diagram,
                include_crud_info=include_crud_info,
            )

            # 명세서 생성
            gen_result = generator.generate_spec(options)

            if gen_result["success"]:
                click.echo("")
                click.echo("✓ Specification generated successfully!")
                click.echo("")
                click.echo(f"File saved to: {gen_result['file_path']}")
                click.echo("")
                click.echo("Summary:")
                stats = gen_result["stats"]
                click.echo(f"  - Class Name: {stats.get('class_name', 'N/A')}")
                click.echo(f"  - Package: {stats.get('package_name', 'N/A')}")
                click.echo(f"  - Type: {stats.get('type', 'N/A')}")
                click.echo(f"  - Sub Type: {stats.get('sub_type', 'N/A')}")
                click.echo(f"  - Methods: {stats.get('methods_count', 0)}")
                click.echo(f"  - Fields: {stats.get('fields_count', 0)}")
                click.echo(f"  - Dependencies: {stats.get('dependencies_count', 0)}")
                click.echo(f"  - Tables Used: {stats.get('tables_count', 0)}")

                result["success"] = True
                result["message"] = gen_result["message"]
                result["files"].append(gen_result["file_path"])
                result["stats"] = stats
            else:
                click.echo("")
                click.echo(f"✗ Failed to generate specification: {gen_result['message']}")
                result["error"] = gen_result["message"]

    except Exception as exc:
        click.echo(f"Error: {exc}")
        result["error"] = str(exc)
    finally:
        pool.close_all()

    return result


def register(cli: click.Group) -> None:
    """Attach class-spec command to the given CLI group."""
    cli.add_command(class_spec_command)


__all__ = ["register"]
