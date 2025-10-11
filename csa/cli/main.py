import os
import sys

import click
from dotenv import load_dotenv

# Ensure project root is on sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from csa.cli.commands.analyze import register as register_analyze
from csa.cli.commands.crud import register as register_crud_commands
from csa.cli.commands.db_calls import register as register_db_commands
from csa.cli.commands.graph_queries import register as register_graph_queries
from csa.cli.commands.sequence import register as register_sequence
from csa.services.neo4j_connection_pool import get_connection_pool

load_dotenv()


@click.group()
def cli():
    """CSA CLI entrypoint."""


register_graph_queries(cli)
register_sequence(cli)
register_crud_commands(cli)
register_db_commands(cli)
register_analyze(cli)


if __name__ == "__main__":
    try:
        cli()
    finally:
        pool = get_connection_pool()
        if pool.is_initialized():
            pool.close_all()
