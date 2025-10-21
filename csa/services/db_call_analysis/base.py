from __future__ import annotations

import os
from neo4j import Driver

from csa.utils.logger import get_logger


class DBCallAnalysisBase:
    """Owns the Neo4j driver shared by analysis mixins."""

    def __init__(self, driver: Driver, database: str = None):
        self.driver = driver
        self.database = database or os.getenv("NEO4J_DATABASE", "neo4j")
        self.logger = get_logger(__name__)

    def _open_session(self):
        """Return a new Neo4j session."""
        return self.driver.session(database=self.database)
