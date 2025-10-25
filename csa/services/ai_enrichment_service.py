"""
AI Enrichment Service - Add AI-generated descriptions to existing Neo4j nodes
"""
from __future__ import annotations

import asyncio
import os
from typing import Any, Dict, List, Optional

import click


class AIEnrichmentService:
    """Service to add AI-generated descriptions to nodes without ai_description."""

    def __init__(self, graph_db, ai_analyzer, logger):
        """
        Args:
            graph_db: GraphDB instance
            ai_analyzer: AIAnalyzer instance
            logger: Logger instance
        """
        self.db = graph_db
        self.analyzer = ai_analyzer
        self.logger = logger

    async def enrich_project_async(
        self,
        project_name: str,
        node_type: str = "all",
        concurrent_requests: Optional[int] = None,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Enrich nodes in a project with AI-generated descriptions (비동기 병렬 처리).

        Args:
            project_name: Project name
            node_type: Node type to enrich (all, class, method, sql)
            concurrent_requests: Number of concurrent AI requests (None for env var)
            limit: Maximum number of nodes to process (None for all)

        Returns:
            Dictionary with statistics
        """
        # 동시 요청 수 결정
        if concurrent_requests is None:
            concurrent_requests = int(os.getenv("CONCURRENT_AI_REQUESTS", "10"))

        stats = {
            "total_processed": 0,
            "success_count": 0,
            "fail_count": 0,
            "skipped_count": 0,
            "node_type_stats": {},
            "concurrent_requests": concurrent_requests
        }

        # 노드 타입별로 처리
        if node_type in ("all", "class"):
            class_stats = await self._enrich_classes_async(project_name, concurrent_requests, limit)
            stats["total_processed"] += class_stats["processed"]
            stats["success_count"] += class_stats["success"]
            stats["fail_count"] += class_stats["failed"]
            stats["skipped_count"] += class_stats["skipped"]
            stats["node_type_stats"]["Class"] = class_stats

        if node_type in ("all", "method"):
            method_stats = await self._enrich_methods_async(project_name, concurrent_requests, limit)
            stats["total_processed"] += method_stats["processed"]
            stats["success_count"] += method_stats["success"]
            stats["fail_count"] += method_stats["failed"]
            stats["skipped_count"] += method_stats["skipped"]
            stats["node_type_stats"]["Method"] = method_stats

        if node_type in ("all", "sql"):
            sql_stats = await self._enrich_sql_statements_async(project_name, concurrent_requests, limit)
            stats["total_processed"] += sql_stats["processed"]
            stats["success_count"] += sql_stats["success"]
            stats["fail_count"] += sql_stats["failed"]
            stats["skipped_count"] += sql_stats["skipped"]
            stats["node_type_stats"]["SqlStatement"] = sql_stats

        return stats

    def enrich_project(
        self,
        project_name: str,
        node_type: str = "all",
        batch_size: int = 50,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Enrich nodes in a project with AI-generated descriptions (하위 호환성을 위한 동기 버전).

        Args:
            project_name: Project name
            node_type: Node type to enrich (all, class, method, sql)
            batch_size: Batch size for processing (deprecated, use concurrent_requests)
            limit: Maximum number of nodes to process (None for all)

        Returns:
            Dictionary with statistics
        """
        # 비동기 메서드를 asyncio.run()으로 실행
        return asyncio.run(self.enrich_project_async(
            project_name=project_name,
            node_type=node_type,
            concurrent_requests=batch_size,  # batch_size를 concurrent_requests로 사용
            limit=limit
        ))

    def _enrich_classes(
        self,
        project_name: str,
        batch_size: int,
        limit: Optional[int]
    ) -> Dict[str, int]:
        """Enrich Class nodes with AI descriptions."""
        stats = {"processed": 0, "success": 0, "failed": 0, "skipped": 0}

        # Neo4j 쿼리: ai_description이 비어있거나 없는 Class 노드 조회
        query = """
        MATCH (c:Class)
        WHERE c.project_name = $project_name
          AND (c.ai_description IS NULL OR c.ai_description = '')
          AND c.source IS NOT NULL AND c.source <> ''
        RETURN c.name as name,
               c.source as source,
               elementId(c) as node_id
        ORDER BY c.name
        """
        if limit:
            query += f" LIMIT {limit}"

        with self.db.driver.session(database=self.db.database) as session:
            result = session.run(query, project_name=project_name)
            classes = list(result)

        total = len(classes)
        if total == 0:
            self.logger.info("No Class nodes found that need AI enrichment")
            return stats

        self.logger.info(f"Found {total} Class nodes to enrich")
        self.logger.info(f"Processing {total} Class nodes...")

        # 배치 처리
        for i, record in enumerate(classes, 1):
            class_name = record["name"]
            source = record["source"]
            node_id = record["node_id"]

            try:
                # AI 분석
                ai_description = self.analyzer.analyze_class(source, class_name)

                if ai_description:
                    # Neo4j 업데이트
                    self._update_node_ai_description(node_id, ai_description)
                    stats["success"] += 1
                    self.logger.info(f"[{i}/{total}] Class enriched: {class_name}")
                else:
                    stats["failed"] += 1
                    self.logger.warning(f"[{i}/{total}] Class AI analysis returned empty: {class_name}")

            except Exception as exc:
                stats["failed"] += 1
                self.logger.error(f"[{i}/{total}] Class enrichment failed ({class_name}): {exc}")

            stats["processed"] += 1

            # 진행률 표시
            #if i % batch_size == 0 or i == total:
            if i <= total:
                self.logger.info(f"  Progress: {i}/{total} ({i*100//total}%) - Success: {stats['success']}, Failed: {stats['failed']}")

        return stats

    async def _enrich_classes_async(
        self,
        project_name: str,
        concurrent_requests: int,
        limit: Optional[int]
    ) -> Dict[str, int]:
        """Enrich Class nodes with AI descriptions (비동기 병렬 처리)."""
        stats = {"processed": 0, "success": 0, "failed": 0, "skipped": 0}

        # Neo4j 쿼리: ai_description이 비어있거나 없는 Class 노드 조회
        query = """
        MATCH (c:Class)
        WHERE c.project_name = $project_name
          AND (c.ai_description IS NULL OR c.ai_description = '')
          AND c.source IS NOT NULL AND c.source <> ''
        RETURN c.name as name,
               c.source as source,
               elementId(c) as node_id
        ORDER BY c.name
        """
        if limit:
            query += f" LIMIT {limit}"

        with self.db.driver.session(database=self.db.database) as session:
            result = session.run(query, project_name=project_name)
            classes = list(result)

        total = len(classes)
        if total == 0:
            self.logger.info("No Class nodes found that need AI enrichment")
            return stats

        self.logger.info(f"Found {total} Class nodes to enrich")
        self.logger.info(f"Processing {total} Class nodes with {concurrent_requests} concurrent requests...")

        # Semaphore로 동시 요청 수 제한
        semaphore = asyncio.Semaphore(concurrent_requests)

        async def process_class(record, index):
            """단일 Class 노드 처리"""
            async with semaphore:
                class_name = record["name"]
                source = record["source"]
                node_id = record["node_id"]

                try:
                    # AI 분석 (비동기)
                    ai_description = await self.analyzer.analyze_class_async(source, class_name)

                    if ai_description:
                        # Neo4j 업데이트
                        self._update_node_ai_description(node_id, ai_description)
                        self.logger.info(f"[{index}/{total}] Class enriched: {class_name}")
                        return {"status": "success", "name": class_name}
                    else:
                        self.logger.warning(f"[{index}/{total}] Class AI analysis returned empty: {class_name}")
                        return {"status": "failed", "name": class_name}

                except Exception as exc:
                    self.logger.error(f"[{index}/{total}] Class enrichment failed ({class_name}): {exc}")
                    return {"status": "failed", "name": class_name}

        # 모든 Class를 병렬 처리
        tasks = [process_class(record, i+1) for i, record in enumerate(classes)]
        results = await asyncio.gather(*tasks)

        # 통계 계산
        for result in results:
            stats["processed"] += 1
            if result["status"] == "success":
                stats["success"] += 1
            else:
                stats["failed"] += 1

        self.logger.info(f"Completed: {total}/{total} (100%) - Success: {stats['success']}, Failed: {stats['failed']}")
        return stats

    def _enrich_methods(
        self,
        project_name: str,
        batch_size: int,
        limit: Optional[int]
    ) -> Dict[str, int]:
        """Enrich Method nodes with AI descriptions."""
        stats = {"processed": 0, "success": 0, "failed": 0, "skipped": 0}

        # Neo4j 쿼리: ai_description이 비어있거나 없는 Method 노드 조회
        query = """
        MATCH (c:Class)-[:HAS_METHOD]->(m:Method)
        WHERE c.project_name = $project_name
          AND (m.ai_description IS NULL OR m.ai_description = '')
          AND m.source IS NOT NULL AND m.source <> ''
        RETURN c.name as class_name,
               m.name as method_name,
               m.source as source,
               elementId(m) as node_id
        ORDER BY c.name, m.name
        """
        if limit:
            query += f" LIMIT {limit}"

        with self.db.driver.session(database=self.db.database) as session:
            result = session.run(query, project_name=project_name)
            methods = list(result)

        total = len(methods)
        if total == 0:
            self.logger.info("No Method nodes found that need AI enrichment")
            return stats

        self.logger.info(f"Found {total} Method nodes to enrich")
        self.logger.info(f"Processing {total} Method nodes...")

        # 배치 처리
        for i, record in enumerate(methods, 1):
            class_name = record["class_name"]
            method_name = record["method_name"]
            source = record["source"]
            node_id = record["node_id"]

            try:
                # AI 분석
                ai_description = self.analyzer.analyze_method(source, method_name, class_name)

                if ai_description:
                    # Neo4j 업데이트
                    self._update_node_ai_description(node_id, ai_description)
                    stats["success"] += 1
                    self.logger.info(f"[{i}/{total}] Method enriched: {class_name}.{method_name}")
                else:
                    stats["failed"] += 1
                    self.logger.warning(f"[{i}/{total}] Method AI analysis returned empty: {class_name}.{method_name}")

            except Exception as exc:
                stats["failed"] += 1
                self.logger.error(f"[{i}/{total}] Method enrichment failed ({class_name}.{method_name}): {exc}")

            stats["processed"] += 1

            # 진행률 표시
            #if i % batch_size == 0 or i == total:
            if i <= total:
                click.echo(f"  Progress: {i}/{total} ({i*100//total}%) - Success: {stats['success']}, Failed: {stats['failed']}")

        return stats

    async def _enrich_methods_async(
        self,
        project_name: str,
        concurrent_requests: int,
        limit: Optional[int]
    ) -> Dict[str, int]:
        """Enrich Method nodes with AI descriptions (비동기 병렬 처리)."""
        stats = {"processed": 0, "success": 0, "failed": 0, "skipped": 0}

        # Neo4j 쿼리: ai_description이 비어있거나 없는 Method 노드 조회
        query = """
        MATCH (c:Class)-[:HAS_METHOD]->(m:Method)
        WHERE c.project_name = $project_name
          AND (m.ai_description IS NULL OR m.ai_description = '')
          AND m.source IS NOT NULL AND m.source <> ''
        RETURN c.name as class_name,
               m.name as method_name,
               m.source as source,
               elementId(m) as node_id
        ORDER BY c.name, m.name
        """
        if limit:
            query += f" LIMIT {limit}"

        with self.db.driver.session(database=self.db.database) as session:
            result = session.run(query, project_name=project_name)
            methods = list(result)

        total = len(methods)
        if total == 0:
            self.logger.info("No Method nodes found that need AI enrichment")
            return stats

        self.logger.info(f"Found {total} Method nodes to enrich")
        self.logger.info(f"Processing {total} Method nodes with {concurrent_requests} concurrent requests...")

        # Semaphore로 동시 요청 수 제한
        semaphore = asyncio.Semaphore(concurrent_requests)

        async def process_method(record, index):
            """단일 Method 노드 처리"""
            async with semaphore:
                class_name = record["class_name"]
                method_name = record["method_name"]
                source = record["source"]
                node_id = record["node_id"]

                try:
                    # AI 분석 (비동기)
                    ai_description = await self.analyzer.analyze_method_async(source, method_name, class_name)

                    if ai_description:
                        # Neo4j 업데이트
                        self._update_node_ai_description(node_id, ai_description)
                        self.logger.info(f"[{index}/{total}] Method enriched: {class_name}.{method_name}")
                        return {"status": "success", "name": f"{class_name}.{method_name}"}
                    else:
                        self.logger.warning(f"[{index}/{total}] Method AI analysis returned empty: {class_name}.{method_name}")
                        return {"status": "failed", "name": f"{class_name}.{method_name}"}

                except Exception as exc:
                    self.logger.error(f"[{index}/{total}] Method enrichment failed ({class_name}.{method_name}): {exc}")
                    return {"status": "failed", "name": f"{class_name}.{method_name}"}

        # 모든 Method를 병렬 처리
        tasks = [process_method(record, i+1) for i, record in enumerate(methods)]
        results = await asyncio.gather(*tasks)

        # 통계 계산
        for result in results:
            stats["processed"] += 1
            if result["status"] == "success":
                stats["success"] += 1
            else:
                stats["failed"] += 1

        self.logger.info(f"Completed: {total}/{total} (100%) - Success: {stats['success']}, Failed: {stats['failed']}")
        return stats

    def _enrich_sql_statements(
        self,
        project_name: str,
        batch_size: int,
        limit: Optional[int]
    ) -> Dict[str, int]:
        """Enrich SqlStatement nodes with AI descriptions."""
        stats = {"processed": 0, "success": 0, "failed": 0, "skipped": 0}

        # Neo4j 쿼리: ai_description이 비어있거나 없는 SqlStatement 노드 조회
        query = """
        MATCH (s:SqlStatement)
        WHERE s.project_name = $project_name
          AND (s.ai_description IS NULL OR s.ai_description = '')
          AND s.sql_content IS NOT NULL AND s.sql_content <> ''
        RETURN s.id as sql_id,
               s.mapper_name as mapper_name,
               s.sql_content as sql_content,
               elementId(s) as node_id
        ORDER BY s.mapper_name, s.id
        """
        if limit:
            query += f" LIMIT {limit}"

        with self.db.driver.session(database=self.db.database) as session:
            result = session.run(query, project_name=project_name)
            sql_statements = list(result)

        total = len(sql_statements)
        if total == 0:
            self.logger.info("No SqlStatement nodes found that need AI enrichment")
            return stats

        self.logger.info(f"Found {total} SqlStatement nodes to enrich")
        self.logger.info(f"Processing {total} SqlStatement nodes...")

        # 배치 처리
        for i, record in enumerate(sql_statements, 1):
            sql_id = record["sql_id"]
            mapper_name = record["mapper_name"]
            sql_content = record["sql_content"]
            node_id = record["node_id"]

            try:
                # AI 분석
                ai_description = self.analyzer.analyze_sql(sql_content, sql_id)

                if ai_description:
                    # Neo4j 업데이트
                    self._update_node_ai_description(node_id, ai_description)
                    stats["success"] += 1
                    self.logger.debug(f"[{i}/{total}] SQL enriched: {mapper_name}.{sql_id}")
                else:
                    stats["failed"] += 1
                    self.logger.warning(f"[{i}/{total}] SQL AI analysis returned empty: {mapper_name}.{sql_id}")

            except Exception as exc:
                stats["failed"] += 1
                self.logger.error(f"[{i}/{total}] SQL enrichment failed ({mapper_name}.{sql_id}): {exc}")

            stats["processed"] += 1

            # 진행률 표시
            #if i % batch_size == 0 or i == total:
            if i <= total:
                self.logger.info(f"  Progress: {i}/{total} ({i*100//total}%) - Success: {stats['success']}, Failed: {stats['failed']}")

        return stats

    async def _enrich_sql_statements_async(
        self,
        project_name: str,
        concurrent_requests: int,
        limit: Optional[int]
    ) -> Dict[str, int]:
        """Enrich SqlStatement nodes with AI descriptions (비동기 병렬 처리)."""
        stats = {"processed": 0, "success": 0, "failed": 0, "skipped": 0}

        # Neo4j 쿼리: ai_description이 비어있거나 없는 SqlStatement 노드 조회
        query = """
        MATCH (s:SqlStatement)
        WHERE s.project_name = $project_name
          AND (s.ai_description IS NULL OR s.ai_description = '')
          AND s.sql_content IS NOT NULL AND s.sql_content <> ''
        RETURN s.id as sql_id,
               s.mapper_name as mapper_name,
               s.sql_content as sql_content,
               elementId(s) as node_id
        ORDER BY s.mapper_name, s.id
        """
        if limit:
            query += f" LIMIT {limit}"

        with self.db.driver.session(database=self.db.database) as session:
            result = session.run(query, project_name=project_name)
            sql_statements = list(result)

        total = len(sql_statements)
        if total == 0:
            self.logger.info("No SqlStatement nodes found that need AI enrichment")
            return stats

        self.logger.info(f"Found {total} SqlStatement nodes to enrich")
        self.logger.info(f"Processing {total} SqlStatement nodes with {concurrent_requests} concurrent requests...")

        # Semaphore로 동시 요청 수 제한
        semaphore = asyncio.Semaphore(concurrent_requests)

        async def process_sql(record, index):
            """단일 SQL 노드 처리"""
            async with semaphore:
                sql_id = record["sql_id"]
                mapper_name = record["mapper_name"]
                sql_content = record["sql_content"]
                node_id = record["node_id"]

                try:
                    # AI 분석 (비동기)
                    ai_description = await self.analyzer.analyze_sql_async(sql_content, sql_id)

                    if ai_description:
                        # Neo4j 업데이트
                        self._update_node_ai_description(node_id, ai_description)
                        self.logger.info(f"[{index}/{total}] SQL enriched: {mapper_name}.{sql_id}")
                        return {"status": "success", "name": f"{mapper_name}.{sql_id}"}
                    else:
                        self.logger.warning(f"[{index}/{total}] SQL AI analysis returned empty: {mapper_name}.{sql_id}")
                        return {"status": "failed", "name": f"{mapper_name}.{sql_id}"}

                except Exception as exc:
                    self.logger.error(f"[{index}/{total}] SQL enrichment failed ({mapper_name}.{sql_id}): {exc}")
                    return {"status": "failed", "name": f"{mapper_name}.{sql_id}"}

        # 모든 SQL을 병렬 처리
        tasks = [process_sql(record, i+1) for i, record in enumerate(sql_statements)]
        results = await asyncio.gather(*tasks)

        # 통계 계산
        for result in results:
            stats["processed"] += 1
            if result["status"] == "success":
                stats["success"] += 1
            else:
                stats["failed"] += 1

        self.logger.info(f"Completed: {total}/{total} (100%) - Success: {stats['success']}, Failed: {stats['failed']}")
        return stats

    def _update_node_ai_description(self, node_id: str, ai_description: str) -> None:
        """
        Update node's ai_description in Neo4j.

        Args:
            node_id: Neo4j element ID
            ai_description: AI-generated description
        """
        query = """
        MATCH (n)
        WHERE elementId(n) = $node_id
        SET n.ai_description = $ai_description
        """
        with self.db.driver.session(database=self.db.database) as session:
            session.run(query, node_id=node_id, ai_description=ai_description)


__all__ = ["AIEnrichmentService"]
