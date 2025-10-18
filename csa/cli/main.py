import os
import sys

import click
from dotenv import load_dotenv
from csa.utils.logger import set_command_context

# Ensure project root is on sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from csa.cli.commands.analyze import register as register_analyze
from csa.cli.commands.crud import register as register_crud_commands
from csa.cli.commands.db_calls import register as register_db_commands
from csa.cli.commands.graph_queries import register as register_graph_queries
from csa.cli.commands.sequence import register as register_sequence
from csa.dbwork.connection_pool import get_connection_pool

load_dotenv()

# 애플리케이션 시작 시 규칙 매니저 초기화 (로거는 수정 후 사용)
try:
    from csa.utils.rules_manager import rules_manager
except Exception as e:
    import sys
    print(f"Warning: 규칙 매니저 초기화 실패: {e}", file=sys.stderr)


@click.group()
@click.pass_context
def cli(ctx):
    """CSA CLI entrypoint."""
    # Click에서 호출된 명령어 이름을 컨텍스트에 저장
    # (이 시점에는 명령어가 결정되지 않았으므로, result_callback 사용)
    pass


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
