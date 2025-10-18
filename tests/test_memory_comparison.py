"""
메모리 사용량 비교 테스트

스트리밍 모드와 배치 모드의 메모리 사용량을 비교합니다.
"""
import os
import psutil
import time
from csa.services.graph_db import GraphDB
from csa.utils.logger import get_logger

logger = get_logger(__name__)


def get_memory_usage_mb():
    """현재 프로세스의 메모리 사용량을 MB 단위로 반환"""
    process = psutil.Process()
    mem_info = process.memory_info()
    return mem_info.rss / (1024 * 1024)  # bytes → MB


def test_streaming_mode():
    """스트리밍 모드 메모리 사용량 측정"""
    from csa.services.java_analysis.project import parse_java_project_streaming

    logger.info("=" * 80)
    logger.info("스트리밍 모드 메모리 사용량 측정 시작")
    logger.info("=" * 80)

    # 시작 메모리
    mem_start = get_memory_usage_mb()
    logger.info(f"시작 메모리: {mem_start:.2f} MB")

    # Neo4j 연결
    db = GraphDB(
        uri=os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687"),
        user=os.getenv("NEO4J_USER", "csauser"),
        password=os.getenv("NEO4J_PASSWORD", "csauser123"),
        database=os.getenv("NEO4J_DATABASE", "csadb01"),
    )

    # Java 소스 폴더
    java_source = os.getenv("JAVA_SOURCE_FOLDER", "target_src/car-center-devlab")
    project_name = "car-center-devlab"

    # 스트리밍 파싱 실행
    time_start = time.time()
    stats = parse_java_project_streaming(java_source, db, project_name)
    time_end = time.time()

    # 종료 메모리
    mem_end = get_memory_usage_mb()
    mem_delta = mem_end - mem_start
    elapsed_time = time_end - time_start

    logger.info("")
    logger.info("=" * 80)
    logger.info("스트리밍 모드 결과")
    logger.info("=" * 80)
    logger.info(f"종료 메모리: {mem_end:.2f} MB")
    logger.info(f"메모리 증가량: {mem_delta:.2f} MB")
    logger.info(f"처리 시간: {elapsed_time:.2f}초")
    logger.info(f"처리된 클래스: {stats['classes']}개")
    logger.info(f"처리된 Bean: {stats['beans']}개")
    logger.info("=" * 80)

    db.close()

    return {
        'mem_start': mem_start,
        'mem_end': mem_end,
        'mem_delta': mem_delta,
        'elapsed_time': elapsed_time,
        'classes': stats['classes'],
    }


def test_batch_mode():
    """배치 모드 메모리 사용량 측정"""
    from csa.services.java_analysis.project import parse_java_project_full

    logger.info("")
    logger.info("=" * 80)
    logger.info("배치 모드 메모리 사용량 측정 시작")
    logger.info("=" * 80)

    # 시작 메모리
    mem_start = get_memory_usage_mb()
    logger.info(f"시작 메모리: {mem_start:.2f} MB")

    # Java 소스 폴더
    java_source = os.getenv("JAVA_SOURCE_FOLDER", "target_src/car-center-devlab")

    # 배치 파싱 실행
    time_start = time.time()
    result = parse_java_project_full(java_source)
    time_end = time.time()

    # 결과 unpacking
    (
        packages_to_add,
        classes_to_add,
        class_to_package_map,
        beans,
        dependencies,
        endpoints,
        mybatis_mappers,
        jpa_entities,
        jpa_repositories,
        jpa_queries,
        config_files,
        test_classes,
        sql_statements,
        detected_project_name,
    ) = result

    # 종료 메모리
    mem_end = get_memory_usage_mb()
    mem_delta = mem_end - mem_start
    elapsed_time = time_end - time_start

    logger.info("")
    logger.info("=" * 80)
    logger.info("배치 모드 결과")
    logger.info("=" * 80)
    logger.info(f"종료 메모리: {mem_end:.2f} MB")
    logger.info(f"메모리 증가량: {mem_delta:.2f} MB")
    logger.info(f"처리 시간: {elapsed_time:.2f}초")
    logger.info(f"처리된 클래스: {len(classes_to_add)}개")
    logger.info(f"처리된 Bean: {len(beans)}개")
    logger.info("=" * 80)

    return {
        'mem_start': mem_start,
        'mem_end': mem_end,
        'mem_delta': mem_delta,
        'elapsed_time': elapsed_time,
        'classes': len(classes_to_add),
    }


def main():
    """메인 함수"""
    logger.info("\n\n")
    logger.info("╔" + "=" * 78 + "╗")
    logger.info("║" + " " * 20 + "메모리 사용량 비교 테스트" + " " * 32 + "║")
    logger.info("╚" + "=" * 78 + "╝")
    logger.info("")

    # 1. 스트리밍 모드 테스트
    streaming_result = test_streaming_mode()

    # 2. 배치 모드 테스트
    batch_result = test_batch_mode()

    # 3. 비교 결과
    logger.info("")
    logger.info("╔" + "=" * 78 + "╗")
    logger.info("║" + " " * 30 + "비교 결과" + " " * 38 + "║")
    logger.info("╚" + "=" * 78 + "╝")
    logger.info("")
    logger.info(f"{'항목':<20} {'스트리밍 모드':>15} {'배치 모드':>15} {'차이':>15}")
    logger.info("-" * 80)
    logger.info(
        f"{'메모리 증가량 (MB)':<20} {streaming_result['mem_delta']:>15.2f} "
        f"{batch_result['mem_delta']:>15.2f} "
        f"{batch_result['mem_delta'] - streaming_result['mem_delta']:>15.2f}"
    )
    logger.info(
        f"{'처리 시간 (초)':<20} {streaming_result['elapsed_time']:>15.2f} "
        f"{batch_result['elapsed_time']:>15.2f} "
        f"{batch_result['elapsed_time'] - streaming_result['elapsed_time']:>15.2f}"
    )
    logger.info(
        f"{'처리된 클래스 (개)':<20} {streaming_result['classes']:>15} "
        f"{batch_result['classes']:>15} "
        f"{batch_result['classes'] - streaming_result['classes']:>15}"
    )

    # 메모리 감소율
    mem_reduction_percent = (
        (batch_result['mem_delta'] - streaming_result['mem_delta'])
        / batch_result['mem_delta'] * 100
    )
    logger.info("")
    logger.info(f"메모리 감소율: {mem_reduction_percent:.1f}%")
    logger.info("")
    logger.info("╚" + "=" * 78 + "╝")


if __name__ == "__main__":
    main()
