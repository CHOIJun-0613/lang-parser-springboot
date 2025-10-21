"""
영향도 분석 CLI 명령어

테이블 또는 메서드 변경 시 영향받는 코드 요소들을 역추적하여 분석
"""
import os
from datetime import datetime
from pathlib import Path

import click
from neo4j import GraphDatabase

from csa.cli.core.lifecycle import with_command_lifecycle
from csa.services.db_call_analysis.base import DBCallAnalysisBase
from csa.services.db_call_analysis.reverse_impact import ReverseImpactMixin
from csa.services.db_call_analysis.impact_reporter import ImpactReporter
from csa.utils.logger import set_command_context, get_logger


def _ensure_password() -> str | None:
    """Neo4j 비밀번호 환경 변수 확인"""
    password = os.getenv("NEO4J_PASSWORD")
    if not password:
        click.echo("Error: NEO4J_PASSWORD environment variable is not set.")
        click.echo("Please set NEO4J_PASSWORD in your .env file or environment variables.")
    return password


class ImpactAnalysisService(DBCallAnalysisBase, ReverseImpactMixin):
    """영향도 분석 서비스 (Mixin 조합)"""
    pass


@click.command(name="impact-analysis")
@click.option("--neo4j-uri", default=os.getenv("NEO4J_URI", "bolt://localhost:7687"), help="Neo4j URI")
@click.option("--neo4j-user", default=os.getenv("NEO4J_USER", "neo4j"), help="Neo4j username")
@click.option(
    "--table-name",
    default=None,
    help="테이블명 (테이블 영향도 분석 시 필수)",
)
@click.option(
    "--class-name",
    default=None,
    help="클래스명 (메서드 영향도 분석 시 필수)",
)
@click.option(
    "--method-name",
    default=None,
    help="메서드명 (선택사항, 생략 시 클래스의 모든 public 메서드 분석)",
)
@click.option(
    "--project-name",
    default=None,
    help="프로젝트명 (선택사항, 생략 시 전체 프로젝트 대상)",
)
@click.option(
    "--max-depth",
    default=10,
    type=int,
    help="최대 호출 깊이 (기본값: 10)",
)
@click.option(
    "--include-json",
    is_flag=True,
    default=False,
    help="JSON 형식 파일 추가 생성 (기본값: False, Markdown+Excel은 항상 생성)",
)
@click.option(
    "--generate-diagram",
    is_flag=True,
    default=False,
    help="Mermaid 다이어그램 생성 (기본값: False)",
)
@click.option(
    "--output-dir",
    default=None,
    help="출력 디렉터리 (기본값: 환경변수 IMPACT_ANALYSIS_OUTPUT_DIR 또는 ./output/impact-analysis)",
)
@with_command_lifecycle("impact-analysis")
def impact_analysis_command(
    neo4j_uri,
    neo4j_user,
    table_name,
    class_name,
    method_name,
    project_name,
    max_depth,
    include_json,
    generate_diagram,
    output_dir,
):
    """영향도 분석 (테이블 또는 메서드)

    Examples:
        # 테이블 영향도 분석
        python -m csa.cli.main impact-analysis --table-name USER

        # 특정 프로젝트의 테이블 영향도 분석 (JSON + 다이어그램 포함)
        python -m csa.cli.main impact-analysis --table-name USER --project-name myproject --include-json --generate-diagram

        # 메서드 영향도 분석 (다이어그램 포함)
        python -m csa.cli.main impact-analysis --class-name UserService --method-name getUser --project-name myproject --generate-diagram

        # 클래스의 모든 public 메서드 영향도 분석
        python -m csa.cli.main impact-analysis --class-name UserService --project-name myproject
    """
    # 명령어 컨텍스트 설정
    set_command_context("impact-analysis")
    logger = get_logger(__name__)

    result = {"success": False, "message": "", "stats": {}, "error": None, "files": []}

    # Neo4j 비밀번호 확인
    neo4j_password = _ensure_password()
    if not neo4j_password:
        result["error"] = "NEO4J_PASSWORD not set"
        return result

    # 옵션 검증
    if not table_name and not class_name:
        error_msg = "Error: --table-name 또는 --class-name 중 하나는 반드시 지정해야 합니다."
        click.echo(error_msg)
        click.echo("\nUsage:")
        click.echo("  테이블 분석: --table-name <table_name>")
        click.echo("  메서드 분석: --class-name <class_name> [--method-name <method_name>]")
        result["error"] = error_msg
        return result

    if table_name and class_name:
        error_msg = "Error: --table-name과 --class-name을 동시에 지정할 수 없습니다."
        click.echo(error_msg)
        result["error"] = error_msg
        return result

    # 출력 디렉터리 설정
    if not output_dir:
        output_dir = os.getenv("IMPACT_ANALYSIS_OUTPUT_DIR", "./output/impact-analysis")
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    try:
        # Neo4j 연결
        neo4j_database = os.getenv("NEO4J_DATABASE", "neo4j")
        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        service = ImpactAnalysisService(driver, database=neo4j_database)

        click.echo("=" * 80)
        if table_name:
            click.echo(f"테이블 영향도 분석: {table_name}")
            if project_name:
                click.echo(f"프로젝트: {project_name}")
            else:
                click.echo("프로젝트: 전체")
        else:
            target_display = f"{class_name}.{method_name}" if method_name else class_name
            click.echo(f"메서드 영향도 분석: {target_display}")
            if project_name:
                click.echo(f"프로젝트: {project_name}")
            else:
                click.echo("프로젝트: 전체")
        click.echo(f"최대 깊이: {max_depth}")
        click.echo("=" * 80)

        # 영향도 분석 수행
        if table_name:
            impact_result = service.analyze_table_impact_reverse(
                table_name=table_name,
                project_name=project_name,
                max_depth=max_depth,
            )
        else:
            impact_result = service.analyze_method_impact_reverse(
                class_name=class_name,
                method_name=method_name,
                project_name=project_name,
                max_depth=max_depth,
            )

        # 요약 정보 출력
        click.echo("\n[요약]")
        click.echo(f"  분석 대상: {impact_result.target_name}")
        click.echo(f"  영향받는 클래스: {impact_result.summary.total_impacted_classes}개")
        click.echo(f"  영향받는 메서드: {impact_result.summary.total_impacted_methods}개")
        click.echo(f"  영향받는 패키지: {impact_result.summary.total_impacted_packages}개")
        click.echo(f"  최대 호출 깊이: {impact_result.summary.max_depth}")
        click.echo(f"  평균 호출 깊이: {impact_result.summary.avg_depth}")
        click.echo(f"  리스크 등급:")
        click.echo(f"    - HIGH: {impact_result.summary.risk_distribution['HIGH']}개")
        click.echo(f"    - MEDIUM: {impact_result.summary.risk_distribution['MEDIUM']}개")
        click.echo(f"    - LOW: {impact_result.summary.risk_distribution['LOW']}개")

        if impact_result.has_circular_reference:
            click.echo(f"\n  ⚠️  순환 참조 감지: {len(impact_result.circular_paths)}개")

        # 리포트 생성
        reporter = ImpactReporter()

        # Markdown 리포트 (기본 생성)
        md_filename = _generate_filename(impact_result, "md")
        md_filepath = output_path / md_filename
        if reporter.generate_markdown(impact_result, md_filepath):
            click.echo(f"\n[OK] Markdown 리포트 생성: {md_filepath}")
            result["files"].append(str(md_filepath))
        else:
            click.echo(f"\n[FAIL] Markdown 리포트 생성 실패")

        # Excel 리포트 (기본 생성)
        excel_filename = _generate_filename(impact_result, "xlsx")
        excel_filepath = output_path / excel_filename
        if reporter.generate_excel(impact_result, excel_filepath):
            click.echo(f"[OK] Excel 리포트 생성: {excel_filepath}")
            result["files"].append(str(excel_filepath))
        else:
            click.echo(f"[FAIL] Excel 리포트 생성 실패")

        # JSON 리포트 (선택 생성)
        if include_json:
            json_filename = _generate_filename(impact_result, "json")
            json_filepath = output_path / json_filename
            if reporter.generate_json(impact_result, json_filepath):
                click.echo(f"[OK] JSON 리포트 생성: {json_filepath}")
                result["files"].append(str(json_filepath))
            else:
                click.echo(f"[FAIL] JSON 리포트 생성 실패")

        # Mermaid 다이어그램 (선택 생성)
        if generate_diagram:
            diagram_filename = _generate_filename(impact_result, "diagram.md")
            diagram_filepath = output_path / diagram_filename
            if reporter.generate_mermaid_diagram(impact_result, diagram_filepath):
                click.echo(f"[OK] Mermaid 다이어그램 생성: {diagram_filepath}")
                result["files"].append(str(diagram_filepath))
            else:
                click.echo(f"[FAIL] Mermaid 다이어그램 생성 실패")

        click.echo("\n분석 완료!")
        result["success"] = True
        result["message"] = f"영향도 분석 완료: {impact_result.target_name}"
        result["stats"] = {
            "impacted_classes": impact_result.summary.total_impacted_classes,
            "impacted_methods": impact_result.summary.total_impacted_methods,
            "max_depth": impact_result.summary.max_depth,
        }

        driver.close()
        return result

    except Exception as exc:
        error_msg = f"영향도 분석 중 오류 발생: {exc}"
        logger.error(error_msg, exc_info=True)
        click.echo(f"\nError: {error_msg}")
        result["error"] = str(exc)
        return result


def _generate_filename(impact_result, extension: str) -> str:
    """파일명 생성

    Args:
        impact_result: ImpactAnalysisResult 객체
        extension: 파일 확장자 (md, xlsx, json)

    Returns:
        생성된 파일명
    """
    if impact_result.analysis_type == "table":
        prefix = "IMPACT_TABLE"
        target = impact_result.target_name
    else:
        prefix = "IMPACT_METHOD"
        # 클래스명.메서드명 → 클래스명_메서드명
        target = impact_result.target_name.replace(".", "_")

    return f"{prefix}_{target}_{impact_result.timestamp}.{extension}"


def register(cli: click.Group) -> None:
    """Attach impact-analysis command to the given CLI group."""
    cli.add_command(impact_analysis_command)


__all__ = ["register"]
