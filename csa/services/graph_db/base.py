from __future__ import annotations

from datetime import datetime
from typing import Any, Callable

from neo4j import Driver, GraphDatabase

from csa.utils.logger import get_logger


class GraphDBBase:
    """Base class that owns the Neo4j driver and shared helpers."""

    def __init__(self, uri: str, user: str, password: str, database: str = "neo4j") -> None:
        self._driver: Driver = GraphDatabase.driver(uri, auth=(user, password))
        self._database = database
        self.logger = get_logger(__name__)

    @property
    def driver(self) -> Driver:
        """Return the Neo4j driver instance."""
        return self._driver

    @property
    def database(self) -> str:
        """Return the database name."""
        return self._database

    @staticmethod
    def _get_current_timestamp() -> str:
        """Return current timestamp formatted as YYYY/MM/DD HH24:Mi:SS.sss."""
        return datetime.now().strftime("%Y/%m/%d %H:%M:%S.%f")[:-3]

    def close(self) -> None:
        """Close the underlying database connection."""
        self._driver.close()

    def _execute_write(self, transaction_function: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute a write transaction against the database."""
        with self._driver.session(database=self._database) as session:
            if hasattr(session, "write_transaction"):
                return session.write_transaction(transaction_function, *args, **kwargs)
            return session.execute_write(transaction_function, *args, **kwargs)

    def _execute_read(self, transaction_function: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute a read transaction against the database."""
        with self._driver.session(database=self._database) as session:
            if hasattr(session, "read_transaction"):
                return session.read_transaction(transaction_function, *args, **kwargs)
            return session.execute_read(transaction_function, *args, **kwargs)
