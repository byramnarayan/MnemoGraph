from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


# 1. sync_reconciliation_jobs
class SyncReconciliationJob(Base):
    __tablename__ = "sync_reconciliation_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    connector_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), default="databricks", nullable=False)
    mode: Mapped[str] = mapped_column(String(30), default="incremental", nullable=False)  # full | incremental
    status: Mapped[str] = mapped_column(String(30), default="queued", nullable=False)  # queued | running | completed | failed
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    documents_checked: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    documents_changed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    docs_deleted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    stale_edges_removed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    vector_entries_removed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    errors: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


# 2. document_version_state
class DocumentVersionState(Base):
    __tablename__ = "document_version_state"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    source_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    workspace_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    version_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # sha256
    previous_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


# 3. permission_policy
class PermissionPolicy(Base):
    __tablename__ = "permission_policy"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    principal_type: Mapped[str] = mapped_column(String(50), nullable=False)  # User, Team, Role, Public
    principal_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)  # Document, Project, Workspace
    entity_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    access_level: Mapped[str] = mapped_column(String(30), default="READ", nullable=False)  # READ, WRITE, ADMIN
    scope: Mapped[str] = mapped_column(String(50), default="DIRECT", nullable=False)  # DIRECT, INHERITED
    inherited_from: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


# 4. answer_validation_log
class AnswerValidationLog(Base):
    __tablename__ = "answer_validation_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_document_ids: Mapped[str] = mapped_column(Text, default="", nullable=False)  # JSON or comma-separated
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    validation_status: Mapped[str] = mapped_column(String(50), nullable=False)  # valid, insufficient_evidence, unauthorized, invalid
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

