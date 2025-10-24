"""
Neo4j 인덱스 및 제약조건 관리
"""
from __future__ import annotations

from csa.services.graph_db.base import GraphDBBase
from csa.utils.logger import get_logger


class IndexManager:
    """Neo4j 인덱스 및 제약조건 관리"""

    def __init__(self, graph_db):
        """
        Args:
            graph_db: GraphDB 인스턴스
        """
        self.graph_db = graph_db
        self.logger = get_logger(__name__)

    def create_all_indexes(self) -> None:
        """
        모든 필수 인덱스 및 제약조건 생성

        성능 최적화를 위해 MERGE, MATCH 연산에 사용되는
        주요 노드 속성에 인덱스를 생성합니다.
        """
        created_count = 0
        skipped_count = 0

        # 1. Project 노드
        if self._create_index("Project", ["name"], unique=True, index_name="idx_project_name"): created_count += 1
        else: skipped_count += 1

        # 2. Package 노드
        if self._create_index("Package", ["name"], unique=False, index_name="idx_package_name"): created_count += 1
        else: skipped_count += 1

        # 3. Class 노드 (복합 인덱스: name + package_name)
        if self._create_index("Class", ["name", "package_name"], unique=False, index_name="idx_class_name_package"): created_count += 1
        else: skipped_count += 1

        # 4. Method 노드 (복합 인덱스: name + class_name)
        if self._create_index("Method", ["name", "class_name"], unique=False, index_name="idx_method_name_class"): created_count += 1
        else: skipped_count += 1

        # 5. Field 노드 (복합 인덱스: name + class_name + project_name)
        if self._create_index("Field", ["name", "class_name", "project_name"], unique=False, index_name="idx_field_name_class_project"): created_count += 1
        else: skipped_count += 1

        # 6. Parameter 노드 (복합 인덱스: name + method_name + class_name)
        if self._create_index("Parameter", ["name", "method_name", "class_name"], unique=False, index_name="idx_parameter_name_method_class"): created_count += 1
        else: skipped_count += 1

        # 7. Bean 노드
        if self._create_index("Bean", ["name"], unique=False, index_name="idx_bean_name"): created_count += 1
        else: skipped_count += 1

        # 8. Endpoint 노드 (복합 인덱스: path + method)
        if self._create_index("Endpoint", ["path", "method"], unique=False, index_name="idx_endpoint_path_method"): created_count += 1
        else: skipped_count += 1

        # 9. MyBatisMapper 노드
        if self._create_index("MyBatisMapper", ["namespace"], unique=False, index_name="idx_mybatis_mapper_namespace"): created_count += 1
        else: skipped_count += 1

        # 10. SqlStatement 노드 (복합 인덱스: id + mapper_name)
        if self._create_index("SqlStatement", ["id", "mapper_name"], unique=False, index_name="idx_sql_statement_id_mapper"): created_count += 1
        else: skipped_count += 1

        # 11. JpaEntity 노드
        if self._create_index("JpaEntity", ["class_name"], unique=False, index_name="idx_jpa_entity_class"): created_count += 1
        else: skipped_count += 1

        # 12. JpaRepository 노드
        if self._create_index("JpaRepository", ["interface_name"], unique=False, index_name="idx_jpa_repository_interface"): created_count += 1
        else: skipped_count += 1

        # 13. Database 노드
        if self._create_index("Database", ["name"], unique=False, index_name="idx_database_name"): created_count += 1
        else: skipped_count += 1

        # 14. Table 노드 (복합 인덱스: name + database_name)
        if self._create_index("Table", ["name", "database_name"], unique=False, index_name="idx_table_name_database"): created_count += 1
        else: skipped_count += 1

        # 15. Column 노드 (복합 인덱스: name + table_name)
        if self._create_index("Column", ["name", "table_name"], unique=False, index_name="idx_column_name_table"): created_count += 1
        else: skipped_count += 1

        # 16. Annotation 노드
        if self._create_index("Annotation", ["name"], unique=False, index_name="idx_annotation_name"): created_count += 1
        else: skipped_count += 1

        # 17. Interface 노드
        if self._create_index("Interface", ["name"], unique=False, index_name="idx_interface_name"): created_count += 1
        else: skipped_count += 1

        # 18. TestClass 노드
        if self._create_index("TestClass", ["name"], unique=False, index_name="idx_test_class_name"): created_count += 1
        else: skipped_count += 1

        # 19. ConfigFile 노드
        result = self._create_index("ConfigFile", ["name"], unique=False, index_name="idx_config_file_name")
        if result: created_count += 1
        else: skipped_count += 1

        if created_count > 0:
            self.logger.info(f"인덱스 생성: {created_count}개 생성, {skipped_count}개 기존 유지")
        else:
            self.logger.info(f"인덱스 확인 완료: 모든 인덱스({created_count + skipped_count}개) 이미 존재함")

    def _create_index(
        self,
        label: str,
        properties: list[str],
        unique: bool = False,
        index_name: str = None
    ) -> bool:
        """
        인덱스 또는 제약조건 생성

        Args:
            label: 노드 레이블 (예: "Class", "Method")
            properties: 인덱스를 생성할 속성 리스트 (복합 인덱스 가능)
            unique: True면 UNIQUE 제약조건, False면 일반 인덱스
            index_name: 인덱스 이름 (선택사항)

        Returns:
            bool: 인덱스 생성 성공 시 True, 이미 존재하면 False
        """
        if not index_name:
            index_name = f"idx_{'_'.join(properties)}".lower()

        props_str = ", ".join([f"n.{prop}" for prop in properties])

        if unique:
            # UNIQUE 제약조건 (자동으로 인덱스도 생성됨)
            query = f"CREATE CONSTRAINT {index_name} IF NOT EXISTS FOR (n:{label}) REQUIRE ({props_str}) IS UNIQUE"
        else:
            # 일반 인덱스
            if len(properties) == 1:
                query = f"CREATE INDEX {index_name} IF NOT EXISTS FOR (n:{label}) ON (n.{properties[0]})"
            else:
                # 복합 인덱스
                query = f"CREATE INDEX {index_name} IF NOT EXISTS FOR (n:{label}) ON ({props_str})"

        try:
            self.graph_db._execute_write(self._create_index_tx, query)
            index_type = "UNIQUE 제약조건" if unique else "인덱스"
            self.logger.debug(f"✓ {label}({', '.join(properties)}) {index_type} 생성: {index_name}")
            return True
        except Exception as e:
            # 이미 존재하거나 다른 이유로 실패한 경우
            if "already exists" in str(e).lower() or "equivalent" in str(e).lower():
                self.logger.debug(f"  {index_name} 이미 존재함 (건너뜀)")
                return False
            else:
                self.logger.warning(f"✗ {index_name} 생성 실패: {e}")
                return False

    @staticmethod
    def _create_index_tx(tx, query: str) -> None:
        """인덱스 생성 트랜잭션"""
        tx.run(query)

    def list_indexes(self) -> list[dict]:
        """
        현재 데이터베이스의 모든 인덱스 조회

        Returns:
            인덱스 정보 리스트
        """
        result = self.graph_db._execute_read(self._list_indexes_tx)
        return result

    @staticmethod
    def _list_indexes_tx(tx) -> list[dict]:
        """인덱스 목록 조회 트랜잭션"""
        result = tx.run("SHOW INDEXES")
        indexes = []
        for record in result:
            indexes.append({
                'name': record.get('name'),
                'state': record.get('state'),
                'type': record.get('type'),
                'entityType': record.get('entityType'),
                'labelsOrTypes': record.get('labelsOrTypes'),
                'properties': record.get('properties'),
            })
        return indexes

    def drop_all_indexes(self) -> None:
        """
        모든 인덱스 및 제약조건 삭제 (주의: 개발/테스트 환경에서만 사용)

        WARNING: 프로덕션 환경에서는 절대 사용하지 마세요!
        """
        indexes = self.list_indexes()

        if not indexes:
            self.logger.debug("삭제할 인덱스가 없습니다.")
            return

        deleted_count = 0
        failed_count = 0

        for idx in indexes:
            idx_name = idx.get('name')
            idx_type = idx.get('type')

            if idx_name:
                try:
                    if 'CONSTRAINT' in idx_type.upper():
                        query = f"DROP CONSTRAINT {idx_name} IF EXISTS"
                    else:
                        query = f"DROP INDEX {idx_name} IF EXISTS"

                    self.graph_db._execute_write(self._drop_index_tx, query)
                    deleted_count += 1
                    self.logger.debug(f"✓ 삭제됨: {idx_name} ({idx_type})")
                except Exception as e:
                    failed_count += 1
                    self.logger.debug(f"✗ {idx_name} 삭제 실패: {e}")

        self.logger.info(f"인덱스 삭제 완료: {deleted_count}개 성공, {failed_count}개 실패")

    @staticmethod
    def _drop_index_tx(tx, query: str) -> None:
        """인덱스 삭제 트랜잭션"""
        tx.run(query)


__all__ = ["IndexManager"]
