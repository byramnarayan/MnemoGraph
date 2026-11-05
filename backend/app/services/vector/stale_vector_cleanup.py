from __future__ import annotations

import logging
import uuid
from typing import Any, Optional
from starlette.concurrency import run_in_threadpool
from qdrant_client import models
from qdrant_client.http.models import PointStruct

from app.core.config import settings
from app.services.graph.falkordb_client import FalkorDBClient
from app.services.vector.embeddings import embed_texts
from app.services.vector.indexer import StructureAwareChunker, VectorIndexer
from app.services.vector.qdrant_client import QdrantService

logger = logging.getLogger(__name__)


class StaleVectorCleanup:
    """
    Deletes or purges vector chunks in Qdrant when a document is updated,
    moved, or deleted.
    """

    def __init__(self, qdrant: Optional[QdrantService] = None):
        self.qdrant = qdrant or QdrantService()

    async def delete_document_vectors(self, document_id: str) -> int:
        """
        Deletes all vector points where payload document_id matches.
        """
        def _exec():
            client = self.qdrant.client
            collection_name = self.qdrant.collection_name

            # Check if collection exists
            try:
                collections = [c.name for c in client.get_collections().collections]
                if collection_name not in collections:
                    return 0
            except Exception:
                return 0

            try:
                # Count points first
                count_res = client.count(
                    collection_name=collection_name,
                    count_filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="document_id",
                                match=models.MatchValue(value=document_id),
                            )
                        ]
                    ),
                )
                pts_count = count_res.count

                if pts_count > 0:
                    client.delete(
                        collection_name=collection_name,
                        points_selector=models.FilterSelector(
                            filter=models.Filter(
                                must=[
                                    models.FieldCondition(
                                        key="document_id",
                                        match=models.MatchValue(value=document_id),
                                    )
                                ]
                            )
                        ),
                    )
                    logger.info(f"Purged {pts_count} vector chunks for document {document_id}")

                return pts_count
            except Exception as e:
                logger.warning(f"Could not purge vectors for document {document_id}: {e}")
                return 0

        return await run_in_threadpool(_exec)


class CascadeReindexingService:
    """
    UKGOE Step 3.3: Automated Re-Indexing on Graph Update (IR-09 Cascade Listener).
    Reacts to IR-09 DOWNSTREAM_INVALIDATION events, re-fetching affected node properties
    and 1-hop graph neighbors from FalkorDB, re-rendering with StructureAwareChunker,
    and idempotently updating Qdrant points with deterministic UUID5.
    """

    def __init__(
        self,
        qdrant: Optional[QdrantService] = None,
        falkordb: Optional[FalkorDBClient] = None,
        indexer: Optional[VectorIndexer] = None,
    ):
        self.qdrant = qdrant or QdrantService()
        self.falkordb = falkordb or FalkorDBClient()
        self.indexer = indexer or VectorIndexer(qdrant_service=self.qdrant)

    async def handle_downstream_invalidation(
        self,
        affected_node_ids: list[str],
        triggered_by_node_id: str,
    ) -> int:
        """
        Re-fetches, re-renders, re-embeds, and updates Qdrant points for all affected nodes.
        """
        if not affected_node_ids:
            return 0

        def _exec() -> int:
            reindexed_count = 0
            for node_id in affected_node_ids:
                # Query node and 1-hop neighbors from FalkorDB
                cypher = f"""
                MATCH (n {{id: '{node_id}'}})
                OPTIONAL MATCH (n)-[r]-(neighbor)
                RETURN labels(n), properties(n), collect({{id: neighbor.id, relation: type(r), label: labels(neighbor)[0]}})
                """
                rows = self.falkordb.query(cypher)
                if not rows or not rows[0]:
                    continue

                labels, props, neighbors = rows[0]
                # Filter out empty neighbor dicts
                valid_neighbors = [
                    n for n in (neighbors or [])
                    if isinstance(n, dict) and n.get("id")
                ]

                # Identify primary label (excluding Stub or MULTI_CAUSE if other label exists)
                primary_label = "Entity"
                for lbl in (labels or []):
                    if lbl not in ["Stub", "MULTI_CAUSE", "EpisodeMemory"]:
                        primary_label = lbl
                        break
                if primary_label == "Entity" and labels:
                    primary_label = labels[0]

                # Synthesize fresh natural language text
                rendered_text = StructureAwareChunker.render_entity(
                    entity_class=primary_label,
                    properties=props or {},
                    neighbors=valid_neighbors,
                )

                # Compute dense embedding via FastEmbed
                vector = embed_texts([rendered_text])[0]

                # Deterministic UUID5 point ID
                point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{node_id}_0"))

                payload = self.indexer.build_15_field_payload(
                    document_id=props.get("source_doc_id"),
                    entity_id=node_id,
                    entity_class=primary_label,
                    chunk_index=0,
                    text=rendered_text,
                    metadata=props,
                    graph_neighbors=valid_neighbors,
                )
                payload["recompute_triggered_by"] = triggered_by_node_id

                point = PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload,
                )

                self.qdrant.client.upsert(
                    collection_name=self.qdrant.collection_name,
                    points=[point],
                )
                reindexed_count += 1

            return reindexed_count

        return await run_in_threadpool(_exec)


class VectorReconciliationService:
    """
    Orchestrates vector indexing updates and stale cleanup.
    """

    def __init__(self, cleanup: Optional[StaleVectorCleanup] = None):
        self.cleanup = cleanup or StaleVectorCleanup()

    async def reconcile_document_vectors(self, document_id: str, is_deleted: bool = False) -> int:
        """Purges stale vector chunks before reindexing or on deletion."""
        return await self.cleanup.delete_document_vectors(document_id)
