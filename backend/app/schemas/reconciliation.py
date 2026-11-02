from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class ReconciliationRunRequest(BaseModel):
    mode: str = "incremental"  # "full" | "incremental"
    active_source_ids: Optional[List[str]] = None


class ReconciliationRunResponse(BaseModel):
    job_id: str
    status: str
    connector_id: str
    mode: str


class ReconciliationJobDetailResponse(BaseModel):
    id: str
    connector_id: str
    source_type: str
    mode: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    documents_checked: int
    documents_changed: int
    docs_deleted: int
    stale_edges_removed: int
    vector_entries_removed: int
    summary: Optional[str] = None
    errors: Optional[str] = None

    class Config:
        from_attributes = True

