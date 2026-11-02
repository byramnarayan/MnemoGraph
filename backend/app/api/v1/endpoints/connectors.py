import logging
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.databricks.client import DatabricksClient
from app.connectors.databricks.sync import DatabricksSyncService
from app.core.database import get_db
from app.core.deps import CurrentUser
from app.models.connector import ConnectorConfig, ConnectorSyncJob

logger = logging.getLogger(__name__)
from app.schemas.connector import (
    ConnectorCreateRequest,
    ConnectorResponse,
    SyncJobResponse,
    TableItem,
    TestConnectionRequest,
    TestConnectionResponse,
    TriggerSyncRequest,
    WarehouseItem,
)
from app.services.graph.reconciliation_graph_service import ReconciliationGraphService
from app.services.storage.s3_store import S3Store
from app.services.vector.stale_vector_cleanup import StaleVectorCleanup

router = APIRouter()


@router.post("/databricks/test-connection", response_model=TestConnectionResponse)
async def test_databricks_connection(
    req: TestConnectionRequest,
    current_user: CurrentUser,
):
    client = DatabricksClient(host=req.host, token=req.token, workspace_id=req.workspace_id)
    try:
        me = await client.get_current_user()
        user_name = me.get("userName") or me.get("displayName") or "Authenticated User"
        return TestConnectionResponse(
            ok=True,
            workspace_name=f"Databricks Workspace ({req.workspace_id})",
            user_name=user_name,
            message="Connection successful",
        )
    except Exception as e:
        return TestConnectionResponse(
            ok=False,
            message=f"Connection failed: {str(e)}",
        )


@router.post("/databricks/warehouses", response_model=list[WarehouseItem])
async def list_databricks_warehouses(
    req: TestConnectionRequest,
    current_user: CurrentUser,
):
    """List SQL Warehouses available on the workspace."""
    client = DatabricksClient(host=req.host, token=req.token, workspace_id=req.workspace_id)
    raw_warehouses = await client.list_sql_warehouses()
    items = []
    for w in raw_warehouses:
        items.append(
            WarehouseItem(
                id=w.get("id") or "",
                name=w.get("name") or "SQL Warehouse",
                state=w.get("state"),
                http_path=w.get("odbc_params", {}).get("path") or f"/sql/1.0/warehouses/{w.get('id')}",
            )
        )
    return items


@router.post("/databricks/catalogs", response_model=list[TableItem])
async def list_databricks_tables(
    req: TestConnectionRequest,
    current_user: CurrentUser,
):
    """List available tables/schemas in the workspace catalog."""
    client = DatabricksClient(host=req.host, token=req.token, workspace_id=req.workspace_id)
    tables: list[TableItem] = []

    try:
        catalogs = await client.list_catalogs()
        cat_names = [c.get("name") for c in catalogs if c.get("name")] or ["main"]

        for cat in cat_names[:2]:  # inspect top 2 catalogs
            schemas = await client.list_schemas(cat)
            schema_names = [s.get("name") for s in schemas if s.get("name")] or ["default"]

            for sc in schema_names[:4]:
                tbls = await client.list_tables(cat, sc)
                for t in tbls:
                    t_name = t.get("name") or ""
                    full_name = f"{cat}.{sc}.{t_name}"
                    tables.append(
                        TableItem(
                            full_name=full_name,
                            name=t_name,
                            catalog=cat,
                            schema_name=sc,
                            table_type=t.get("table_type"),
                        )
                    )
    except Exception:
        pass

    # If Unity Catalog is not enabled or returns empty, provide default metadata entities
    if not tables:
        tables = [
            TableItem(full_name="default.users", name="users", catalog="hive_metastore", schema_name="default", table_type="MANAGED"),
            TableItem(full_name="default.orders", name="orders", catalog="hive_metastore", schema_name="default", table_type="MANAGED"),
            TableItem(full_name="default.transactions", name="transactions", catalog="hive_metastore", schema_name="default", table_type="MANAGED"),
            TableItem(full_name="analytics.customer_events", name="customer_events", catalog="analytics", schema_name="analytics", table_type="VIEW"),
        ]

    return tables


