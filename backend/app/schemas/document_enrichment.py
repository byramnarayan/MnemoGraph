from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# Request Schema
class DocumentEnrichRequest(BaseModel):
    force_reparse: bool = False
    raw_text: Optional[str] = None


# Response Schema for /enrich
class DocumentEnrichResponse(BaseModel):
    document_id: str
    status: str
    sections_count: int
    entities_count: int
    mentions_count: int
    project_mentions_count: Optional[int] = 0
    decision_mentions_count: Optional[int] = 0
    graph_enrichment: Optional[Dict[str, Any]] = None


# Section Schema
class DocumentSectionResponse(BaseModel):
    id: str
    document_id: str
    section_type: str
    heading: Optional[str] = None
    content: str
    order_index: int
    source_start: int
    source_end: int
    created_at: datetime

    class Config:
        from_attributes = True


# Extracted Entity Schema
class ExtractedEntityResponse(BaseModel):
    id: str
    document_id: str
    entity_type: str
    entity_value: str
    normalized_value: str
    confidence_score: float
    source_section_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# Document Mention Schema
class DocumentMentionResponse(BaseModel):
    id: str
    document_id: str
    mention_type: str
    mention_value: str
    normalized_value: str
    source_section_id: Optional[str] = None
    confidence_score: float
    created_at: datetime

    class Config:
        from_attributes = True


# Project Mention Schema
class ProjectMentionResponse(BaseModel):
    id: str
    document_id: str
    project_id: str
    mention_count: int
    source_section_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# Decision Mention Schema
class DecisionMentionResponse(BaseModel):
    id: str
    document_id: str
    decision_id: str
    mention_count: int
    source_section_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

