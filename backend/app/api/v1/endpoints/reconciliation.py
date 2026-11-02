from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, get_db
from app.core.deps import CurrentUser
from app.models.sync_reconciliation_job import SyncReconciliationJob
from app.schemas.reconciliation import (
    ReconciliationJobDetailResponse,
    ReconciliationRunRequest,
    ReconciliationRunResponse,
)
from app.services.reconciliation.sync_reconciler import SyncReconciler

router = APIRouter(tags=["Sync Reconciliation"])


async def _run_reconciliation_task(
    connector_id: str,
    mode: str,
    active_source_ids: list[str] | None,
):
    async with AsyncSessionLocal() as db:
        reconciler = SyncReconciler()
        await reconciler.run_reconciliation(
            connector_id=connector_id,
            db=db,
            mode=mode,
            active_source_ids=active_source_ids,
        )


# 1. POST /api/v1/reconciliation/{connector_id}/run
@router.post("/reconciliation/{connector_id}/run", response_model=ReconciliationRunResponse)
async def trigger_reconciliation(
    connector_id: str,
    payload: ReconciliationRunRequest,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger full or incremental reconciliation of documents, stale graph edges,
    and out-of-sync vector records.
    """
    job = SyncReconciliationJob(
        connector_id=connector_id,
        source_type="databricks",
        mode=payload.mode,
        status="queued",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    background_tasks.add_task(
        _run_reconciliation_task,
        connector_id=connector_id,
        mode=payload.mode,
        active_source_ids=payload.active_source_ids,
    )

    return ReconciliationRunResponse(
        job_id=job.id,
        status="queued",
        connector_id=connector_id,
        mode=payload.mode,
    )


# 2. GET /api/v1/reconciliation/jobs/{job_id}
@router.get("/reconciliation/jobs/{job_id}", response_model=ReconciliationJobDetailResponse)
async def get_reconciliation_job(
    job_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Fetch status and outcome metrics of a reconciliation job."""
    stmt = select(SyncReconciliationJob).where(SyncReconciliationJob.id == job_id)
    res = await db.execute(stmt)
    job = res.scalar_one_or_none()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reconciliation job {job_id} not found",
        )
    return job

