from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class OntologyEvolutionRecord(Base):
    """
    Tracks candidate entity classes and novel relationship types identified
    by pattern detection across multiple documents (Step 6.1, 6.2).
    """
    __tablename__ = "ontology_evolution_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    candidate_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "CLASS" | "RELATION"
    candidate_name: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    source_document_ids: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    exemplar_entities: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    frequency: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False)  # PENDING, CANDIDATE, APPROVED, REJECTED
    metadata_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))


class InferenceRuleRecord(Base):
    """
    Registers dynamically submitted YAML inference rules (Step 6.3).
    """
    __tablename__ = "inference_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    rule_id: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    trigger_entity: Mapped[str] = mapped_column(String(50), nullable=False)
    rule_yaml: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    registered_by: Mapped[str] = mapped_column(String(100), default="system", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class ConstraintViolationRecord(Base):
    """
    Audits property constraint violations for human-gated constraint relaxation (Step 6.4).
    """
    __tablename__ = "constraint_violations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    entity_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    entity_class: Mapped[str] = mapped_column(String(50), nullable=False)
    property_name: Mapped[str] = mapped_column(String(100), nullable=False)
    violation_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_constraint: Mapped[str] = mapped_column(Text, nullable=False)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

