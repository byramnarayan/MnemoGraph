from __future__ import annotations

import logging
import uuid
from datetime import datetime, UTC
from typing import Any
from starlette.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.graph.falkordb_client import FalkorDBClient
from app.models.graph_analytics import GraphAnalyticsSnapshot

logger = logging.getLogger(__name__)


class GraphAnalyticsService:
    """
    Manages cached analytical snapshots for global graph topology algorithms:
    PageRank, Betweenness, HarmonicCentrality, LabelPropagation (CDLP), and WCC.
    """

    _cache: dict[str, tuple[datetime, dict[str, Any]]] = {}
    CACHE_TTL_SECONDS = 3600

    def __init__(self, falkor: FalkorDBClient | None = None):
        self.falkor = falkor or FalkorDBClient()

    async def get_pagerank(self, label: str = "Person", rel: str = "CONNECTED_TO") -> dict[str, float]:
        cache_key = f"pagerank_{label}_{rel}"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        def _run():
            cypher = f"CALL algo.pageRank('{label}', '{rel}') YIELD node, score RETURN node.id, score LIMIT 100"
            return self.falkor.query(cypher)

        try:
            rows = await run_in_threadpool(_run)
            res = {str(r[0]): round(float(r[1]), 5) for r in rows if r and len(r) >= 2 and r[0]}
            self._set_cache(cache_key, res)
            return res
        except Exception as exc:
            logger.warning(f"algo.pageRank query error: {exc}")
            return {}

    async def get_betweenness(self) -> dict[str, float]:
        cache_key = "betweenness_global"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        def _run():
            cypher = "CALL algo.betweenness() YIELD node, score RETURN node.id, score LIMIT 100"
            return self.falkor.query(cypher)

        try:
            rows = await run_in_threadpool(_run)
            res = {str(r[0]): round(float(r[1]), 4) for r in rows if r and len(r) >= 2 and r[0]}
            self._set_cache(cache_key, res)
            return res
        except Exception as exc:
            logger.warning(f"algo.betweenness error: {exc}")
            return {}

    async def get_harmonic_centrality(self) -> dict[str, float]:
        cache_key = "harmonic_centrality_global"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        def _run():
            cypher = "CALL algo.HarmonicCentrality({}) YIELD node, score RETURN node.id, score LIMIT 100"
            return self.falkor.query(cypher)

        try:
            rows = await run_in_threadpool(_run)
            res = {str(r[0]): round(float(r[1]), 4) for r in rows if r and len(r) >= 2 and r[0]}
            self._set_cache(cache_key, res)
            return res
        except Exception as exc:
            logger.warning(f"algo.HarmonicCentrality error: {exc}")
            return {}

    async def get_communities(self) -> dict[str, int]:
        cache_key = "communities_cdlp"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        def _run():
            cypher = "CALL algo.labelPropagation() YIELD node, communityId RETURN node.id, communityId LIMIT 100"
            return self.falkor.query(cypher)

        try:
            rows = await run_in_threadpool(_run)
            res = {str(r[0]): int(r[1]) for r in rows if r and len(r) >= 2 and r[0]}
            self._set_cache(cache_key, res)
            return res
        except Exception as exc:
            logger.warning(f"algo.labelPropagation error: {exc}")
            return {}

    async def persist_snapshot(
        self,
        db: AsyncSession,
        algorithm_name: str,
        metrics: dict[str, Any],
        target_label: str | None = None,
        rel_type: str | None = None,
    ) -> GraphAnalyticsSnapshot:
        snap = GraphAnalyticsSnapshot(
            id=f"snap_{algorithm_name}_{uuid.uuid4().hex[:8]}",
            algorithm_name=algorithm_name,
            target_label=target_label,
            relationship_type=rel_type,
            parameters={"label": target_label, "rel_type": rel_type},
            metric_values=metrics,
            node_count=len(metrics),
            computed_at=datetime.now(UTC),
        )
        db.add(snap)
        await db.commit()
        await db.refresh(snap)
        return snap

    def _get_from_cache(self, key: str) -> dict[str, Any] | None:
        if key in self._cache:
            ts, val = self._cache[key]
            if (datetime.now(UTC) - ts).total_seconds() < self.CACHE_TTL_SECONDS:
                return val
        return None

    def _set_cache(self, key: str, value: dict[str, Any]) -> None:
        self._cache[key] = (datetime.now(UTC), value)

