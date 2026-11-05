from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class EntityRecord(Base):
    """
    Canonical Relational Ledger Table for all Universal Entity Classes.
    """
    __tablename__ = "entities"

    entity_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    entity_class: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    properties: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    is_stub: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    completeness_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    validation_status: Mapped[str] = mapped_column(String(50), default="valid", nullable=False)
    data_quality_grade: Mapped[str] = mapped_column(String(5), default="A", nullable=False)
    source_document_ids: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    property_history: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    provenance_sources: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

