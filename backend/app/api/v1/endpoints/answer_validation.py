from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser
from app.schemas.answer_validation import (
    AnswerValidateRequest,
    AnswerValidateResponse,
)
from app.services.answer_validation.answer_validator import AnswerValidator

router = APIRouter(tags=["Answer Quality Validation"])


# 1. POST /api/v1/answers/validate
@router.post("/answers/validate", response_model=AnswerValidateResponse)
async def validate_answer_quality(
    payload: AnswerValidateRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """
    Validate answer quality, provenance grounding, authorization, and confidence.
    """
    validator = AnswerValidator()
    result = await validator.validate_answer(
        query=payload.query,
        answer_text=payload.answer_text,
        source_document_ids=payload.source_document_ids,
        confidence_score=payload.confidence_score,
        user_id=payload.user_id or current_user.id,
        db=db,
    )
    return AnswerValidateResponse(
        status=result.status,
        confidence_score=result.confidence_score,
        is_valid=result.is_valid,
        safe_answer_text=result.safe_answer_text,
        validated_source_ids=result.validated_source_ids,
        failure_reason=result.failure_reason,
    )

