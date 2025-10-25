"""
AI Enrichment command - Add AI-generated descriptions to existing Neo4j nodes
"""
import os
from datetime import datetime

import click

from csa.cli.core.lifecycle import with_command_lifecycle
from csa.services.graph_db import GraphDB
from csa.utils.logger import get_logger, set_command_context


def _ensure_password() -> str | None:
    password = os.getenv("NEO4J_PASSWORD")
    if not password:
        click.echo("Error: NEO4J_PASSWORD environment variable is not set.")
        click.echo("Please set NEO4J_PASSWORD in your .env file or environment variables.")
    return password


@click.command(name="ai-enrich")
@click.option("--neo4j-uri", default=os.getenv("NEO4J_URI", "bolt://localhost:7687"), help="Neo4j URI")
@click.option("--neo4j-user", default=os.getenv("NEO4J_USER", "neo4j"), help="Neo4j username")
@click.option("--neo4j-database", default=os.getenv("NEO4J_DATABASE", "neo4j"), help="Neo4j database name")
@click.option("--project-name", required=True, help="Project name to enrich")
@click.option(
    "--node-type",
    default="all",
    type=click.Choice(["all", "class", "method", "sql"], case_sensitive=False),
    help="Node type to enrich (default: all)",
)
@click.option(
    "--batch-size",
    default=int(os.getenv("AI_ENRICHMENT_BATCH_SIZE", "50")),
    help="Batch size for processing (default: 50 or AI_ENRICHMENT_BATCH_SIZE env var)",
)
@click.option(
    "--limit",
    default=None,
    type=int,
    help="Maximum number of nodes to process (default: all)",
)
@with_command_lifecycle("ai-enrich")
def ai_enrich_command(neo4j_uri, neo4j_user, neo4j_database, project_name, node_type, batch_size, limit):
    """Add AI-generated descriptions to existing Neo4j nodes without ai_description."""

    # 명령어 실행 직전에 컨텍스트 설정
    set_command_context("ai-enrich")
    logger = get_logger(__name__, command="ai-enrich")

    result = {"success": False, "message": "", "stats": {}, "error": None}

    neo4j_password = _ensure_password()
    if not neo4j_password:
        result["error"] = "NEO4J_PASSWORD not set"
        return result

    # AI 분석기 가용성 확인
    try:
        from csa.aiwork.ai_analyzer import get_ai_analyzer
        analyzer = get_ai_analyzer()
        if not analyzer.is_available():
            result["error"] = "AI analyzer is not available. Please check your AI configuration in .env file."
            click.echo(result["error"])
            return result
    except Exception as exc:
        result["error"] = f"Failed to initialize AI analyzer: {exc}"
        click.echo(result["error"])
        return result

    try:
        db = GraphDB(neo4j_uri, neo4j_user, neo4j_password, neo4j_database)

        click.echo("=" * 80)
        click.echo("AI Enrichment - Add AI descriptions to existing nodes")
        click.echo("=" * 80)
        click.echo(f"Project: {project_name}")
        click.echo(f"Node type: {node_type}")
        click.echo(f"Batch size: {batch_size}")
        if limit:
            click.echo(f"Limit: {limit} nodes")
        click.echo("")

        start_time = datetime.now()

        # AI enrichment 서비스 임포트 및 실행
        from csa.services.ai_enrichment_service import AIEnrichmentService

        enrichment_service = AIEnrichmentService(db, analyzer, logger)

        stats = enrichment_service.enrich_project(
            project_name=project_name,
            node_type=node_type,
            batch_size=batch_size,
            limit=limit
        )

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        click.echo("")
        click.echo("=" * 80)
        click.echo("AI Enrichment Summary")
        click.echo("=" * 80)
        click.echo(f"Total nodes processed: {stats['total_processed']}")
        click.echo(f"Successfully enriched: {stats['success_count']}")
        click.echo(f"Failed: {stats['fail_count']}")
        click.echo(f"Skipped (already has ai_description): {stats['skipped_count']}")
        click.echo(f"Duration: {duration:.2f} seconds")

        if stats['success_count'] > 0:
            click.echo(f"Average time per node: {duration / stats['total_processed']:.2f} seconds")

        if stats['node_type_stats']:
            click.echo("")
            click.echo("By Node Type:")
            for node_type_name, type_stats in stats['node_type_stats'].items():
                click.echo(f"  {node_type_name}:")
                click.echo(f"    - Processed: {type_stats['processed']}")
                click.echo(f"    - Success: {type_stats['success']}")
                click.echo(f"    - Failed: {type_stats['failed']}")

        result["success"] = True
        result["message"] = "AI enrichment completed successfully"
        result["stats"] = stats

    except Exception as exc:
        logger.error(f"AI enrichment error: {exc}")
        result["error"] = str(exc)
        click.echo(f"Error during AI enrichment: {exc}")
    finally:
        if db:
            db.close()

    return result


def register(cli: click.Group) -> None:
    """Attach the ai-enrich command to the given CLI group."""
    cli.add_command(ai_enrich_command)


__all__ = ["register"]
