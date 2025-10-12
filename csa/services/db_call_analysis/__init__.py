from __future__ import annotations

from csa.services.db_call_analysis.base import DBCallAnalysisBase
from csa.services.db_call_analysis.call_chain import CallChainMixin
from csa.services.db_call_analysis.crud import CrudMatrixMixin
from csa.services.db_call_analysis.diagrams import DiagramMixin
from csa.services.db_call_analysis.impact import ImpactMixin
from csa.services.db_call_analysis.reports import ReportMixin


class DBCallAnalysisService(
    DBCallAnalysisBase,
    CallChainMixin,
    CrudMatrixMixin,
    DiagramMixin,
    ImpactMixin,
    ReportMixin,
):
    """Facade exposing database call analysis features."""


__all__ = ["DBCallAnalysisService"]
