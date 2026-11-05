from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.connector import ConnectorConfig, ConnectorSyncJob
from app.models.postgres_connector import PostgresTableConfig
from app.connectors.postgres.client import PostgresClient
from app.connectors.postgres.mapper import OntologyEntityMapper
from app.services.ledger.relational_ledger_service import RelationalLedgerService
from app.services.graph.repository import GraphRepository
from app.services.storage.s3_store import S3ObjectStore
from app.services.vector.indexer import VectorIndexer
from app.core.crypto import decrypt_secret

logger = logging.getLogger(__name__)


class PostgresSyncService:
    """
    Orchestrates ingestion of selected tables into the UKGOE ontology,
    PostgreSQL ledger, FalkorDB Knowledge Graph, S3, and Qdrant.
    """

    def __init__(
        self,
        db: AsyncSession,
        ledger: RelationalLedgerService | None = None,
        graph_repo: GraphRepository | None = None,
        s3_store: S3ObjectStore | None = None,
        vector_indexer: VectorIndexer | None = None,
    ) -> None:
        self.db = db
        self.ledger = ledger or RelationalLedgerService()
        self.graph_repo = graph_repo or GraphRepository()
        self.s3_store = s3_store or S3ObjectStore()
        self.vector_indexer = vector_indexer or VectorIndexer()

    async def sync_connector(self, connector_id: str, job_id: str) -> dict[str, Any]:
        """Runs synchronization across all enabled tables for a connector."""
        connector_stmt = select(ConnectorConfig).where(ConnectorConfig.id == connector_id)
        res = await self.db.execute(connector_stmt)
        connector = res.scalar_one_or_none()
        if not connector:
            raise ValueError(f"Connector {connector_id} not found.")

        job_stmt = select(ConnectorSyncJob).where(ConnectorSyncJob.id == job_id)
        res_job = await self.db.execute(job_stmt)
        job = res_job.scalar_one_or_none()
        if job:
            job.status = "RUNNING"
            job.started_at = datetime.now(UTC)
            await self.db.commit()

        tables_stmt = (
            select(PostgresTableConfig)
            .where(PostgresTableConfig.connector_id == connector_id, PostgresTableConfig.enabled.is_(True))
        )
        res_tables = await self.db.execute(tables_stmt)
        tables = list(res_tables.scalars().all())

        raw_pwd = connector.encrypted_password or ""
        password = decrypt_secret(raw_pwd) if raw_pwd else ""
        client = PostgresClient(
            host=connector.host or "localhost",
            port=connector.port or 5432,
            database=connector.database_name or "postgres",
            username=connector.username or "postgres",
            password=password,
            ssl_mode=connector.ssl_mode or "prefer",
        )

        total_ingested = 0
        total_failed = 0
        error_details: list[str] = []

        try:
            for table_cfg in tables:
                table_ingested, table_failed, max_cursor = await self._sync_table(client, connector, table_cfg)
                total_ingested += table_ingested
                total_failed += table_failed
                if max_cursor:
                    table_cfg.last_cursor_value = str(max_cursor)
                    table_cfg.last_successful_sync_at = datetime.now(UTC)
                    await self.db.commit()

            if job:
                job.status = "COMPLETED" if total_failed == 0 else "PARTIAL"
                job.completed_at = datetime.now(UTC)
                job.records_ingested = total_ingested
                job.records_failed = total_failed
                await self.db.commit()

        except Exception as exc:
            logger.exception("Sync job failed for connector %s: %s", connector_id, exc)
            if job:
                job.status = "FAILED"
                job.completed_at = datetime.now(UTC)
                job.error_message = str(exc)
                await self.db.commit()
            raise

        return {"total_ingested": total_ingested, "total_failed": total_failed, "errors": error_details}

    async def _sync_table(
        self, client: PostgresClient, connector: ConnectorConfig, table_cfg: PostgresTableConfig
    ) -> tuple[int, int, Any]:
        """Pulls and ingests rows for a specific table configuration."""
        ingested = 0
        failed = 0
        max_cursor = None

        async for batch in client.fetch_rows_batched(
            schema=table_cfg.schema_name,
            table=table_cfg.table_name,
            columns=table_cfg.included_columns or None,
            cursor_col=table_cfg.cursor_column,
            cursor_val=table_cfg.last_cursor_value,
            batch_size=500,
        ):
            for row in batch:
                try:
                    await self._ingest_row(connector, table_cfg, row)
                    ingested += 1
                    if table_cfg.cursor_column and table_cfg.cursor_column in row:
                        val = row[table_cfg.cursor_column]
                        if val is not None:
                            max_cursor = val
                except Exception as row_exc:
                    logger.warning("Failed to ingest row in %s.%s: %s", table_cfg.schema_name, table_cfg.table_name, row_exc)
                    failed += 1

        return ingested, failed, max_cursor

    async def _ingest_row(
        self, connector: ConnectorConfig, table_cfg: PostgresTableConfig, row: dict[str, Any]
    ) -> None:
        """Transforms a row into a Universal Entity and persists across PostgreSQL, FalkorDB, S3, Qdrant."""
        entity = OntologyEntityMapper.map_row_to_entity(
            row=row,
            connector_id=connector.id,
            schema_name=table_cfg.schema_name,
            table_name=table_cfg.table_name,
            entity_type=table_cfg.entity_type,
            primary_key_cols=table_cfg.primary_key_columns,
            text_cols=table_cfg.text_columns,
        )

        entity_id = entity["entity_id"]
        entity_class = entity["entity_class"]
        label = entity["label"]
        props = entity["properties"]

        # 1. Canonical PostgreSQL Ledger
        await self.ledger.upsert_entity_atomic(
            session=self.db,
            entity_id=entity_id,
            entity_class=entity_class,
            label=label,
            properties={"source_system": f"postgres:{table_cfg.schema_name}.{table_cfg.table_name}", **props},
            source_document_id=f"postgres:{table_cfg.schema_name}.{table_cfg.table_name}",
        )

        # 2. FalkorDB Knowledge Graph
        try:
            await self.graph_repo.upsert_node(
                label=entity_class,
                entity_id=entity_id,
                properties={"name": label, "source": "postgres", **props},
            )
            # Link to generic external system node
            sys_id = f"system:postgres_{connector.database_name}"
            await self.graph_repo.upsert_node("System", sys_id, {"name": f"PostgreSQL {connector.database_name}"})
            await self.graph_repo.upsert_edge(entity_id, sys_id, "PART_OF_SYSTEM", {"synced_at": datetime.now(UTC).isoformat()})
        except Exception as g_exc:
            logger.warning("FalkorDB graph sync non-fatal error for %s: %s", entity_id, g_exc)

        # 3. Object Storage & Qdrant Search Indexing
        search_text = entity.get("searchable_text")
        if search_text:
            doc_id = f"doc_{entity_id}"
            try:
                storage_key = f"connectors/postgres/{connector.id}/{table_cfg.schema_name}_{table_cfg.table_name}/{doc_id}.txt"
                await self.s3_store.put_object(
                    key=storage_key,
                    data=search_text.encode("utf-8"),
                    content_type="text/plain",
                )
                await self.vector_indexer.index_document(
                    document_id=doc_id,
                    text=search_text,
                    doc_title=label,
                    metadata={"entity_id": entity_id, "entity_class": entity_class, "source": "postgres"},
                )
            except Exception as s_exc:
                logger.warning("Search indexing non-fatal error for %s: %s", entity_id, s_exc)
