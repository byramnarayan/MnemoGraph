from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RelationshipRecord(Base):
    """
    Canonical Directed Typed Relationship Ledger across Universal Taxonomy.
    """
    __tablename__ = "relationships"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    target_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    relationship_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    context: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_document_id: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    is_inferred: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    extracted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

