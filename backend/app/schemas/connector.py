from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class TestConnectionRequest(BaseModel):
    host: str = Field(..., description="Databricks host URL (e.g. https://<workspace>.cloud.databricks.com)")
    token: str = Field(..., description="Personal Access Token (PAT) or OAuth token")
    workspace_id: str = Field(..., description="Workspace ID")


class TestConnectionResponse(BaseModel):
    ok: bool
    workspace_name: str | None = None
    user_name: str | None = None
    message: str


class ConnectorCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    host: str
    token: str
    workspace_id: str
    org_id: str | None = None
    selected_warehouse_id: str | None = None
    selected_tables: list[str] = Field(default_factory=list)
    sync_interval_minutes: int = 60
    auto_index: bool = True


class ConnectorResponse(BaseModel):
    id: str
    name: str
    connector_type: str
    host: str
    workspace_id: str
    selected_warehouse_id: str | None = None
    selected_tables: str | None = None
    status: str
    sync_interval_minutes: int
    auto_index: bool
    last_sync_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WarehouseItem(BaseModel):
    id: str
    name: str
    state: str | None = None
    http_path: str | None = None


class TableItem(BaseModel):
    full_name: str
    name: str
    catalog: str | None = None
    schema_name: str | None = None
    table_type: str | None = None


class TriggerSyncRequest(BaseModel):
    mode: str = Field("full", pattern="^(full|incremental)$")


class SyncJobResponse(BaseModel):
    job_id: str
    connector_id: str
    mode: str
    status: str
    records_synced: int = 0
    docs_indexed: int = 0
    started_at: datetime
    finished_at: datetime | None = None
    error_message: str | None = None

    model_config = ConfigDict(from_attributes=True)

