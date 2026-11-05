import pytest
from app.services.graph.algorithms.router import GraphAlgorithmRouter
from app.services.graph.algorithms.bfs_traversal import BFSTraversalEngine
from app.services.graph.algorithms.path_finder import PathFinderEngine
from app.services.graph.algorithms.analytics_service import GraphAnalyticsService
from app.services.permissions.permission_resolver import PermissionResolver


@pytest.mark.asyncio
async def test_algo_router_factual_abstention():
    router = GraphAlgorithmRouter()
    # Factual query must abstain to preserve sub-200ms fast path
    evidence = await router.route_and_execute(
        intent="FACTUAL",
        query="What is Ramnarayan's role and title?",
        anchor_ids=["person:ramnarayan-maurya"],
        user_clearance="Internal",
    )
    assert evidence.algorithm_name is None
    assert evidence.query_intent == "FACTUAL"
    assert len(evidence.paths) == 0


@pytest.mark.asyncio
async def test_algo_router_relational_bfs():
    bfs = BFSTraversalEngine()
    paths = await bfs.traverse_bfs(
        anchor_id="person:arjun-nair",
        rel_type="CONNECTED_TO",
        max_depth=2,
        user_clearance="Internal",
    )
    assert len(paths) > 0
    first_path = paths[0]
    assert first_path.source_id == "person:arjun-nair"
    assert len(first_path.nodes) >= 2
    assert "CONNECTED_TO" in first_path.relationships


@pytest.mark.asyncio
async def test_algo_router_causal_shortest_path():
    finder = PathFinderEngine()
    # Query shortest path between Ramnarayan and Bandra Kurla Tower
    paths = await finder.find_shortest_path(
        source_id="person:ramnarayan-maurya",
        target_id="loc:bandra-kurla-tower",
        max_len=4,
        user_clearance="Internal",
    )
    assert len(paths) > 0
    sp = paths[0]
    assert sp.source_id == "person:ramnarayan-maurya"
    assert sp.target_id == "loc:bandra-kurla-tower"
    assert sp.length >= 1
    assert "CONNECTED_TO" in sp.relationships


@pytest.mark.asyncio
async def test_algo_security_clearance_pruning():
    class MockSecurityRestricted:
        def is_node_authorized(self, classification: str | None, user_clearance: str = "Internal") -> bool:
            return False  # Deny all to simulate restricted nodes along path

    bfs = BFSTraversalEngine(perm_resolver=MockSecurityRestricted())
    paths = await bfs.traverse_bfs(
        anchor_id="person:arjun-nair",
        rel_type="CONNECTED_TO",
        max_depth=2,
        user_clearance="Public",
    )
    # When intermediate nodes are unauthorized, paths must be pruned (INV-05)
    assert len(paths) == 0


@pytest.mark.asyncio
async def test_cached_analytics_snapshots():
    analytics = GraphAnalyticsService()
    # 1. PageRank
    pr = await analytics.get_pagerank("Person", "CONNECTED_TO")
    assert isinstance(pr, dict)
    assert len(pr) > 0
    assert any("arjun" in k or "ram" in k for k in pr.keys())

    # 2. Centrality / Betweenness
    hc = await analytics.get_harmonic_centrality()
    assert isinstance(hc, dict)

    # 3. CDLP Communities
    comm = await analytics.get_communities()
    assert isinstance(comm, dict)
    assert len(comm) > 0

