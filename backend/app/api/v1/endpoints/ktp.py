from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.deps import CurrentUser
from app.schemas.ktp import (
    AssignHandoverRequest,
    AssignHandoverResponse,
    KTPCandidateResponse,
    KnowledgeTransferPackageResponse,
    KtpPersonSummary,
)
from app.services.graph.ktp_service import KTPService

logger = logging.getLogger(__name__)

router = APIRouter()
ktp_service = KTPService()


@router.get("/candidates", response_model=list[KTPCandidateResponse])
async def list_ktp_candidates(
    current_user: CurrentUser,
):
    """
    UKGOE Phase 9: List personnel who are departing, inactive, on leave,
    or eligible for Knowledge Transfer Package generation.
    """
    try:
        return await ktp_service.list_candidates()
    except Exception as e:
        logger.error(f"Error listing KTP candidates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list KTP candidates: {str(e)}",
        )


@router.post("/generate/{person_id}", response_model=KnowledgeTransferPackageResponse)
async def generate_ktp_package(
    person_id: str,
    current_user: CurrentUser,
):
    """
    UKGOE Phase 9: Generates, persists, and returns a Knowledge Transfer Package
    for a departing or inactive individual.
    Enforces KTP_ACCESS_POLICY (2-hop manager, senior peer, or admin).
    """
    # 1. Enforce Access Policy Gate
    allowed, reason, effective_role = await ktp_service.evaluate_ktp_access(current_user, person_id)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=reason,
        )

    # 2. Extract Subgraph and Build Handover Package
    try:
        user_clearance = getattr(current_user, "clearance_level", "Internal") or "Internal"
        ktp_data = await ktp_service.build_ktp_package(
            target_person_id=person_id,
            requestor_id=str(current_user.id),
            requestor_role=effective_role,
            user_clearance=user_clearance,
        )

        # 3. Persist as first-class :Document node in FalkorDB
        await ktp_service.persist_ktp_document(ktp_data)

        return ktp_data
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        logger.error(f"Failed to generate KTP for {person_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate KTP: {str(e)}",
        )


@router.get("/people", response_model=list[KtpPersonSummary])
async def list_personnel(
    current_user: CurrentUser,
    status_filter: str | None = Query(None, alias="status"),
):
    """
    KTP Hub: Lists personnel with successor-gated access control.
    - Admins see full institutional directory.
    - Managers see their direct & indirect reports + handed-over personnel + self.
    - Regular employees strictly see themselves and personnel handed over to them.
    """
    try:
        return await ktp_service.list_all_personnel(user=current_user, status_filter=status_filter)
    except Exception as e:
        logger.error(f"Error listing personnel for KTP hub: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list personnel: {str(e)}",
        )


@router.get("/people/{person_id}", response_model=KnowledgeTransferPackageResponse)
async def get_person_ktp_package(
    person_id: str,
    current_user: CurrentUser,
):
    """
    KTP Hub: Retrieves the full interconnected institutional subgraph for a person.
    Evaluates KTP_ACCESS_POLICY (admin, 2-hop manager, senior peer, or assigned successor).
    """
    allowed, reason, effective_role = await ktp_service.evaluate_ktp_access(current_user, person_id)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=reason,
        )

    try:
        user_clearance = getattr(current_user, "clearance_level", "Internal") or "Internal"
        ktp_data = await ktp_service.build_ktp_package(
            target_person_id=person_id,
            requestor_id=str(current_user.id),
            requestor_role=effective_role,
            user_clearance=user_clearance,
        )
        return ktp_data
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        logger.error(f"Failed to build KTP package for person {person_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to compile knowledge transfer package: {str(e)}",
        )


@router.post("/people/{person_id}/assign-handover", response_model=AssignHandoverResponse)
async def assign_person_handover(
    person_id: str,
    payload: AssignHandoverRequest,
    current_user: CurrentUser,
):
    """
    KTP Hub: Assigns a person's knowledge handover to another team member (successor).
    Creates directed [:HANDED_OVER_TO] edge in FalkorDB.
    Enforces Admin or Direct/2-Hop Manager permission check.
    """
    try:
        return await ktp_service.assign_ktp_handover(
            source_person_id=person_id,
            target_person_id=payload.target_person_id,
            notes=payload.notes,
            user=current_user,
        )
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.error(f"Failed to assign handover for person {person_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to assign handover: {str(e)}",
        )


@router.get("/{doc_id}", response_model=KnowledgeTransferPackageResponse)
async def get_ktp_document(
    doc_id: str,
    current_user: CurrentUser,
):
    """
    UKGOE Phase 9: Retrieves a generated KTP document by ID,
    including IR-09 stale cascade warnings if referenced entities were modified.
    """
    try:
        user_clearance = getattr(current_user, "clearance_level", "Internal") or "Internal"
        ktp = await ktp_service.get_ktp_document(doc_id, requestor_clearance=user_clearance)
        if not ktp:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Knowledge Transfer Package document '{doc_id}' not found.",
            )
        return ktp
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get KTP document {doc_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve KTP document: {str(e)}",
        )

