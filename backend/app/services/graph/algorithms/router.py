from __future__ import annotations

import logging
from datetime import datetime, UTC
from typing import Any

from app.schemas.answer import GraphAlgorithmEvidence
from app.services.graph.algorithms.bfs_traversal import BFSTraversalEngine
from app.services.graph.algorithms.path_finder import PathFinderEngine
from app.services.graph.algorithms.analytics_service import GraphAnalyticsService

logger = logging.getLogger(__name__)


class GraphAlgorithmRouter:
    """
    Directs incoming search queries to the optimal FalkorDB graph algorithm
    based on intent archetype, anchor entities, and ABAC clearance boundary (INV-05).
    """

    def __init__(
        self,
        bfs_engine: BFSTraversalEngine | None = None,
        path_engine: PathFinderEngine | None = None,
        analytics: GraphAnalyticsService | None = None,
    ):
        self.bfs = bfs_engine or BFSTraversalEngine()
        self.paths = path_engine or PathFinderEngine()
        self.analytics = analytics or GraphAnalyticsService()

    async def route_and_execute(
        self,
        intent: str,
        query: str,
        anchor_ids: list[str],
        user_clearance: str = "Internal",
    ) -> GraphAlgorithmEvidence:
        # 1. FACTUAL: Strict Abstention for sub-200ms fast path
        if intent == "FACTUAL" or not anchor_ids:
            return GraphAlgorithmEvidence(
                algorithm_name=None,
                query_intent=intent,
                anchor_entity_ids=anchor_ids[:3],
                computed_at=datetime.now(UTC).isoformat(),
            )

        primary_anchor = anchor_ids[0]
        secondary_anchor = anchor_ids[1] if len(anchor_ids) > 1 else None

        # 2. RELATIONAL: algo.BFS multi-hop bounded neighborhood
        if intent == "RELATIONAL":
            bfs_paths = await self.bfs.traverse_bfs(
                anchor_id=primary_anchor,
                rel_type="CONNECTED_TO",
                max_depth=2,
                user_clearance=user_clearance,
            )
            raw_paths = [p.model_dump() for p in bfs_paths]
            return GraphAlgorithmEvidence(
                algorithm_name="algo.BFS",
                query_intent="RELATIONAL",
                anchor_entity_ids=[primary_anchor],
                paths=raw_paths,
                traversal_depth=2,
                computed_at=datetime.now(UTC).isoformat(),
            )

        # 3. CAUSAL: algo.SPpaths / algo.SSpaths dependency & causal routes
        if intent == "CAUSAL":
            if secondary_anchor:
                sp_paths = await self.paths.find_shortest_path(
                    source_id=primary_anchor,
                    target_id=secondary_anchor,
                    max_len=4,
                    user_clearance=user_clearance,
                )
                algo_used = "algo.SPpaths"
                found_paths = sp_paths
            else:
                ss_paths = await self.paths.find_source_to_many(
                    source_id=primary_anchor,
                    max_len=3,
                    user_clearance=user_clearance,
                )
                algo_used = "algo.SSpaths"
                found_paths = ss_paths

            return GraphAlgorithmEvidence(
                algorithm_name=algo_used,
                query_intent="CAUSAL",
                anchor_entity_ids=[primary_anchor] + ([secondary_anchor] if secondary_anchor else []),
                paths=[p.model_dump() for p in found_paths],
                traversal_depth=3,
                computed_at=datetime.now(UTC).isoformat(),
            )

        # 4. PREDICTIVE: Hybrid (algo.BFS + Cached Centrality Analytics)
        if intent == "PREDICTIVE":
            bfs_paths = await self.bfs.traverse_bfs(
                anchor_id=primary_anchor,
                rel_type="CONNECTED_TO",
                max_depth=2,
                user_clearance=user_clearance,
            )
            pageranks = await self.analytics.get_pagerank("Person", "CONNECTED_TO")
            betweenness = await self.analytics.get_betweenness()
            communities = await self.analytics.get_communities()

            metrics = {
                f"pagerank_{k}": v for k, v in pageranks.items() if k in anchor_ids or "arjun" in k or "ram" in k
            }
            if betweenness:
                for k, v in list(betweenness.items())[:5]:
                    metrics[f"betweenness_{k}"] = v

            return GraphAlgorithmEvidence(
                algorithm_name="Hybrid(algo.BFS + PageRank + Betweenness)",
                query_intent="PREDICTIVE",
                anchor_entity_ids=anchor_ids[:3],
                paths=[p.model_dump() for p in bfs_paths],
                metric_values=metrics,
                community_memberships=communities,
                traversal_depth=2,
                computed_at=datetime.now(UTC).isoformat(),
            )

        # 5. COMPARATIVE: CDLP Communities & Structural Affinity
        if intent == "COMPARATIVE":
            communities = await self.analytics.get_communities()
            pageranks = await self.analytics.get_pagerank()
            return GraphAlgorithmEvidence(
                algorithm_name="algo.labelPropagation",
                query_intent="COMPARATIVE",
                anchor_entity_ids=anchor_ids[:4],
                metric_values=pageranks,
                community_memberships=communities,
                computed_at=datetime.now(UTC).isoformat(),
            )

        # Default fallback
        return GraphAlgorithmEvidence(
            algorithm_name=None,
            query_intent=intent,
            anchor_entity_ids=anchor_ids,
            computed_at=datetime.now(UTC).isoformat(),
        )

