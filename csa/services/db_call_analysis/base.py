from __future__ import annotations

from neo4j import Driver

from csa.utils.logger import get_logger


class DBCallAnalysisBase:
    """Owns the Neo4j driver shared by analysis mixins."""

    def __init__(self, driver: Driver):
        self.driver = driver
        self.logger = get_logger(__name__)

    def _open_session(self):
        """Return a new Neo4j session."""
        return self.driver.session()
