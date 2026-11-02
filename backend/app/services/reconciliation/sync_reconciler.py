from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.connector import Document
from app.models.sync_reconciliation_job import DocumentVersionState, SyncReconciliationJob
from app.services.enrichment.enrichment_service import EnrichmentService
from app.services.reconciliation.change_detector import ChangeDetector
from app.services.reconciliation.orphan_cleanup import OrphanCleanup
from app.services.reconciliation.reindex_queue import ReindexQueue
from app.services.reconciliation.stale_edge_cleaner import StaleEdgeCleaner
from app.services.reconciliation.version_reconciler import VersionReconciler
from app.services.storage.document_store import DocumentStore
from app.services.vector.indexer import VectorIndexer
from app.services.vector.stale_vector_cleanup import StaleVectorCleanup

logger = logging.getLogger(__name__)


class SyncReconciler:
    """
    Enterprise sync reconciliation engine:
    1. Detects changed, moved, or deleted documents.
    2. Purges stale graph edges and outdated vector points.
    3. Triggers targeted re-indexing only for modified documents.
    4. Records job execution and metrics in sync_reconciliation_jobs.
    """

    def __init__(
        self,
        change_detector: Optional[ChangeDetector] = None,
        stale_edge_cleaner: Optional[StaleEdgeCleaner] = None,
        version_reconciler: Optional[VersionReconciler] = None,
        orphan_cleanup: Optional[OrphanCleanup] = None,
        vector_cleanup: Optional[StaleVectorCleanup] = None,
        doc_store: Optional[DocumentStore] = None,
        enrichment_service: Optional[EnrichmentService] = None,
        indexer: Optional[VectorIndexer] = None,
    ):
        self.detector = change_detector or ChangeDetector()
        self.stale_edge_cleaner = stale_edge_cleaner or StaleEdgeCleaner()
        self.version_reconciler = version_reconciler or VersionReconciler(self.detector)
        self.orphan_cleanup = orphan_cleanup or OrphanCleanup()
        self.vector_cleanup = vector_cleanup or StaleVectorCleanup()
        self.doc_store = doc_store or DocumentStore()
        self.enrichment_service = enrichment_service or EnrichmentService()
        self.indexer = indexer or VectorIndexer()
        self.reindex_queue = ReindexQueue()

    async def run_reconciliation(
        self,
        connector_id: str,
        db: AsyncSession,
        mode: str = "incremental",
        active_source_ids: Optional[List[str]] = None,
    ) -> SyncReconciliationJob:
        """
        Executes a reconciliation job across documents for a given connector/workspace.
        """
        job = SyncReconciliationJob(
            connector_id=connector_id,
            source_type="databricks",
            mode=mode,
            status="running",
            started_at=datetime.now(UTC),
        )
        db.add(job)
        await db.commit()

        try:
            # Query all documents for this connector or active workspace
            stmt = select(Document)
            res = await db.execute(stmt)
            documents = res.scalars().all()

            checked_count = 0
            changed_count = 0
            deleted_count = 0
            total_edges_removed = 0
            total_vectors_removed = 0

            # Set of source IDs reported by active source system
            source_id_set = set(active_source_ids) if active_source_ids is not None else None

            for doc in documents:
                checked_count += 1

                # Check if deleted at source
                if source_id_set is not None and doc.source_id not in source_id_set:
                    purge_res = await self.orphan_cleanup.mark_deleted_and_purge(doc.id, db)
                    deleted_count += 1
                    total_edges_removed += purge_res["edges_removed"]
                    total_vectors_removed += purge_res["vectors_removed"]
                    continue

                # Fetch raw content bytes from storage
                content_bytes = b""
                if doc.storage_key:
                    content_bytes = await self.doc_store.get_document_bytes(doc.storage_key) or b""

                # Get version state
                vstate = await self.version_reconciler.get_or_create_state(
                    document_id=doc.id,
                    source_id=doc.source_id,
                    db=db,
                )

                change_res = self.detector.detect_change(
                    current_content=content_bytes,
                    stored_hash=vstate.version_hash if vstate.version_hash else None,
                    path=doc.storage_key,
                )

                if change_res.has_changed or mode == "full":
                    changed_count += 1
                    # 1. Purge stale vectors from Qdrant
                    vecs_purged = await self.vector_cleanup.delete_document_vectors(doc.id)
                    total_vectors_removed += vecs_purged

                    # 2. Clean stale edges in FalkorDB
                    edges_cleaned = await self.stale_edge_cleaner.clean_edges_for_document(doc.id)
                    total_edges_removed += edges_cleaned

                    # 3. Re-index into Qdrant if content exists
                    text_content = content_bytes.decode("utf-8", errors="replace") if content_bytes else doc.title
                    if text_content:
                        await self.indexer.index_document(
                            document_id=doc.id,
                            text=text_content,
                            metadata={
                                "title": doc.title,
                                "project_id": doc.project_id,
                                "team_id": doc.team_id,
                                "owner_id": doc.owner_user_id,
                            },
                        )

                    # 4. Re-enrich sections, entities, and mentions
                    await self.enrichment_service.enrich_document(
                        document_id=doc.id,
                        db=db,
                        raw_text=text_content,
                        force_reparse=True,
                    )

                    # 5. Update version hash
                    await self.version_reconciler.update_version(
                        state=vstate,
                        new_hash=change_res.current_hash,
                        db=db,
                    )

            job.status = "completed"
            job.completed_at = datetime.now(UTC)
            job.documents_checked = checked_count
            job.documents_changed = changed_count
            job.docs_deleted = deleted_count
            job.stale_edges_removed = total_edges_removed
            job.vector_entries_removed = total_vectors_removed
            job.summary = (
                f"Reconciled {checked_count} documents. Changed: {changed_count}, "
                f"Deleted: {deleted_count}, Edges removed: {total_edges_removed}, "
                f"Vectors purged: {total_vectors_removed}."
            )
            await db.commit()

        except Exception as e:
            logger.error(f"Reconciliation job failed: {e}", exc_info=True)
            job.status = "failed"
            job.completed_at = datetime.now(UTC)
            job.errors = str(e)
            await db.commit()

        return job
