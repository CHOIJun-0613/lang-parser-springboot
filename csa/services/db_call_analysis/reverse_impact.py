"""
역방향 영향도 분석 모듈

테이블 또는 메서드 변경 시 영향받는 모든 상위 호출자를 역추적하는 기능 제공
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from collections import defaultdict

from csa.models.impact import (
    ImpactNode,
    ImpactSummary,
    PackageSummary,
    SqlDetail,
    TestScopeItem,
    ImpactAnalysisResult,
)
from csa.utils.logger import get_logger

logger = get_logger(__name__)


class ReverseImpactMixin:
    """역방향 영향도 분석 Mixin

    테이블 → SQL → Mapper → Method → Caller Method 체인을 역추적
    """

    def analyze_table_impact_reverse(
        self,
        table_name: str,
        project_name: Optional[str] = None,
        max_depth: int = 10,
    ) -> ImpactAnalysisResult:
        """테이블 역방향 영향도 분석

        Args:
            table_name: 분석 대상 테이블명
            project_name: 프로젝트명 (선택사항, 생략 시 전체 프로젝트 대상)
            max_depth: 최대 호출 깊이

        Returns:
            ImpactAnalysisResult: 영향도 분석 결과
        """
        try:
            with self._open_session() as session:
                # 1단계: 테이블을 사용하는 SQL 조회
                # sql.tables는 JSON 문자열 형태: "[{\"name\": \"users\", \"alias\": \"u\"}]"
                # 간단하게 테이블명이 포함되어 있는지만 확인 (대소문자 구분 없음)
                sql_query = """
                MATCH (sql:SqlStatement)
                WHERE ($project_name IS NULL OR sql.project_name = $project_name)
                  AND sql.tables IS NOT NULL
                  AND toLower(sql.tables) CONTAINS toLower($table_name)
                RETURN DISTINCT
                    sql.id AS sql_id,
                    sql.sql_type AS sql_type,
                    sql.complexity_score AS sql_complexity,
                    sql.sql_content AS query_text,
                    sql.project_name AS sql_project_name
                """
                sql_result = session.run(sql_query, project_name=project_name, table_name=table_name)
                sql_statements = [dict(record) for record in sql_result]

                if not sql_statements:
                    # 테이블을 사용하는 SQL이 없으면 빈 결과 반환
                    return self._create_empty_result("table", table_name, project_name)

                # SQL 상세 정보 수집
                sql_details = self._collect_sql_details(session, sql_statements)

                # 2단계: SQL을 호출하는 Method 및 상위 호출자 재귀 조회
                # 관계: Service.Method -> Mapper.Method (name == sql.id) -> SqlStatement
                impact_query = """
                MATCH (sql:SqlStatement)
                WHERE sql.id IN $sql_ids

                // SqlStatement.id와 같은 이름을 가진 Mapper Method 찾기
                // 클래스명 또는 패키지명으로 Mapper/Repository 식별
                MATCH (mapper_class:Class)-[:HAS_METHOD]->(mapper_method:Method)
                WHERE mapper_method.name = sql.id
                  AND (mapper_class.name CONTAINS 'Repository'
                       OR mapper_class.name CONTAINS 'Mapper'
                       OR mapper_class.package_name CONTAINS 'repository'
                       OR mapper_class.package_name CONTAINS 'mapper')

                // Mapper Method를 호출하는 Service/Controller Method 찾기 (Level 1 - 직접 영향)
                OPTIONAL MATCH (m:Method)-[:CALLS]->(mapper_method)
                OPTIONAL MATCH (c:Class)-[:HAS_METHOD]->(m)

                // Service Method를 호출하는 상위 Method 재귀 조회 (Level 2+ - 간접 영향)
                OPTIONAL MATCH path = (caller:Method)-[:CALLS*1..10]->(m)
                WHERE length(path) <= $max_depth
                OPTIONAL MATCH (caller_class:Class)-[:HAS_METHOD]->(caller)

                WITH DISTINCT
                    c.name AS class_name,
                    c.package_name AS package_name,
                    c.project_name AS project_name,
                    m.name AS method_name,
                    sql.id AS sql_id,
                    sql.sql_type AS sql_type,
                    sql.complexity_score AS sql_complexity,
                    caller_class.name AS caller_class_name,
                    caller_class.package_name AS caller_package_name,
                    caller_class.project_name AS caller_project_name,
                    caller.name AS caller_method_name,
                    CASE WHEN path IS NULL THEN 0 ELSE length(path) END AS depth

                RETURN
                    project_name, class_name, package_name, method_name,
                    sql_id, sql_type, sql_complexity,
                    caller_project_name, caller_class_name, caller_package_name, caller_method_name,
                    depth
                ORDER BY depth ASC, caller_package_name, caller_class_name
                """

                sql_ids = [s["sql_id"] for s in sql_statements]
                logger.debug(f"SQL IDs to analyze: {sql_ids}")

                impact_result = session.run(impact_query, sql_ids=sql_ids, max_depth=max_depth)
                raw_nodes = [dict(record) for record in impact_result]

                logger.info(f"Query returned {len(raw_nodes)} raw nodes")
                if raw_nodes:
                    logger.debug(f"Sample node: {raw_nodes[0]}")
                else:
                    logger.warning("No raw nodes returned from query!")

                # 3단계: 영향도 트리 구축
                impact_tree = self._build_impact_tree(raw_nodes, max_depth)
                logger.info(f"Impact tree built with {len(impact_tree)} levels")

                # 4단계: 요약 통계 계산
                summary = self._calculate_summary("table", table_name, project_name, impact_tree)

                # 5단계: 패키지별 통계 계산
                package_summary = self._calculate_package_summary(impact_tree)

                # 6단계: 테스트 범위 식별
                impacted_classes = self._extract_impacted_classes(impact_tree)
                test_scope = self._identify_test_scope(session, impacted_classes, project_name)

                # 7단계: 순환 참조 탐지
                has_circular, circular_paths = self._detect_circular_references(session, impacted_classes, project_name)

                # 결과 생성
                timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                result = ImpactAnalysisResult(
                    project_name=project_name,
                    analysis_type="table",
                    target_name=table_name,
                    timestamp=timestamp,
                    summary=summary,
                    impact_tree=impact_tree,
                    package_summary=package_summary,
                    sql_details=sql_details,
                    test_scope=test_scope,
                    has_circular_reference=has_circular,
                    circular_paths=circular_paths,
                )

                return result

        except Exception as exc:
            self.logger.error(f"테이블 역방향 영향도 분석 오류: {exc}", exc_info=True)
            raise

    def analyze_method_impact_reverse(
        self,
        class_name: str,
        method_name: Optional[str] = None,
        project_name: Optional[str] = None,
        max_depth: int = 10,
    ) -> ImpactAnalysisResult:
        """메서드 역방향 영향도 분석

        Args:
            class_name: 분석 대상 클래스명
            method_name: 분석 대상 메서드명 (선택사항, 생략 시 클래스의 모든 public 메서드)
            project_name: 프로젝트명 (선택사항)
            max_depth: 최대 호출 깊이

        Returns:
            ImpactAnalysisResult: 영향도 분석 결과
        """
        try:
            with self._open_session() as session:
                # 1단계: 대상 Method 조회
                if method_name:
                    target_query = """
                    MATCH (target_class:Class {name: $class_name})-[:HAS_METHOD]->(target_method:Method {name: $method_name})
                    WHERE $project_name IS NULL OR target_class.project_name = $project_name
                    RETURN DISTINCT
                        target_class.name AS class_name,
                        target_class.package_name AS package_name,
                        target_class.project_name AS project_name,
                        target_method.name AS method_name
                    """
                    params = {"class_name": class_name, "method_name": method_name, "project_name": project_name}
                else:
                    target_query = """
                    MATCH (target_class:Class {name: $class_name})-[:HAS_METHOD]->(target_method:Method)
                    WHERE ($project_name IS NULL OR target_class.project_name = $project_name)
                      AND target_method.access_modifier = 'public'
                    RETURN DISTINCT
                        target_class.name AS class_name,
                        target_class.package_name AS package_name,
                        target_class.project_name AS project_name,
                        target_method.name AS method_name
                    """
                    params = {"class_name": class_name, "project_name": project_name}

                target_result = session.run(target_query, **params)
                target_methods = [dict(record) for record in target_result]

                if not target_methods:
                    # 대상 메서드가 없으면 빈 결과 반환
                    target_display_name = f"{class_name}.{method_name}" if method_name else class_name
                    return self._create_empty_result("method", target_display_name, project_name)

                # 2단계: 해당 Method를 호출하는 모든 상위 Method 재귀 조회
                impact_query = """
                MATCH (target_class:Class {name: $class_name})-[:HAS_METHOD]->(target_method:Method)
                WHERE ($project_name IS NULL OR target_class.project_name = $project_name)
                  AND ($method_name IS NULL OR target_method.name = $method_name)
                  AND ($method_name IS NOT NULL OR target_method.access_modifier = 'public')

                // 상위 호출자 재귀 조회
                OPTIONAL MATCH path = (caller:Method)-[:CALLS*1..10]->(target_method)
                WHERE length(path) <= $max_depth
                OPTIONAL MATCH (caller_class:Class)-[:HAS_METHOD]->(caller)

                WITH DISTINCT
                    target_class.name AS target_class_name,
                    target_class.project_name AS target_project_name,
                    target_class.package_name AS target_package_name,
                    target_method.name AS target_method_name,
                    caller_class.name AS caller_class_name,
                    caller_class.package_name AS caller_package_name,
                    caller_class.project_name AS caller_project_name,
                    caller.name AS caller_method_name,
                    CASE WHEN path IS NULL THEN 0 ELSE length(path) END AS depth

                RETURN
                    target_project_name, target_package_name, target_class_name, target_method_name,
                    caller_project_name, caller_class_name, caller_package_name, caller_method_name,
                    depth
                ORDER BY depth ASC, caller_package_name, caller_class_name
                """

                impact_result = session.run(impact_query, class_name=class_name, method_name=method_name, project_name=project_name, max_depth=max_depth)
                raw_nodes = [dict(record) for record in impact_result]

                # 3단계: 영향도 트리 구축 (메서드용)
                impact_tree = self._build_method_impact_tree(raw_nodes, max_depth)

                # 4단계: 요약 통계 계산
                target_display_name = f"{class_name}.{method_name}" if method_name else class_name
                summary = self._calculate_summary("method", target_display_name, project_name, impact_tree)

                # 5단계: 패키지별 통계 계산
                package_summary = self._calculate_package_summary(impact_tree)

                # 6단계: 테스트 범위 식별
                impacted_classes = self._extract_impacted_classes(impact_tree)
                test_scope = self._identify_test_scope(session, impacted_classes, project_name)

                # 7단계: 순환 참조 탐지
                has_circular, circular_paths = self._detect_circular_references(session, impacted_classes, project_name)

                # 결과 생성
                timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                result = ImpactAnalysisResult(
                    project_name=project_name,
                    analysis_type="method",
                    target_name=target_display_name,
                    timestamp=timestamp,
                    summary=summary,
                    impact_tree=impact_tree,
                    package_summary=package_summary,
                    sql_details=[],  # 메서드 분석 시 SQL 상세 정보 없음
                    test_scope=test_scope,
                    has_circular_reference=has_circular,
                    circular_paths=circular_paths,
                )

                return result

        except Exception as exc:
            self.logger.error(f"메서드 역방향 영향도 분석 오류: {exc}", exc_info=True)
            raise

    def _build_impact_tree(
        self,
        raw_nodes: List[Dict[str, Any]],
        max_depth: int,
    ) -> Dict[int, List[ImpactNode]]:
        """영향도 트리 구축 (테이블 분석용)

        Args:
            raw_nodes: Neo4j 쿼리 결과 (raw 노드 리스트)
            max_depth: 최대 깊이

        Returns:
            Level별 노드 딕셔너리
        """
        tree: Dict[int, List[ImpactNode]] = defaultdict(list)

        for node_data in raw_nodes:
            depth = node_data.get("depth", 0)
            level = depth + 1  # Level은 1부터 시작

            # depth 0: 직접 SQL 호출 메서드
            if depth == 0:
                if node_data.get("class_name") and node_data.get("method_name"):
                    impact_node = ImpactNode(
                        level=1,
                        depth=0,
                        package_name=node_data.get("package_name", ""),
                        class_name=node_data["class_name"],
                        method_name=node_data["method_name"],
                        project_name=node_data.get("project_name"),
                        sql_id=node_data.get("sql_id"),
                        sql_type=node_data.get("sql_type"),
                        sql_complexity=node_data.get("sql_complexity"),
                        risk_grade=self._calculate_risk_grade(node_data, len(raw_nodes)),
                    )
                    tree[1].append(impact_node)
            # depth 1+: 간접 호출 메서드
            else:
                if node_data.get("caller_class_name") and node_data.get("caller_method_name"):
                    impact_node = ImpactNode(
                        level=level,
                        depth=depth,
                        package_name=node_data.get("caller_package_name", ""),
                        class_name=node_data["caller_class_name"],
                        method_name=node_data["caller_method_name"],
                        project_name=node_data.get("caller_project_name"),
                        sql_id=None,
                        sql_type=None,
                        sql_complexity=None,
                        risk_grade=self._calculate_risk_grade(node_data, len(raw_nodes)),
                    )
                    tree[level].append(impact_node)

        # 중복 제거 (동일 클래스.메서드는 하나만)
        for level in tree:
            unique_nodes = {}
            for node in tree[level]:
                key = f"{node.package_name}.{node.class_name}.{node.method_name}"
                if key not in unique_nodes:
                    unique_nodes[key] = node
            tree[level] = list(unique_nodes.values())

        return dict(tree)

    def _build_method_impact_tree(
        self,
        raw_nodes: List[Dict[str, Any]],
        max_depth: int,
    ) -> Dict[int, List[ImpactNode]]:
        """영향도 트리 구축 (메서드 분석용)

        Args:
            raw_nodes: Neo4j 쿼리 결과
            max_depth: 최대 깊이

        Returns:
            Level별 노드 딕셔너리
        """
        tree: Dict[int, List[ImpactNode]] = defaultdict(list)

        for node_data in raw_nodes:
            depth = node_data.get("depth", 0)
            level = depth + 1

            # depth 0: 대상 메서드 자체 (분석 대상이므로 트리에 포함하지 않음)
            if depth == 0:
                continue

            # depth 1+: 호출자 메서드
            if node_data.get("caller_class_name") and node_data.get("caller_method_name"):
                impact_node = ImpactNode(
                    level=level,
                    depth=depth,
                    package_name=node_data.get("caller_package_name", ""),
                    class_name=node_data["caller_class_name"],
                    method_name=node_data["caller_method_name"],
                    project_name=node_data.get("caller_project_name"),
                    sql_id=None,
                    sql_type=None,
                    sql_complexity=None,
                    risk_grade=self._calculate_risk_grade(node_data, len(raw_nodes)),
                )
                tree[level].append(impact_node)

        # 중복 제거
        for level in tree:
            unique_nodes = {}
            for node in tree[level]:
                key = f"{node.package_name}.{node.class_name}.{node.method_name}"
                if key not in unique_nodes:
                    unique_nodes[key] = node
            tree[level] = list(unique_nodes.values())

        return dict(tree)

    def _calculate_risk_grade(
        self,
        node_data: Dict[str, Any],
        total_nodes: int,
    ) -> str:
        """리스크 등급 계산

        Args:
            node_data: 노드 데이터
            total_nodes: 전체 노드 수

        Returns:
            리스크 등급 (HIGH/MEDIUM/LOW)
        """
        # 리스크 점수 계산
        risk_score = 0.0

        # 1. SQL 복잡도 (30%)
        sql_complexity = node_data.get("sql_complexity", 0) or 0
        if sql_complexity > 10:
            risk_score += 30
        elif sql_complexity > 5:
            risk_score += 20
        elif sql_complexity > 0:
            risk_score += 10

        # 2. 호출 깊이 (20%)
        depth = node_data.get("depth", 0)
        if depth >= 5:
            risk_score += 20
        elif depth >= 3:
            risk_score += 15
        elif depth >= 1:
            risk_score += 10

        # 3. 영향 범위 (40%)
        if total_nodes > 50:
            risk_score += 40
        elif total_nodes > 20:
            risk_score += 30
        elif total_nodes > 10:
            risk_score += 20
        else:
            risk_score += 10

        # 4. SQL 타입 (10%)
        sql_type = node_data.get("sql_type", "")
        if sql_type in ("UPDATE", "DELETE"):
            risk_score += 10
        elif sql_type == "INSERT":
            risk_score += 5

        # 리스크 등급 결정
        if risk_score >= 70:
            return "HIGH"
        elif risk_score >= 40:
            return "MEDIUM"
        else:
            return "LOW"

    def _calculate_summary(
        self,
        analysis_type: str,
        target_name: str,
        project_name: Optional[str],
        impact_tree: Dict[int, List[ImpactNode]],
    ) -> ImpactSummary:
        """요약 통계 계산

        Args:
            analysis_type: 분석 타입 (table/method)
            target_name: 분석 대상 이름
            project_name: 프로젝트명
            impact_tree: 영향도 트리

        Returns:
            ImpactSummary 객체
        """
        all_nodes = [node for nodes in impact_tree.values() for node in nodes]

        if not all_nodes:
            return ImpactSummary(
                target_type=analysis_type,
                target_name=target_name,
                project_name=project_name,
            )

        # 통계 계산
        impacted_classes = {node.class_name for node in all_nodes}
        impacted_methods = {f"{node.class_name}.{node.method_name}" for node in all_nodes}
        impacted_packages = {node.package_name for node in all_nodes if node.package_name}

        depths = [node.depth for node in all_nodes]
        max_depth = max(depths) if depths else 0
        avg_depth = sum(depths) / len(depths) if depths else 0.0

        risk_distribution = {
            "HIGH": sum(1 for node in all_nodes if node.risk_grade == "HIGH"),
            "MEDIUM": sum(1 for node in all_nodes if node.risk_grade == "MEDIUM"),
            "LOW": sum(1 for node in all_nodes if node.risk_grade == "LOW"),
        }

        return ImpactSummary(
            target_type=analysis_type,
            target_name=target_name,
            project_name=project_name,
            total_impacted_classes=len(impacted_classes),
            total_impacted_methods=len(impacted_methods),
            total_impacted_packages=len(impacted_packages),
            max_depth=max_depth,
            avg_depth=round(avg_depth, 2),
            risk_distribution=risk_distribution,
        )

    def _calculate_package_summary(
        self,
        impact_tree: Dict[int, List[ImpactNode]],
    ) -> List[PackageSummary]:
        """패키지별 통계 계산

        Args:
            impact_tree: 영향도 트리

        Returns:
            PackageSummary 리스트
        """
        package_data: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "classes": set(),
            "methods": set(),
            "depths": [],
            "risk_distribution": {"HIGH": 0, "MEDIUM": 0, "LOW": 0},
        })

        # 패키지별 집계
        for nodes in impact_tree.values():
            for node in nodes:
                pkg = node.package_name or "default"
                package_data[pkg]["classes"].add(node.class_name)
                package_data[pkg]["methods"].add(f"{node.class_name}.{node.method_name}")
                package_data[pkg]["depths"].append(node.depth)
                package_data[pkg]["risk_distribution"][node.risk_grade] += 1

        # PackageSummary 객체 생성
        summaries = []
        for pkg_name, data in package_data.items():
            avg_depth = sum(data["depths"]) / len(data["depths"]) if data["depths"] else 0.0
            summaries.append(
                PackageSummary(
                    package_name=pkg_name,
                    impacted_classes=len(data["classes"]),
                    impacted_methods=len(data["methods"]),
                    avg_depth=round(avg_depth, 2),
                    risk_distribution=data["risk_distribution"],
                )
            )

        # 영향 메서드 수 기준 내림차순 정렬
        summaries.sort(key=lambda x: x.impacted_methods, reverse=True)
        return summaries

    def _collect_sql_details(
        self,
        session,
        sql_statements: List[Dict[str, Any]],
    ) -> List[SqlDetail]:
        """SQL 상세 정보 수집

        Args:
            session: Neo4j 세션
            sql_statements: SQL 문 리스트

        Returns:
            SqlDetail 리스트
        """
        sql_details = []

        for sql_data in sql_statements:
            # SQL을 호출하는 Mapper 정보 조회
            mapper_query = """
            MATCH (sql:SqlStatement {id: $sql_id})
            OPTIONAL MATCH (m:Method)-[:CALLS]->(sql)
            OPTIONAL MATCH (c:Class)-[:HAS_METHOD]->(m)
            RETURN DISTINCT
                c.name AS mapper_class,
                m.name AS mapper_method
            LIMIT 1
            """
            mapper_result = session.run(mapper_query, sql_id=sql_data["sql_id"])
            mapper_record = mapper_result.single()

            if mapper_record:
                query_text = sql_data.get("query_text", "")
                query_preview = query_text[:100] if query_text else ""

                sql_detail = SqlDetail(
                    sql_id=sql_data["sql_id"],
                    sql_type=sql_data.get("sql_type", "UNKNOWN"),
                    mapper_class=mapper_record.get("mapper_class", "Unknown"),
                    mapper_method=mapper_record.get("mapper_method", "Unknown"),
                    complexity=sql_data.get("sql_complexity", 0) or 0,
                    query_preview=query_preview,
                )
                sql_details.append(sql_detail)

        return sql_details

    def _extract_impacted_classes(
        self,
        impact_tree: Dict[int, List[ImpactNode]],
    ) -> List[str]:
        """영향받는 클래스 목록 추출

        Args:
            impact_tree: 영향도 트리

        Returns:
            클래스명 리스트
        """
        classes = set()
        for nodes in impact_tree.values():
            for node in nodes:
                classes.add(node.class_name)
        return sorted(list(classes))

    def _identify_test_scope(
        self,
        session,
        impacted_classes: List[str],
        project_name: Optional[str],
    ) -> List[TestScopeItem]:
        """테스트 범위 식별

        네이밍 컨벤션 기반으로 테스트 클래스 자동 매핑
        - {ClassName}Test
        - {ClassName}Tests
        - Test{ClassName}

        Args:
            session: Neo4j 세션
            impacted_classes: 영향받는 클래스 목록
            project_name: 프로젝트명

        Returns:
            TestScopeItem 리스트
        """
        test_scope_items = []

        for class_name in impacted_classes:
            # 테스트 클래스 후보 이름들
            test_class_candidates = [
                f"{class_name}Test",
                f"{class_name}Tests",
                f"Test{class_name}",
            ]

            # Neo4j에서 테스트 클래스 조회
            test_query = """
            MATCH (c:Class)
            WHERE c.name IN $test_class_names
              AND c.is_test_class = true
              AND ($project_name IS NULL OR c.project_name = $project_name)
            OPTIONAL MATCH (c)-[:HAS_METHOD]->(m:Method)
            RETURN DISTINCT
                c.name AS test_class_name,
                count(m) AS method_count
            LIMIT 1
            """
            test_result = session.run(
                test_query,
                test_class_names=test_class_candidates,
                project_name=project_name,
            )
            test_record = test_result.single()

            if test_record:
                test_scope_items.append(
                    TestScopeItem(
                        impacted_class=class_name,
                        test_class=test_record["test_class_name"],
                        test_method_count=test_record["method_count"] or 0,
                        status="존재",
                    )
                )
            else:
                test_scope_items.append(
                    TestScopeItem(
                        impacted_class=class_name,
                        test_class=None,
                        test_method_count=0,
                        status="미존재",
                    )
                )

        return test_scope_items

    def _detect_circular_references(
        self,
        session,
        impacted_classes: List[str],
        project_name: Optional[str],
    ) -> tuple[bool, List[str]]:
        """순환 참조 탐지

        Args:
            session: Neo4j 세션
            impacted_classes: 영향받는 클래스 목록
            project_name: 프로젝트명

        Returns:
            (순환 참조 존재 여부, 순환 경로 리스트)
        """
        if not impacted_classes:
            return False, []

        # 순환 참조 탐지 쿼리
        circular_query = """
        MATCH (c:Class)-[:HAS_METHOD]->(m:Method)
        WHERE c.name IN $class_names
          AND ($project_name IS NULL OR c.project_name = $project_name)

        // 순환 경로 찾기 (자기 자신으로 돌아오는 경로)
        MATCH path = (m)-[:CALLS*2..10]->(m)

        RETURN DISTINCT
            [node IN nodes(path) |
                CASE
                    WHEN 'Method' IN labels(node) THEN node.name
                    ELSE ''
                END
            ] AS circular_path
        LIMIT 10
        """

        try:
            result = session.run(circular_query, class_names=impacted_classes, project_name=project_name)
            circular_paths = []

            for record in result:
                path_nodes = [node for node in record["circular_path"] if node]
                if path_nodes:
                    path_str = " → ".join(path_nodes)
                    circular_paths.append(path_str)

            has_circular = len(circular_paths) > 0
            return has_circular, circular_paths

        except Exception as exc:
            self.logger.warning(f"순환 참조 탐지 중 오류 발생: {exc}")
            return False, []

    def _create_empty_result(
        self,
        analysis_type: str,
        target_name: str,
        project_name: Optional[str],
    ) -> ImpactAnalysisResult:
        """빈 결과 생성 (분석 대상이 없을 때)

        Args:
            analysis_type: 분석 타입
            target_name: 대상 이름
            project_name: 프로젝트명

        Returns:
            빈 ImpactAnalysisResult
        """
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        return ImpactAnalysisResult(
            project_name=project_name,
            analysis_type=analysis_type,
            target_name=target_name,
            timestamp=timestamp,
            summary=ImpactSummary(
                target_type=analysis_type,
                target_name=target_name,
                project_name=project_name,
            ),
            impact_tree={},
            package_summary=[],
            sql_details=[],
            test_scope=[],
            has_circular_reference=False,
            circular_paths=[],
        )
