"""
Mermaid 다이어그램 생성기 for 영향도 분석

ImpactAnalysisResult를 Mermaid 다이어그램으로 변환
"""
from __future__ import annotations

from typing import List, Dict
from pathlib import Path
from datetime import datetime

from csa.models.impact import ImpactAnalysisResult, ImpactNode
from csa.utils.logger import get_logger

logger = get_logger(__name__)


class ImpactMermaidGenerator:
    """영향도 분석 Mermaid 다이어그램 생성기

    생성되는 다이어그램:
    1. 호출 체인 트리 (graph TD)
    2. 리스크 분포 파이 차트 (pie)
    3. 패키지별 영향도 (graph LR)
    """

    def generate_diagram(
        self,
        result: ImpactAnalysisResult,
        filepath: Path,
    ) -> bool:
        """Mermaid 다이어그램 생성

        Args:
            result: ImpactAnalysisResult 객체
            filepath: 저장 경로 (.md)

        Returns:
            성공 여부
        """
        try:
            lines = []

            # timestamp 형식 변환: YYYYMMDD-HHmmss -> YYYY-MM-DD HH:mm:ss
            formatted_timestamp = self._format_timestamp(result.timestamp)

            # 제목
            lines.append(f"# 영향도 분석 다이어그램: {result.target_name}")
            lines.append("")
            lines.append(f"**분석 대상**: {result.target_name}  ")
            lines.append("")
            lines.append(f"**프로젝트**: {result.project_name or '전체'}  ")
            lines.append("")
            lines.append(f"**분석 일시**: {formatted_timestamp}  ")
            lines.append("")
            lines.append("---")
            lines.append("")

            # 1. 호출 체인 트리 다이어그램
            if result.impact_tree:
                lines.append("## 1. 호출 체인 트리")
                lines.append("")
                lines.append("```mermaid")
                lines.extend(self._generate_tree_diagram(result))
                lines.append("```")
                lines.append("")
            else:
                lines.append("## 1. 호출 체인 트리")
                lines.append("")
                lines.append("_영향받는 코드가 없습니다._")
                lines.append("")

            # 2. 리스크 분포 파이 차트
            if result.summary.total_impacted_methods > 0:
                lines.append("## 2. 리스크 분포")
                lines.append("")
                lines.append("```mermaid")
                lines.extend(self._generate_risk_pie_chart(result))
                lines.append("```")
                lines.append("")
            else:
                lines.append("## 2. 리스크 분포")
                lines.append("")
                lines.append("_데이터가 없습니다._")
                lines.append("")

            # 3. 패키지별 영향도
            if result.package_summary:
                lines.append("## 3. 패키지별 영향도")
                lines.append("")
                lines.append("```mermaid")
                lines.extend(self._generate_package_chart(result))
                lines.append("```")
                lines.append("")
            else:
                lines.append("## 3. 패키지별 영향도")
                lines.append("")
                lines.append("_데이터가 없습니다._")
                lines.append("")

            # 요약 정보
            lines.append("---")
            lines.append("")
            lines.append("## 요약")
            lines.append(f"- **총 영향 범위**: 클래스 {result.summary.total_impacted_classes}개, "
                        f"메서드 {result.summary.total_impacted_methods}개")
            lines.append(f"- **최대 깊이**: {result.summary.max_depth}")
            lines.append(f"- **평균 깊이**: {result.summary.avg_depth}")

            risk_dist = result.summary.risk_distribution
            lines.append(f"- **리스크**: HIGH {risk_dist['HIGH']}개, "
                        f"MEDIUM {risk_dist['MEDIUM']}개, "
                        f"LOW {risk_dist['LOW']}개")

            if result.has_circular_reference:
                lines.append(f"- ⚠️ **순환 참조 감지**: {len(result.circular_paths)}개")

            # 파일 저장
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))

            logger.info(f"Mermaid 다이어그램 생성 완료: {filepath}")
            return True

        except Exception as exc:
            logger.error(f"Mermaid 다이어그램 생성 실패: {exc}", exc_info=True)
            return False

    def _generate_tree_diagram(self, result: ImpactAnalysisResult) -> List[str]:
        """호출 체인 트리 다이어그램 생성 (graph TD)

        Args:
            result: ImpactAnalysisResult 객체

        Returns:
            Mermaid 코드 라인 리스트
        """
        lines = []
        lines.append("graph TD")

        # 노드 ID 매핑 (중복 방지)
        node_id_map: Dict[str, str] = {}
        node_counter = 0

        # 분석 대상 (루트 노드)
        root_id = "ROOT"
        root_label = result.target_name
        lines.append(f'    {root_id}["{root_label}"]')
        lines.append(f"    style {root_id} fill:#e1f5ff,stroke:#01579b,stroke-width:3px")

        # Level별 노드 생성
        for level in sorted(result.impact_tree.keys()):
            nodes = result.impact_tree[level]

            for node in nodes:
                # 노드 ID 생성
                node_key = f"{node.class_name}.{node.method_name}"
                if node_key not in node_id_map:
                    node_id = f"N{node_counter}"
                    node_id_map[node_key] = node_id
                    node_counter += 1
                else:
                    node_id = node_id_map[node_key]

                # 노드 레이블
                label = f"{node.class_name}\\n{node.method_name}"
                if node.sql_type:
                    label += f"\\n({node.sql_type})"

                lines.append(f'    {node_id}["{label}"]')

                # 노드 스타일 (리스크 등급별)
                if node.risk_grade == "HIGH":
                    lines.append(f"    style {node_id} fill:#ffcdd2,stroke:#c62828,stroke-width:2px")
                elif node.risk_grade == "MEDIUM":
                    lines.append(f"    style {node_id} fill:#fff9c4,stroke:#f57f17,stroke-width:2px")
                else:
                    lines.append(f"    style {node_id} fill:#c8e6c9,stroke:#2e7d32,stroke-width:2px")

                # 연결 (루트 → 노드)
                if level == 1:
                    lines.append(f"    {root_id} --> {node_id}")

        # Level 간 연결 (간단화: Level 1 → Level 2, Level 2 → Level 3...)
        # 실제 호출 관계는 Neo4j에서 가져와야 정확하지만, 여기서는 Level 기반으로 표현
        prev_level_nodes = []
        for level in sorted(result.impact_tree.keys()):
            nodes = result.impact_tree[level]
            current_level_nodes = []

            for node in nodes:
                node_key = f"{node.class_name}.{node.method_name}"
                node_id = node_id_map[node_key]
                current_level_nodes.append(node_id)

            # Level 1은 이미 ROOT와 연결됨
            if level > 1 and prev_level_nodes:
                # 이전 레벨의 노드들과 현재 레벨 노드들 연결 (간단화)
                for prev_id in prev_level_nodes[:3]:  # 최대 3개만 연결 (다이어그램 복잡도 제한)
                    for curr_id in current_level_nodes[:2]:
                        lines.append(f"    {prev_id} --> {curr_id}")

            prev_level_nodes = current_level_nodes

        return lines

    def _generate_risk_pie_chart(self, result: ImpactAnalysisResult) -> List[str]:
        """리스크 분포 파이 차트 생성

        Args:
            result: ImpactAnalysisResult 객체

        Returns:
            Mermaid 코드 라인 리스트
        """
        lines = []
        risk_dist = result.summary.risk_distribution

        # 파이 차트 크기를 작게 설정 (textPosition: 0.5로 크기 축소)
        lines.append("%%{init: {'theme':'base', 'themeVariables': {'pieOuterStrokeWidth': '3px', 'pieSectionTextSize': '14px'}, 'pie': {'textPosition': 0.5}}}%%")
        lines.append("pie title 리스크 등급 분포")

        high_count = risk_dist.get("HIGH", 0)
        medium_count = risk_dist.get("MEDIUM", 0)
        low_count = risk_dist.get("LOW", 0)

        if high_count > 0:
            lines.append(f'    "HIGH" : {high_count}')
        if medium_count > 0:
            lines.append(f'    "MEDIUM" : {medium_count}')
        if low_count > 0:
            lines.append(f'    "LOW" : {low_count}')

        return lines

    def _generate_package_chart(self, result: ImpactAnalysisResult) -> List[str]:
        """패키지별 영향도 차트 생성 (graph LR)

        Args:
            result: ImpactAnalysisResult 객체

        Returns:
            Mermaid 코드 라인 리스트
        """
        lines = []
        lines.append("graph LR")

        # 최대 10개 패키지만 표시
        packages = result.package_summary[:10]

        for idx, pkg in enumerate(packages):
            pkg_id = f"PKG{idx}"
            pkg_name = pkg.package_name.split(".")[-1]  # 마지막 패키지명만 사용

            # 레이블: 패키지명 + 메서드 수
            label = f"{pkg_name}\\n메서드: {pkg.impacted_methods}개"

            lines.append(f'    {pkg_id}["{label}"]')

            # 스타일 (영향도에 따라 색상 변경)
            high_count = pkg.risk_distribution.get("HIGH", 0)
            medium_count = pkg.risk_distribution.get("MEDIUM", 0)

            if high_count > 0:
                lines.append(f"    style {pkg_id} fill:#ffcdd2,stroke:#c62828,stroke-width:2px")
            elif medium_count > 0:
                lines.append(f"    style {pkg_id} fill:#fff9c4,stroke:#f57f17,stroke-width:2px")
            else:
                lines.append(f"    style {pkg_id} fill:#c8e6c9,stroke:#2e7d32,stroke-width:2px")

        # 패키지 간 연결 (간단히 순서대로 연결)
        for idx in range(len(packages) - 1):
            lines.append(f"    PKG{idx} --> PKG{idx+1}")

        return lines

    def _format_timestamp(self, timestamp: str) -> str:
        """timestamp 형식 변환

        Args:
            timestamp: YYYYMMDD-HHmmss 형식의 문자열

        Returns:
            YYYY-MM-DD HH:mm:ss 형식의 문자열
        """
        try:
            # YYYYMMDD-HHmmss 형식 파싱
            dt = datetime.strptime(timestamp, "%Y%m%d-%H%M%S")
            # YYYY-MM-DD HH:mm:ss 형식으로 변환
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            # 파싱 실패 시 원본 반환
            logger.warning(f"timestamp 파싱 실패: {timestamp}, 원본 사용")
            return timestamp
