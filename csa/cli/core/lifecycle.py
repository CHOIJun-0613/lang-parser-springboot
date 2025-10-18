import os
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, Optional

from csa.dbwork.connection_pool import get_connection_pool
from csa.utils.logger import get_logger, set_command_context


def format_duration(seconds: float) -> str:
    """초 단위 값을 HH:MM:SS 형태로 변환합니다."""
    seconds = max(0, int(seconds))
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    remaining_seconds = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{remaining_seconds:02d}"


def format_number(value: int) -> str:
    """숫자를 천 단위 구분 기호가 있는 문자열로 반환합니다."""
    return f"{value:,}"


def start(command_name: str) -> Dict[str, Any]:
    """
    CLI 명령 실행 전 호출되는 공통 초기화 함수.

    Args:
        command_name: 실행할 명령 이름 (예: 'analyze', 'crud-matrix')

    Returns:
        dict: 시작 시간, 로거, 커넥션 풀 등의 컨텍스트 정보
    """
    # 전역 컨텍스트 설정: 모든 서브 모듈의 로거가 동일한 로그 파일을 사용하도록 함
    set_command_context(command_name)

    start_time = datetime.now()
    logger = get_logger(__name__, command=command_name)

    # 규칙 매니저 초기화 로그 출력 (명령어별 로그 파일에 기록)
    try:
        from csa.utils.rules_manager import rules_manager
        logger.info("규칙 매니저 초기화 완료")
    except Exception as e:
        logger.warning(f"규칙 매니저 초기화 실패: {e}")

    logger.info("")
    logger.info(f"====== {command_name} 작업 시작 ======")

    pool = get_connection_pool()
    if not pool.is_initialized():
        neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        neo4j_password = os.getenv("NEO4J_PASSWORD")
        neo4j_database = os.getenv("NEO4J_DATABASE", "neo4j")
        pool_size = int(os.getenv("NEO4J_POOL_SIZE", "10"))

        if neo4j_password:
            pool.initialize(neo4j_uri, neo4j_user, neo4j_password, neo4j_database, pool_size)
            logger.info(f"Connection pool initialized with {pool_size} connections")
        else:
            logger.warning("NEO4J_PASSWORD not set - connection pool not initialized")

    return {
        "start_time": start_time,
        "logger": logger,
        "pool": pool,
        "command_name": command_name,
    }


def end(context: Dict[str, Any], result: Optional[Dict[str, Any]] = None) -> None:
    """
    CLI 명령 실행 후 호출되는 공통 정리 함수.

    Args:
        context: start()에서 반환된 컨텍스트
        result: 명령 함수가 반환한 결과 (선택)
    """
    end_time = datetime.now()
    logger = context.get("logger")
    command_name = context.get("command_name", "unknown")
    start_time = context.get("start_time")

    # 에러가 발생한 경우에만 로그 출력
    if result and not result.get("success"):
        logger.error(f"작업 실패: {result.get('error', 'Unknown error')}")


def with_command_lifecycle(command_name: str) -> Callable[[Callable[..., Any]], Callable[..., Dict[str, Any]]]:
    """
    CLI 명령 실행 전후 초기화/종료 처리를 담당하는 데코레이터.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Dict[str, Any]]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Dict[str, Any]:
            context = start(command_name)

            result: Dict[str, Any] = {
                "success": False,
                "message": "",
                "stats": {},
                "error": None,
            }

            try:
                func_result = func(*args, **kwargs)

                if isinstance(func_result, dict):
                    result.update(func_result)
                else:
                    result["success"] = True
                    result["message"] = "Success"
            except Exception as exc:  # pylint: disable=broad-except
                logger = context.get("logger")
                if logger:
                    logger.exception("명령 실행 중 오류가 발생했습니다.")
                result["success"] = False
                result["error"] = str(exc)
            finally:
                end(context, result)

            return result

        return wrapper

    return decorator


__all__ = [
    "format_duration",
    "format_number",
    "start",
    "end",
    "with_command_lifecycle",
]
