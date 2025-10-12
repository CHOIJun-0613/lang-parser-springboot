from __future__ import annotations

import os
import queue
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator, Optional

from neo4j import Driver, GraphDatabase

from csa.utils.logger import get_logger


@dataclass(frozen=True)
class Neo4jPoolConfig:
    """Immutable configuration for the Neo4j connection pool."""

    uri: str
    user: str
    password: str
    database: str = "neo4j"
    pool_size: int = 10


class _ConnectionWrapper:
    """Thin wrapper that exposes sessions for a given database."""

    def __init__(self, driver: Driver, database: str):
        self.driver = driver
        self.database = database

    def session(self):
        """Create a new session from the underlying driver."""
        return self.driver.session(database=self.database)


class Neo4jConnectionPool:
    """Simple thread-safe Neo4j connection pool (singleton)."""

    _instance: Optional["Neo4jConnectionPool"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "Neo4jConnectionPool":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized"):
            return

        self._initialized = True
        self._pool: "queue.Queue[_ConnectionWrapper]" = queue.Queue()
        self._all_connections: list[_ConnectionWrapper] = []
        self._config: Optional[Neo4jPoolConfig] = None
        self.logger = get_logger(__name__)

    # --------------------------------------------------------------------- #
    # Pool lifecycle                                                        #
    # --------------------------------------------------------------------- #
    def initialize(
        self,
        uri: str,
        user: str,
        password: str,
        database: str,
        pool_size: int = 10,
    ) -> None:
        """Initialise the pool by creating the configured number of connections."""
        self.initialize_with_config(
            Neo4jPoolConfig(
                uri=uri,
                user=user,
                password=password,
                database=database,
                pool_size=pool_size,
            )
        )

    def initialize_with_config(self, config: Neo4jPoolConfig) -> None:
        """Initialise the pool using a config object."""
        if self._all_connections:
            self.logger.warning("Connection pool already initialised; skipping reinitialisation.")
            return

        self._config = config
        self.logger.info(
            "Initialising Neo4j connection pool (%d connections) for database '%s'",
            config.pool_size,
            config.database,
        )

        try:
            for index in range(config.pool_size):
                driver = GraphDatabase.driver(config.uri, auth=(config.user, config.password))
                wrapper = _ConnectionWrapper(driver, config.database)
                self._pool.put(wrapper)
                self._all_connections.append(wrapper)
                self.logger.debug("Created connection %d/%d", index + 1, config.pool_size)

            self.logger.info("Neo4j connection pool initialised successfully.")
        except Exception as exc:  # pylint: disable=broad-except
            self.logger.error("Failed to initialise connection pool: %s", exc)
            self.close_all()
            raise

    def close_all(self) -> None:
        """Close every driver managed by the pool."""
        if not self._all_connections:
            self.logger.info("No Neo4j connections to close.")
            return

        self.logger.info("Closing %d Neo4j connections...", len(self._all_connections))
        for wrapper in self._all_connections:
            try:
                wrapper.driver.close()
            except Exception as exc:  # pylint: disable=broad-except
                self.logger.error("Error closing Neo4j driver: %s", exc)

        self._all_connections.clear()
        while not self._pool.empty():
            try:
                self._pool.get_nowait()
            except queue.Empty:
                break

        self.logger.info("All Neo4j connections have been closed.")

    # --------------------------------------------------------------------- #
    # Acquisition helpers                                                   #
    # --------------------------------------------------------------------- #
    def acquire(self, timeout: int = 30) -> _ConnectionWrapper:
        """Acquire a connection wrapper from the pool."""
        try:
            wrapper = self._pool.get(timeout=timeout)
            self.logger.debug("Connection acquired (available: %d)", self._pool.qsize())
            return wrapper
        except queue.Empty as exc:
            raise TimeoutError(f"Could not acquire connection within {timeout} seconds") from exc

    def release(self, wrapper: _ConnectionWrapper) -> None:
        """Return a connection wrapper to the pool."""
        if wrapper not in self._all_connections:
            self.logger.warning("Attempted to release a connection not owned by this pool.")
            return

        self._pool.put(wrapper)
        self.logger.debug("Connection released (available: %d)", self._pool.qsize())

    @contextmanager
    def connection(self, timeout: int = 30) -> Iterator[_ConnectionWrapper]:
        """
        Context manager that acquires a connection and releases it automatically.

        Example:
            with pool.connection() as conn:
                with conn.session() as session:
                    session.run(...)
        """
        wrapper = self.acquire(timeout=timeout)
        try:
            yield wrapper
        finally:
            self.release(wrapper)

    @contextmanager
    def session(self, timeout: int = 30):
        """Convenience context manager yielding a Neo4j session."""
        with self.connection(timeout=timeout) as wrapper:
            session = wrapper.session()
            try:
                yield session
            finally:
                session.close()

    # --------------------------------------------------------------------- #
    # Pool state helpers                                                    #
    # --------------------------------------------------------------------- #
    def is_initialized(self) -> bool:
        """Return True when the pool has been initialised."""
        return bool(self._all_connections)

    def get_pool_status(self) -> dict:
        """Expose a snapshot of the current pool status."""
        config = self._config or Neo4jPoolConfig("", "", "")
        return {
            "initialized": self.is_initialized(),
            "total_connections": len(self._all_connections),
            "available_connections": self._pool.qsize(),
            "database": config.database,
            "pool_size": config.pool_size,
        }


def get_connection_pool() -> Neo4jConnectionPool:
    """Return the singleton Neo4j connection pool."""
    return Neo4jConnectionPool()


def initialize_pool_from_env() -> Neo4jConnectionPool:
    """Initialise the pool using environment variables."""
    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USER")
    password = os.getenv("NEO4J_PASSWORD")
    database = os.getenv("NEO4J_DATABASE", "neo4j")
    pool_size = int(os.getenv("NEO4J_POOL_SIZE", "10"))

    if not all([uri, user, password]):
        raise ValueError("Missing required Neo4j environment variables: NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD")

    pool = get_connection_pool()
    pool.initialize(uri=uri, user=user, password=password, database=database, pool_size=pool_size)
    return pool


__all__ = [
    "Neo4jConnectionPool",
    "Neo4jPoolConfig",
    "get_connection_pool",
    "initialize_pool_from_env",
]
