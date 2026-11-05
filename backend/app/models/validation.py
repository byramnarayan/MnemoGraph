from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ConflictRecord(Base):
    """
    Audits contradictory factual assertions across multiple sources (INV-07).
    """
    __tablename__ = "conflicts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    entity_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    property_name: Mapped[str] = mapped_column(String(100), nullable=False)
    val_a: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_a: Mapped[str | None] = mapped_column(String(255), nullable=True)
    val_b: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_b: Mapped[str | None] = mapped_column(String(255), nullable=True)
    resolved_val: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class ValidationLogRecord(Base):
    """
    Audits temporal, schema, and completeness validation results.
    """
    __tablename__ = "validation_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    entity_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    rule_id: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class InferenceEventRecord(Base):
    """
    Audits execution of Universal Inference Rules (IR-01 through IR-10).
    """
    __tablename__ = "inference_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    rule_id: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    trigger_entity_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    affected_entity_ids: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    emitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    consumed_by: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)


class CascadeLogRecord(Base):
    """
    Audits IR-09 downstream invalidation cascade events.
    """
    __tablename__ = "cascade_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    trigger_entity_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    trigger_event: Mapped[str] = mapped_column(String(50), nullable=False)
    affected_entities: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    cascade_depth: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class EntityAccessLogRecord(Base):
    """
    Audits entity access attempts and security boundary enforcement (INV-05).
    """
    __tablename__ = "entity_access_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    entity_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    access_level: Mapped[str] = mapped_column(String(50), nullable=False)
    granted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
