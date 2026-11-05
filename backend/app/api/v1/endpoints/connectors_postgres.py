import logging
from typing import Annotated, Any
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, AsyncSessionLocal
from app.core.deps import CurrentUser
from app.core.crypto import encrypt_secret, decrypt_secret
from app.models.connector import ConnectorConfig, ConnectorSyncJob
from app.models.postgres_connector import PostgresTableConfig
from app.connectors.postgres.client import PostgresClient
from app.connectors.postgres.schema_discovery import PostgresSchemaDiscovery
from app.connectors.postgres.sync import PostgresSyncService
from app.schemas.postgres_connector import (
    PostgresConnectionTestRequest,
    PostgresConnectionTestResponse,
    PostgresDiscoveredSchemaResponse,
    PostgresDiscoveredTable,
    PostgresDiscoveredColumn,
    PostgresConnectorCreateRequest,
    PostgresTableConfigDTO,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/postgres", tags=["postgres-connector"])


@router.post("/test-connection", response_model=PostgresConnectionTestResponse)
async def test_postgres_connection(
    req: PostgresConnectionTestRequest,
    current_user: CurrentUser,
) -> PostgresConnectionTestResponse:
    """Test read-only connectivity to an external PostgreSQL database."""
    client = PostgresClient(
        host=req.host,
        port=req.port,
        database=req.database,
        username=req.username,
        password=req.password,
        ssl_mode=req.ssl_mode,
    )
    result = await client.test_connection()
    return PostgresConnectionTestResponse(
        ok=result.get("ok", False),
        success=result.get("ok", False),
        server_version=result.get("server_version"),
        database_name=result.get("database_name"),
        connected_user=result.get("connected_user"),
        message=result.get("message"),
        error=result.get("message") if not result.get("ok") else None,
    )


@router.post("/discover-schemas", response_model=PostgresDiscoveredSchemaResponse)
async def discover_postgres_schemas(
    req: PostgresConnectionTestRequest,
    current_user: CurrentUser,
) -> PostgresDiscoveredSchemaResponse:
    """Discovers schemas, tables, columns, PKs, cursor candidates, and suggests ontology classes."""
    client = PostgresClient(
        host=req.host,
        port=req.port,
        database=req.database,
        username=req.username,
        password=req.password,
        ssl_mode=req.ssl_mode,
    )
    discovery = PostgresSchemaDiscovery(client)
    try:
        tables_data = await discovery.discover_schemas_and_tables()
        tables = [
            PostgresDiscoveredTable(
                schema_name=t["schema_name"],
                table_name=t["table_name"],
                primary_keys=t.get("primary_keys", []),
                suggested_cursor_col=t.get("suggested_cursor_col") or t.get("suggested_cursor"),
                suggested_entity_type=t.get("suggested_entity_type", "Document"),
                columns=[PostgresDiscoveredColumn(**c) for c in t.get("columns", [])],
            )
            for t in tables_data
        ]
        return PostgresDiscoveredSchemaResponse(tables=tables)
    except Exception as exc:
        logger.error("Schema discovery failed: %s", exc)
        raise HTTPException(status_code=400, detail=f"Failed to discover schemas: {str(exc)}")


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_postgres_connector(
    req: PostgresConnectorCreateRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    """Saves connector configuration with encrypted credentials and table mappings."""
    enc_password = encrypt_secret(req.password)
    connector = ConnectorConfig(
        name=req.name,
        connector_type="postgresql",
        auth_type="basic",
        host=req.host,
        port=req.port,
        database_name=req.database,
        username=req.username,
        encrypted_password=enc_password,
        ssl_mode=req.ssl_mode,
        is_active=True,
        workspace_id=req.database,
        token_encrypted=enc_password,
    )
    db.add(connector)
    await db.flush()

    for tbl in req.tables:
        cfg = PostgresTableConfig(
            connector_id=connector.id,
            schema_name=tbl.schema_name,
            table_name=tbl.table_name,
            primary_key_columns=tbl.primary_key_columns,
            cursor_column=tbl.cursor_column,
            included_columns=tbl.included_columns,
            excluded_columns=tbl.excluded_columns,
            text_columns=tbl.text_columns,
            entity_type=tbl.entity_type,
            visibility_policy=tbl.visibility_policy,
            enabled=tbl.enabled,
        )
        db.add(cfg)

    await db.commit()
    await db.refresh(connector)
    return {"id": connector.id, "name": connector.name, "connector_type": connector.connector_type}


@router.get("/{connector_id}/tables", response_model=list[PostgresTableConfigDTO])
async def list_postgres_tables(
    connector_id: str,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[PostgresTableConfigDTO]:
    """Retrieves saved table configurations for a connector."""
    stmt = select(PostgresTableConfig).where(PostgresTableConfig.connector_id == connector_id)
    res = await db.execute(stmt)
    records = res.scalars().all()
    return [
        PostgresTableConfigDTO(
            id=r.id,
            schema_name=r.schema_name,
            table_name=r.table_name,
            primary_key_columns=r.primary_key_columns,
            cursor_column=r.cursor_column,
            included_columns=r.included_columns,
            excluded_columns=r.excluded_columns,
            text_columns=r.text_columns,
            entity_type=r.entity_type,
            visibility_policy=r.visibility_policy,
            enabled=r.enabled,
            last_cursor_value=r.last_cursor_value,
        )
        for r in records
    ]


async def _run_postgres_sync_background(connector_id: str, job_id: str) -> None:
    async with AsyncSessionLocal() as session:
        sync_svc = PostgresSyncService(db=session)
        try:
            await sync_svc.sync_connector(connector_id=connector_id, job_id=job_id)
        except Exception as e:
            logger.error("Background sync failed for connector %s: %s", connector_id, e)


@router.post("/{connector_id}/sync")
async def trigger_postgres_sync(
    connector_id: str,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    """Trigger incremental or initial sync for a PostgreSQL source connector."""
    stmt = select(ConnectorConfig).where(ConnectorConfig.id == connector_id)
    res = await db.execute(stmt)
    connector = res.scalar_one_or_none()
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")

    job = ConnectorSyncJob(connector_id=connector.id, status="PENDING")
    db.add(job)
    await db.commit()
    await db.refresh(job)

    background_tasks.add_task(_run_postgres_sync_background, connector.id, job.id)
    return {"job_id": job.id, "status": job.status, "message": "PostgreSQL sync job started"}

