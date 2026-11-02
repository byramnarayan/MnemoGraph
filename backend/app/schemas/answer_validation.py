from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel


class AnswerValidateRequest(BaseModel):
    query: str
    answer_text: str
    source_document_ids: List[str]
    confidence_score: float = 0.8
    user_id: Optional[str] = None


class AnswerValidateResponse(BaseModel):
    status: str  # "valid" | "insufficient_evidence" | "unauthorized" | "invalid"
    confidence_score: float
    is_valid: bool
    safe_answer_text: str
    validated_source_ids: List[str]
    failure_reason: Optional[str] = None

