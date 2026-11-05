from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PostgresTableConfig(Base):
    """
    Configuration and incremental cursor state per table for external PostgreSQL connectors.
    """
    __tablename__ = "postgres_table_configs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    connector_id: Mapped[str] = mapped_column(ForeignKey("connectors.id", ondelete="CASCADE"), nullable=False, index=True)
    schema_name: Mapped[str] = mapped_column(String(100), nullable=False)
    table_name: Mapped[str] = mapped_column(String(150), nullable=False)
    primary_key_columns: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    cursor_column: Mapped[str | None] = mapped_column(String(100), nullable=True)
    included_columns: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    excluded_columns: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    text_columns: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), default="Document", nullable=False)
    visibility_policy: Mapped[str] = mapped_column(String(50), default="Internal", nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_cursor_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_successful_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        UniqueConstraint("connector_id", "schema_name", "table_name", name="uq_pg_table_config"),
        Index("ix_pg_table_enabled", "connector_id", "enabled"),
    )

