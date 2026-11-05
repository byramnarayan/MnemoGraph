from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser
from app.schemas.incident_interconnect import (
    IncidentInterconnectResponse,
    IncidentSummaryItem,
    Layer8SimilarIncidents,
)
from app.services.graph.incident_interconnect_service import IncidentInterconnectService

logger = logging.getLogger(__name__)

router = APIRouter()
incident_service = IncidentInterconnectService()


@router.get("", response_model=list[IncidentSummaryItem])
async def list_incidents(
    current_user: CurrentUser,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
):
    """
    UKGOE Phase 10: Lists incidents across the organization
    ordered by view count and last view timestamp for quick navigation.
    """
    try:
        return await incident_service.list_recent_incidents(limit=limit)
    except Exception as e:
        logger.error(f"Error listing incidents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list incidents: {str(e)}",
        )


@router.get("/{incident_id}/interconnect", response_model=IncidentInterconnectResponse)
async def get_incident_interconnect_view(
    incident_id: str,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    UKGOE Phase 10: Returns the access-controlled, 9-layer interconnected subgraph
    (Layers 0 through 8) for the selected Incident node.
    Enforces INCIDENT_VIEW_ACCESS_POLICY (Levels 1, 2, or 3) and records non-destructive
    view metrics and Graphiti :EpisodeMemory.
    """
    try:
        # 1. Evaluate Dynamic Access Policy
        access_level, desc = await incident_service.evaluate_incident_view_policy(current_user, incident_id)

        # 2. Build Multi-Layer Interconnected View
        view = await incident_service.build_incident_interconnect_view(
            incident_id=incident_id,
            user=current_user,
            access_level=access_level,
        )

        # 3. Non-destructive Episodic Memory & View Count Update
        await incident_service.record_view_access(
            incident_id=incident_id,
            user=current_user,
            view_response=view,
            db=db,
        )

        return view
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        logger.error(f"Error building incident interconnect view for {incident_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to build incident interconnect view: {str(e)}",
        )


@router.get("/{incident_id}/similar", response_model=Layer8SimilarIncidents)
async def get_similar_incidents(
    incident_id: str,
    current_user: CurrentUser,
):
    """
    UKGOE Phase 10: Standalone Layer 8 Qdrant Vector Intelligence endpoint
    surfacing similar historical incidents and preventative tasks.
    """
    try:
        access_level, _ = await incident_service.evaluate_incident_view_policy(current_user, incident_id)
        if access_level > 1:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Vector-similar incidents require Level 1 (Manager/Admin) authorization.",
            )

        view = await incident_service.build_incident_interconnect_view(
            incident_id=incident_id,
            user=current_user,
            access_level=1,
        )
        return view.layer8_similar_incidents or Layer8SimilarIncidents()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving similar incidents for {incident_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query similar incidents: {str(e)}",
        )