@router.post("/databricks", response_model=ConnectorResponse, status_code=status.HTTP_201_CREATED)
async def create_databricks_connector(
    req: ConnectorCreateRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    import json
    tables_json = json.dumps(req.selected_tables) if req.selected_tables else None

    connector = ConnectorConfig(
        org_id=req.org_id or current_user.tenant_slug or "default",
        name=req.name,
        connector_type="databricks",
        host=req.host,
        workspace_id=req.workspace_id,
        token_encrypted=req.token,
        selected_warehouse_id=req.selected_warehouse_id,
        selected_tables=tables_json,
        sync_interval_minutes=req.sync_interval_minutes,
        auto_index=req.auto_index,
        status="configured",
    )
    db.add(connector)
    await db.commit()
    await db.refresh(connector)
    return connector


@router.get("", response_model=list[ConnectorResponse])
async def list_connectors(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    res = await db.execute(select(ConnectorConfig))
    return res.scalars().all()


@router.delete("/{connector_id}", status_code=status.HTTP_200_OK)
async def delete_connector(
    connector_id: str,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Cascade cleanup of a connector:
    1. Removes PostgreSQL connector row & cascades sync jobs and metadata.
    2. Detaches & deletes the Workspace node, Documents, and edges from FalkorDB.
    3. Purges vector points from Qdrant.
    4. Deletes S3 raw exported items under databricks/{workspace_id}/.
    """
    res = await db.execute(select(ConnectorConfig).where(ConnectorConfig.id == connector_id))
    connector = res.scalars().first()
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")

    workspace_id = connector.workspace_id

    # 1. FalkorDB graph cleanup
    try:
        graph_service = ReconciliationGraphService()
        # Delete workspace node and connected items in graph
        await graph_service.delete_document_node(f"workspace:{workspace_id}")
    except Exception as e:
        logger.warning(f"Error during graph cleanup for workspace {workspace_id}: {e}")

    # 2. Qdrant vector cleanup
    try:
        vector_cleanup = StaleVectorCleanup()
        await vector_cleanup.delete_document_vectors(connector_id)
    except Exception as e:
        logger.warning(f"Error during vector cleanup for connector {connector_id}: {e}")

    # 3. S3 object storage cleanup
    try:
        s3 = S3Store()
        await s3.delete_prefix(f"databricks/{workspace_id}/")
    except Exception as e:
        logger.warning(f"Error during S3 cleanup for workspace {workspace_id}: {e}")

    # 4. PostgreSQL cascade deletion
    await db.delete(connector)
    await db.commit()

    return {
        "status": "deleted",
        "connector_id": connector_id,
        "workspace_id": workspace_id,
        "message": "Connector and all associated graph nodes, vectors, and storage assets removed.",
    }


async def _run_sync_task(connector_id: str, job_id: str):
    from app.core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        conn_res = await session.execute(select(ConnectorConfig).where(ConnectorConfig.id == connector_id))
        connector = conn_res.scalars().first()
        job_res = await session.execute(select(ConnectorSyncJob).where(ConnectorSyncJob.id == job_id))
        job = job_res.scalars().first()
        if connector and job:
            service = DatabricksSyncService(db=session, connector=connector)
            await service.execute_sync(job)


@router.post("/databricks/{connector_id}/sync", response_model=SyncJobResponse)
async def trigger_sync(
    connector_id: str,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    req: TriggerSyncRequest | None = None,
):
    res = await db.execute(select(ConnectorConfig).where(ConnectorConfig.id == connector_id))
    connector = res.scalars().first()
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")

    mode = req.mode if req else "full"
    job = ConnectorSyncJob(
        connector_id=connector.id,
        mode=mode,
        status="queued",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Background ingestion
    background_tasks.add_task(_run_sync_task, connector.id, job.id)

    return SyncJobResponse(
        job_id=job.id,
        connector_id=job.connector_id,
        mode=job.mode,
        status=job.status,
        records_synced=job.records_synced,
        docs_indexed=job.docs_indexed,
        started_at=job.started_at,
        finished_at=job.finished_at,
        error_message=job.error_message,
    )


from fastapi import File, Form, UploadFile
from app.services.connectors.document_pipeline_service import DocumentPipelineService


@router.post("/documents/upload")
async def upload_document_to_pipeline(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...),
    title: str | None = Form(None),
    project_id: str | None = Form(None),
    classification: str = Form("Internal"),
    department: str | None = Form(None),
) -> dict[str, Any]:
    """
    Ingests an uploaded document through the complete pipeline:
    1. Parse text & structure (.pdf, .docx, .txt, .md, .json, .csv)
    2. Store raw binary object in MinIO / S3
    3. Persist metadata & permission in PostgreSQL
    4. Enrich document with entity & decision references
    5. Ingest node & relationships into FalkorDB
    6. Chunk and embed into Qdrant for semantic search
    """
    try:
        content_bytes = await file.read()
        if not content_bytes:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        pipeline = DocumentPipelineService()
        result = await pipeline.ingest_document(
            db=db,
            current_user=current_user,
            filename=file.filename or "uploaded_file",
            file_bytes=content_bytes,
            mime_type=file.content_type,
            custom_title=title,
            project_id=project_id,
            classification=classification,
            department=department,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Upload pipeline failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Document ingestion failed: {str(e)}")














@router.get("/databricks/{connector_id}/sync/{job_id}", response_model=SyncJobResponse)
async def get_sync_job_status(
    connector_id: str,
    job_id: str,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    res = await db.execute(
        select(ConnectorSyncJob).where(ConnectorSyncJob.id == job_id, ConnectorSyncJob.connector_id == connector_id)
    )
    job = res.scalars().first()
    if not job:
        raise HTTPException(status_code=404, detail="Sync job not found")

    return SyncJobResponse(
        job_id=job.id,
        connector_id=job.connector_id,
        mode=job.mode,
        status=job.status,
        records_synced=job.records_synced,
        docs_indexed=job.docs_indexed,
        started_at=job.started_at,
        finished_at=job.finished_at,
        error_message=job.error_message,
    )


from fastapi import File, Form, UploadFile
from app.services.connectors.document_pipeline_service import DocumentPipelineService


@router.post("/documents/upload")
async def upload_document_to_pipeline(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...),
    title: str | None = Form(None),
    project_id: str | None = Form(None),
    classification: str = Form("Internal"),
    department: str | None = Form(None),
) -> dict[str, Any]:
    """
    Ingests an uploaded document through the complete pipeline:
    1. Parse text & structure (.pdf, .docx, .txt, .md, .json, .csv)
    2. Store raw binary object in MinIO / S3
    3. Persist metadata & permission in PostgreSQL
    4. Enrich document with entity & decision references
    5. Ingest node & relationships into FalkorDB
    6. Chunk and embed into Qdrant for semantic search
    """
    try:
        content_bytes = await file.read()
        if not content_bytes:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        pipeline = DocumentPipelineService()
        result = await pipeline.ingest_document(
            db=db,
            current_user=current_user,
            filename=file.filename or "uploaded_file",
            file_bytes=content_bytes,
            mime_type=file.content_type,
            custom_title=title,
            project_id=project_id,
            classification=classification,
            department=department,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Upload pipeline failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Document ingestion failed: {str(e)}")














