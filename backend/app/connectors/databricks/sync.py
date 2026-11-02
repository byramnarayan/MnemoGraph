from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.databricks.client import DatabricksClient
from app.connectors.databricks.mapper import DatabricksMapper
from app.connectors.databricks.models import InternalNotebook, InternalProject
from app.models.connector import (
    ConnectorConfig,
    ConnectorSyncJob,
    Department,
    Document,
    Person,
    Project,
    SourceEntity,
    Team,
)
from app.services.graph.repository import GraphRepository
from app.services.graph.schema import NodeLabel, RelationType
from app.services.storage.document_store import DocumentStore
from app.services.vector.indexer import VectorIndexer

logger = logging.getLogger(__name__)


class DatabricksSyncService:
    """Orchestrates end-to-end sync: Databricks -> Graph (FalkorDB) -> Storage (S3) -> Vector (Qdrant)."""

    def __init__(
        self,
        db: AsyncSession,
        connector: ConnectorConfig,
        graph_repo: GraphRepository | None = None,
        doc_store: DocumentStore | None = None,
        vector_indexer: VectorIndexer | None = None,
    ):
        self.db = db
        self.connector = connector
        self.client = DatabricksClient(
            host=connector.host,
            token=connector.token_encrypted,
            workspace_id=connector.workspace_id,
        )
        self.graph = graph_repo or GraphRepository()
        self.doc_store = doc_store or DocumentStore()
        self.vector_indexer = vector_indexer or VectorIndexer()

    async def execute_sync(self, sync_job: ConnectorSyncJob) -> None:
        try:
            sync_job.status = "running"
            await self.db.commit()

            records_count = 0
            docs_count = 0

            # 1. Upsert Workspace / SourceSystem root node in Graph
            ws_id = f"workspace:{self.connector.workspace_id}"
            await self.graph.upsert_node(
                label=NodeLabel.WORKSPACE,
                entity_id=ws_id,
                properties={
                    "workspace_id": self.connector.workspace_id,
                    "host": self.connector.host,
                    "name": self.connector.name,
                },
            )

            # 2. Sync Users & People
            raw_users = await self.client.list_users()
            user_id_map: dict[str, str] = {}
            for ru in raw_users:
                u = DatabricksMapper.map_user(ru)
                person_node_id = f"person:{u.email}"
                user_id_map[u.source_id] = person_node_id
                user_id_map[u.email] = person_node_id

                # Graph
                await self.graph.upsert_node(
                    label=NodeLabel.PERSON,
                    entity_id=person_node_id,
                    properties={
                        "email": u.email,
                        "display_name": u.display_name,
                        "role": u.role,
                        "active": u.active,
                    },
                )
                await self.graph.upsert_edge(
                    from_id=person_node_id,
                    to_id=ws_id,
                    relation=RelationType.BELONGS_TO,
                )

                # PostgreSQL
                p_res = await self.db.execute(select(Person).where(Person.email == u.email))
                person_row = p_res.scalars().first()
                if not person_row:
                    person_row = Person(
                        full_name=u.display_name,
                        email=u.email,
                        role=u.role,
                    )
                    self.db.add(person_row)
                else:
                    person_row.full_name = u.display_name
                    person_row.role = u.role

                records_count += 1

            # 3. Sync Groups & Teams
            raw_groups = await self.client.list_groups()
            team_id_map: dict[str, str] = {}
            for rg in raw_groups:
                t = DatabricksMapper.map_group(rg)
                team_slug = t.name.lower().replace(" ", "-")
                team_node_id = f"team:{team_slug}"
                team_id_map[t.name] = team_node_id

                # Graph
                await self.graph.upsert_node(
                    label=NodeLabel.TEAM,
                    entity_id=team_node_id,
                    properties={"name": t.name},
                )
                await self.graph.upsert_edge(
                    from_id=team_node_id,
                    to_id=ws_id,
                    relation=RelationType.BELONGS_TO,
                )

                # PostgreSQL
                t_res = await self.db.execute(select(Team).where(Team.name == t.name))
                team_row = t_res.scalars().first()
                if not team_row:
                    team_row = Team(name=t.name)
                    self.db.add(team_row)

                # Membership edges (person -> team)
                for m_id in t.member_source_ids:
                    member_person_node = user_id_map.get(m_id)
                    if member_person_node:
                        await self.graph.upsert_edge(
                            from_id=member_person_node,
                            to_id=team_node_id,
                            relation=RelationType.MEMBER_OF,
                        )
                records_count += 1

            # 4. Sync Workspace Items (Projects, Folders, Notebooks, Files)
            raw_items = await self.client.list_workspace_items("/")
            for item in raw_items:
                mapped = DatabricksMapper.map_workspace_item(item, self.connector.workspace_id)
                if not mapped:
                    continue

                path = item.get("path", "")

                # Handle Project/Initiative folder
                if isinstance(mapped, InternalProject):
                    proj_slug = mapped.name.lower().replace(" ", "-")
                    proj_node_id = f"project:{proj_slug}"
                    await self.graph.upsert_node(
                        label=NodeLabel.PROJECT,
                        entity_id=proj_node_id,
                        properties={"name": mapped.name, "workspace_id": self.connector.workspace_id},
                    )
                    await self.graph.upsert_edge(
                        from_id=proj_node_id,
                        to_id=ws_id,
                        relation=RelationType.BELONGS_TO,
                    )
                    # PostgreSQL
                    pr_res = await self.db.execute(select(Project).where(Project.name == mapped.name))
                    if not pr_res.scalars().first():
                        self.db.add(Project(name=mapped.name, workspace_id=self.connector.workspace_id))
                    records_count += 1
                    continue

                # Handle Document (Notebook / File)
                doc_node_id = f"doc:{mapped.source_id}"

                # Export text if notebook
                content = ""
                if item.get("object_type") == "NOTEBOOK":
                    try:
                        content = await self.client.export_notebook(path)
                    except Exception as e:
                        logger.debug(f"Export notebook error for {path}: {e}")

                clean_path = path.strip("/").replace("/", "_")
                storage_key = f"databricks/{self.connector.workspace_id}/{clean_path}.py"

                # Save or update SourceEntity in Postgres
                se_res = await self.db.execute(
                    select(SourceEntity).where(
                        SourceEntity.connector_id == self.connector.id,
                        SourceEntity.source_id == mapped.source_id,
                    )
                )
                source_entity = se_res.scalars().first()
                if not source_entity:
                    source_entity = SourceEntity(
                        connector_id=self.connector.id,
                        source_type=item.get("object_type", "NOTEBOOK").lower(),
                        source_id=mapped.source_id,
                        source_url=f"{self.connector.host}#notebook/{mapped.source_id}",
                        workspace_id=self.connector.workspace_id,
                        title=mapped.title,
                    )
                    self.db.add(source_entity)
                    await self.db.flush()
                else:
                    source_entity.title = mapped.title
                    source_entity.updated_at = datetime.now(UTC)

                # Persist Document row in Postgres
                d_res = await self.db.execute(
                    select(Document).where(Document.source_id == mapped.source_id)
                )
                doc_row = d_res.scalars().first()
                if not doc_row:
                    doc_row = Document(
                        title=mapped.title,
                        source_system="databricks",
                        source_id=mapped.source_id,
                        storage_key=storage_key,
                        mime_type="text/x-python",
                    )
                    self.db.add(doc_row)

                # Storage + Checksum Versioning
                is_changed = True
                if content:
                    doc_meta, is_changed = await self.doc_store.save_document(
                        db=self.db,
                        source_entity_id=source_entity.id,
                        storage_key=storage_key,
                        content=content.encode("utf-8"),
                        mime_type="text/x-python",
                        source_url=source_entity.source_url,
                    )

                # FalkorDB Graph Node
                label = NodeLabel.NOTEBOOK if item.get("object_type") == "NOTEBOOK" else NodeLabel.FILE
                await self.graph.upsert_node(
                    label=label,
                    entity_id=doc_node_id,
                    properties={
                        "title": mapped.title,
                        "path": path,
                        "storage_key": storage_key,
                        "workspace_id": self.connector.workspace_id,
                    },
                )
                await self.graph.upsert_edge(
                    from_id=doc_node_id,
                    to_id=ws_id,
                    relation=RelationType.CONTAINS,
                )

                # Connect Ownership (person -> doc)
                if mapped.owner_email:
                    person_node = user_id_map.get(mapped.owner_email)
                    if person_node:
                        await self.graph.upsert_edge(
                            from_id=person_node,
                            to_id=doc_node_id,
                            relation=RelationType.OWNS,
                        )

                # Connect Project (project -> doc)
                if mapped.project_id:
                    proj_node = f"project:{mapped.project_id.lower().replace(' ', '-')}"
                    await self.graph.upsert_edge(
                        from_id=proj_node,
                        to_id=doc_node_id,
                        relation=RelationType.CONTAINS,
                    )

                # Qdrant Vector Indexing
                if is_changed and content and self.connector.auto_index:
                    try:
                        await self.vector_indexer.index_document(
                            document_id=doc_node_id,
                            text=content,
                            metadata={
                                "source_system": "databricks",
                                "connector_id": self.connector.id,
                                "workspace_id": self.connector.workspace_id,
                                "title": mapped.title,
                                "path": path,
                                "storage_key": storage_key,
                                "source_type": item.get("object_type", "NOTEBOOK"),
                                "owner_email": mapped.owner_email,
                            },
                        )
                        docs_count += 1
                    except Exception as ve:
                        logger.warning(f"Vector indexing warning for {doc_node_id}: {ve}")

                records_count += 1

            # Complete sync job
            sync_job.status = "completed"
            sync_job.records_synced = records_count
            sync_job.docs_indexed = docs_count
            sync_job.finished_at = datetime.now(UTC)
            self.connector.status = "active"
            await self.db.commit()
            logger.info(f"Sync complete: {records_count} records, {docs_count} docs indexed")

        except Exception as e:
            logger.error(f"Sync failed: {e}", exc_info=True)
            sync_job.status = "failed"
            sync_job.error_message = str(e)
            sync_job.finished_at = datetime.now(UTC)
            self.connector.status = "error"
            await self.db.commit()
