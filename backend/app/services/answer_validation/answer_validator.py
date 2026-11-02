from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sync_reconciliation_job import AnswerValidationLog
from app.services.answer_validation.confidence_gate import ConfidenceGate
from app.services.answer_validation.evidence_ranker import EvidenceRanker
from app.services.answer_validation.provenance_validator import ProvenanceValidator
from app.services.permissions.visibility_service import VisibilityService

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    status: str  # "valid", "insufficient_evidence", "unauthorized", "invalid"
    confidence_score: float
    is_valid: bool
    safe_answer_text: str
    validated_source_ids: List[str]
    failure_reason: Optional[str] = None


class AnswerValidator:
    """
    Validates answer quality, provenance grounding, authorization, and confidence
    before answers are returned to users.
    """

    SAFE_FALLBACK = "I could not find enough authorized evidence to answer this safely."

    def __init__(
        self,
        evidence_ranker: Optional[EvidenceRanker] = None,
        provenance_validator: Optional[ProvenanceValidator] = None,
        visibility_service: Optional[VisibilityService] = None,
        gate: Optional[ConfidenceGate] = None,
    ):
        self.ranker = evidence_ranker or EvidenceRanker()
        self.provenance_validator = provenance_validator or ProvenanceValidator()
        self.visibility_service = visibility_service or VisibilityService()
        self.gate = gate or ConfidenceGate()

    async def validate_answer(
        self,
        query: str,
        answer_text: str,
        source_document_ids: List[str],
        confidence_score: float,
        user_id: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> ValidationResult:
        # 1. Check for basic empty answers
        if not answer_text or not answer_text.strip():
            return ValidationResult(
                status="invalid",
                confidence_score=0.0,
                is_valid=False,
                safe_answer_text=self.SAFE_FALLBACK,
                validated_source_ids=[],
                failure_reason="empty_answer_text",
            )

        # 2. Check for missing sources
        if not source_document_ids:
            return ValidationResult(
                status="insufficient_evidence",
                confidence_score=round(confidence_score * 0.3, 2),
                is_valid=False,
                safe_answer_text=self.SAFE_FALLBACK,
                validated_source_ids=[],
                failure_reason="no_source_documents_cited",
            )

        # 3. Check document existence in DB if db is provided
        valid_doc_ids = source_document_ids
        if db:
            valid_doc_ids = await self.provenance_validator.validate_document_ids(
                source_document_ids, db
            )
            if not valid_doc_ids:
                return ValidationResult(
                    status="insufficient_evidence",
                    confidence_score=0.1,
                    is_valid=False,
                    safe_answer_text=self.SAFE_FALLBACK,
                    validated_source_ids=[],
                    failure_reason="cited_documents_do_not_exist",
                )

            # 4. Check user authorization if user_id is provided
            if user_id:
                authorized_ids = await self.visibility_service.filter_authorized_document_ids(
                    valid_doc_ids, user_id, db
                )
                if not authorized_ids:
                    return ValidationResult(
                        status="unauthorized",
                        confidence_score=0.0,
                        is_valid=False,
                        safe_answer_text=self.SAFE_FALLBACK,
                        validated_source_ids=[],
                        failure_reason="user_unauthorized_to_view_evidence",
                    )
                valid_doc_ids = authorized_ids

        # 5. Evaluate Confidence Gate
        passes_gate = self.gate.evaluate(
            confidence_score=confidence_score,
            source_count=len(valid_doc_ids),
            has_grounding=True,
        )

        if not passes_gate:
            return ValidationResult(
                status="insufficient_evidence",
                confidence_score=round(confidence_score, 2),
                is_valid=False,
                safe_answer_text=self.SAFE_FALLBACK,
                validated_source_ids=[],
                failure_reason=f"confidence_score_{confidence_score}_below_threshold",
            )

        # 6. Log result in database
        if db:
            try:
                log_entry = AnswerValidationLog(
                    user_id=user_id,
                    query=query,
                    answer_text=answer_text,
                    source_document_ids=",".join(valid_doc_ids),
                    confidence_score=round(confidence_score, 2),
                    validation_status="valid",
                    failure_reason=None,
                )
                db.add(log_entry)
                await db.commit()
            except Exception as e:
                logger.warning(f"Failed to record answer validation log: {e}")

        return ValidationResult(
            status="valid",
            confidence_score=round(confidence_score, 2),
            is_valid=True,
            safe_answer_text=answer_text,
            validated_source_ids=valid_doc_ids,
            failure_reason=None,
        )

