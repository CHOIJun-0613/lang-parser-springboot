"""
Neo4j Connection Pool Manager

이 모듈은 Neo4j 데이터베이스 연결을 관리하는 Connection Pool을 제공합니다.
멀티스레드 환경에서 안전하게 동작하며, 설정된 개수만큼 미리 연결을 생성하여 재사용합니다.
"""

import queue
import threading
import os
from typing import Optional
from neo4j import GraphDatabase, Driver

from csa.utils.logger import get_logger


class ConnectionWrapper:
    """연결과 세션을 래핑하는 클래스"""
    
    def __init__(self, driver: Driver, database: str):
        self.driver = driver
        self.database = database
    
    def session(self):
        """데이터베이스 세션 생성"""
        return self.driver.session(database=self.database)


class Neo4jConnectionPool:
    """Neo4j Connection Pool (Singleton)"""
    
    _instance: Optional['Neo4jConnectionPool'] = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self._pool: queue.Queue = queue.Queue()
        self._all_connections: list[ConnectionWrapper] = []
        self._config: dict = {}
        self.logger = get_logger(__name__)
    
    def initialize(self, uri: str, user: str, password: str, database: str, pool_size: int = 10):
        """Pool 초기화 - 설정된 개수만큼 연결 생성"""
        if self._all_connections:
            self.logger.warning("Connection pool already initialized")
            return
        
        self._config = {
            'uri': uri,
            'user': user,
            'password': password,
            'database': database,
            'pool_size': pool_size
        }
        
        self.logger.info(f"Initializing connection pool: {pool_size} connections to database '{database}'")
        
        try:
            for i in range(pool_size):
                driver = GraphDatabase.driver(uri, auth=(user, password))
                conn = ConnectionWrapper(driver, database)
                self._pool.put(conn)
                self._all_connections.append(conn)
                self.logger.debug(f"Created connection {i+1}/{pool_size}")
            
            self.logger.info(f"Connection pool initialized successfully with {pool_size} connections")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize connection pool: {e}")
            # 실패 시 생성된 연결들 정리
            self.close_all()
            raise
    
    def acquire(self, timeout: int = 30) -> ConnectionWrapper:
        """연결 획득 (blocking, timeout 지원)"""
        try:
            conn = self._pool.get(timeout=timeout)
            self.logger.debug(f"Connection acquired. Available connections: {self._pool.qsize()}")
            return conn
        except queue.Empty:
            raise TimeoutError(f"Could not acquire connection from pool within {timeout} seconds")
    
    def release(self, conn: ConnectionWrapper):
        """연결 반납"""
        if conn not in self._all_connections:
            self.logger.warning("Attempting to release connection not from this pool")
            return
        
        self._pool.put(conn)
        self.logger.debug(f"Connection released. Available connections: {self._pool.qsize()}")
    
    def get_database(self) -> str:
        """데이터베이스 이름 반환"""
        return self._config.get('database', 'neo4j')
    
    def get_pool_size(self) -> int:
        """Pool 크기 반환"""
        return self._config.get('pool_size', 0)
    
    def get_available_connections(self) -> int:
        """사용 가능한 연결 개수 반환"""
        return self._pool.qsize()
    
    def close_all(self):
        """모든 연결 종료"""
        if not self._all_connections:
            self.logger.info("No connections to close")
            return
        
        self.logger.info(f"Closing all {len(self._all_connections)} connections in pool...")
        
        for conn in self._all_connections:
            try:
                conn.driver.close()
            except Exception as e:
                self.logger.error(f"Error closing connection: {e}")
        
        self._all_connections.clear()
        
        # Queue 비우기
        while not self._pool.empty():
            try:
                self._pool.get_nowait()
            except queue.Empty:
                break
        
        self.logger.info("All connections closed")
    
    def is_initialized(self) -> bool:
        """Pool이 초기화되었는지 확인"""
        return len(self._all_connections) > 0
    
    def get_pool_status(self) -> dict:
        """Pool 상태 정보 반환"""
        return {
            'initialized': self.is_initialized(),
            'total_connections': len(self._all_connections),
            'available_connections': self.get_available_connections(),
            'database': self.get_database(),
            'pool_size': self.get_pool_size()
        }


# 편의 함수들
def get_connection_pool() -> Neo4jConnectionPool:
    """Connection Pool 인스턴스 반환"""
    return Neo4jConnectionPool()


def initialize_pool_from_env() -> Neo4jConnectionPool:
    """환경 변수에서 설정을 읽어 Pool 초기화"""
    uri = os.getenv('NEO4J_URI')
    user = os.getenv('NEO4J_USER')
    password = os.getenv('NEO4J_PASSWORD')
    database = os.getenv('NEO4J_DATABASE', 'neo4j')
    pool_size = int(os.getenv('NEO4J_POOL_SIZE', '10'))
    
    if not all([uri, user, password]):
        raise ValueError("Required Neo4j environment variables not set: NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD")
    
    pool = get_connection_pool()
    pool.initialize(uri, user, password, database, pool_size)
    return pool
