"""
영향도 분석 데이터 모델

테이블 또는 메서드 변경 시 영향받는 코드 요소들을 추적하기 위한 데이터 모델
"""
from __future__ import annotations

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class ImpactNode(BaseModel):
    """영향도 분석 노드

    호출 체인의 각 노드(클래스, 메서드, SQL 등)를 표현하는 모델
    """
    level: int = Field(description="영향도 레벨 (1: 직접, 2+: 간접)")
    depth: int = Field(description="호출 깊이 (0: 직접 호출)")
    package_name: str = Field(description="패키지명")
    class_name: str = Field(description="클래스명")
    method_name: str = Field(description="메서드명")
    project_name: Optional[str] = Field(default=None, description="프로젝트명")
    sql_id: Optional[str] = Field(default=None, description="SQL ID")
    sql_type: Optional[str] = Field(default=None, description="SQL 타입 (SELECT/INSERT/UPDATE/DELETE)")
    sql_complexity: Optional[int] = Field(default=None, description="SQL 복잡도")
    risk_grade: str = Field(default="LOW", description="리스크 등급 (HIGH/MEDIUM/LOW)")

    class Config:
        allow_mutation = True


class ImpactSummary(BaseModel):
    """영향도 분석 요약

    전체 영향도 분석 결과의 통계 정보
    """
    target_type: str = Field(description="분석 대상 타입 (table/method)")
    target_name: str = Field(description="분석 대상 이름")
    project_name: Optional[str] = Field(default=None, description="프로젝트명 (선택사항)")
    total_impacted_classes: int = Field(default=0, description="영향받는 클래스 수")
    total_impacted_methods: int = Field(default=0, description="영향받는 메서드 수")
    total_impacted_packages: int = Field(default=0, description="영향받는 패키지 수")
    max_depth: int = Field(default=0, description="최대 호출 깊이")
    avg_depth: float = Field(default=0.0, description="평균 호출 깊이")
    risk_distribution: Dict[str, int] = Field(
        default_factory=lambda: {"HIGH": 0, "MEDIUM": 0, "LOW": 0},
        description="리스크 등급별 개수"
    )

    class Config:
        allow_mutation = True


class PackageSummary(BaseModel):
    """패키지별 통계

    패키지별로 그룹핑된 영향도 통계
    """
    package_name: str = Field(description="패키지명")
    impacted_classes: int = Field(default=0, description="영향받는 클래스 수")
    impacted_methods: int = Field(default=0, description="영향받는 메서드 수")
    avg_depth: float = Field(default=0.0, description="평균 호출 깊이")
    risk_distribution: Dict[str, int] = Field(
        default_factory=lambda: {"HIGH": 0, "MEDIUM": 0, "LOW": 0},
        description="리스크 등급별 개수"
    )

    class Config:
        allow_mutation = True


class SqlDetail(BaseModel):
    """SQL 상세 정보 (테이블 영향도 분석 시)

    영향받는 SQL 문의 상세 정보
    """
    sql_id: str = Field(description="SQL ID")
    sql_type: str = Field(description="SQL 타입 (SELECT/INSERT/UPDATE/DELETE)")
    mapper_class: Optional[str] = Field(default=None, description="매퍼 클래스명")
    mapper_method: Optional[str] = Field(default=None, description="매퍼 메서드명")
    complexity: int = Field(default=0, description="SQL 복잡도")
    query_preview: Optional[str] = Field(default=None, description="쿼리 미리보기 (앞 100자)")

    class Config:
        allow_mutation = True


class TestScopeItem(BaseModel):
    """테스트 범위 항목

    영향받는 클래스에 대응하는 테스트 클래스 정보
    """
    impacted_class: str = Field(description="영향받는 클래스명")
    test_class: Optional[str] = Field(default=None, description="대응 테스트 클래스명")
    test_method_count: int = Field(default=0, description="테스트 메서드 수")
    status: str = Field(default="미존재", description="테스트 존재 여부 (존재/미존재)")

    class Config:
        allow_mutation = True


class ImpactAnalysisResult(BaseModel):
    """영향도 분석 결과

    테이블 또는 메서드 변경 영향도 분석의 최종 결과
    """
    project_name: Optional[str] = Field(default=None, description="프로젝트명 (선택사항)")
    analysis_type: str = Field(description="분석 타입 (table/method)")
    target_name: str = Field(description="분석 대상 이름")
    timestamp: str = Field(description="분석 시각 (YYYYMMDD-HHmmss)")
    summary: ImpactSummary = Field(description="영향도 요약")
    impact_tree: Dict[int, List[ImpactNode]] = Field(
        default_factory=dict,
        description="Level별 노드 목록 (key: level, value: 노드 리스트)"
    )
    package_summary: List[PackageSummary] = Field(
        default_factory=list,
        description="패키지별 통계"
    )
    sql_details: List[SqlDetail] = Field(
        default_factory=list,
        description="SQL 상세 정보 (테이블 영향도만)"
    )
    test_scope: List[TestScopeItem] = Field(
        default_factory=list,
        description="테스트 범위"
    )
    has_circular_reference: bool = Field(
        default=False,
        description="순환 참조 존재 여부"
    )
    circular_paths: List[str] = Field(
        default_factory=list,
        description="순환 참조 경로 목록"
    )

    class Config:
        allow_mutation = True
