from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser
from app.models.connector import Document, Project
from app.models.document_section import (
    DecisionMention,
    DocumentMention,
    DocumentSection,
    ExtractedEntity,
    ProjectMention,
)
from app.models.provenance import Decision
from app.schemas.document_enrichment import (
    DecisionMentionResponse,
    DocumentEnrichRequest,
    DocumentEnrichResponse,
    DocumentMentionResponse,
    DocumentSectionResponse,
    ExtractedEntityResponse,
    ProjectMentionResponse,
)
from app.services.enrichment.enrichment_service import EnrichmentService

router = APIRouter(tags=["Document Enrichment"])


# 1. POST /api/v1/documents/{document_id}/enrich
@router.post("/documents/{document_id}/enrich", response_model=DocumentEnrichResponse)
async def enrich_document(
    document_id: str,
    payload: DocumentEnrichRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """
    Parse and enrich document text into structured sections, extracted entities,
    and project/decision mentions. Connects entities into the knowledge graph.
    """
    enricher = EnrichmentService()
    try:
        result = await enricher.enrich_document(
            document_id=document_id,
            db=db,
            raw_text=payload.raw_text,
            force_reparse=payload.force_reparse,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Enrichment failed: {str(e)}",
        )


# 2. GET /api/v1/documents/{document_id}/sections
@router.get("/documents/{document_id}/sections", response_model=List[DocumentSectionResponse])
async def get_document_sections(
    document_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Return all parsed sections for a document sorted by order_index."""
    stmt = (
        select(DocumentSection)
        .where(DocumentSection.document_id == document_id)
        .order_index_by(DocumentSection.order_index)
        if hasattr(select(DocumentSection), "order_index_by")
        else select(DocumentSection)
        .where(DocumentSection.document_id == document_id)
        .order_by(DocumentSection.order_index)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


# 3. GET /api/v1/documents/{document_id}/entities
@router.get("/documents/{document_id}/entities", response_model=List[ExtractedEntityResponse])
async def get_document_entities(
    document_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Return all extracted entities for a document."""
    stmt = (
        select(ExtractedEntity)
        .where(ExtractedEntity.document_id == document_id)
        .order_by(ExtractedEntity.created_at)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


# 4. GET /api/v1/documents/{document_id}/mentions
@router.get("/documents/{document_id}/mentions", response_model=List[DocumentMentionResponse])
async def get_document_mentions(
    document_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Return all mention records for a document."""
    stmt = (
        select(DocumentMention)
        .where(DocumentMention.document_id == document_id)
        .order_by(DocumentMention.created_at)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


# 5. GET /api/v1/projects/{project_id}/mentions
@router.get("/projects/{project_id}/mentions", response_model=List[ProjectMentionResponse])
async def get_project_mentions(
    project_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Return all document mentions for a given project."""
    stmt = (
        select(ProjectMention)
        .where(ProjectMention.project_id == project_id)
        .order_by(ProjectMention.created_at.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()


# 6. GET /api/v1/decisions/{decision_id}/mentions
@router.get("/decisions/{decision_id}/mentions", response_model=List[DecisionMentionResponse])
async def get_decision_mentions(
    decision_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Return all document references attached to a decision."""
    stmt = (
        select(DecisionMention)
        .where(DecisionMention.decision_id == decision_id)
        .order_by(DecisionMention.created_at.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()

