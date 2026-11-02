from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


# 1. Connectors Table
class ConnectorConfig(Base):
    __tablename__ = "connectors"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    connector_type: Mapped[str] = mapped_column(String(50), default="databricks", nullable=False)
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    workspace_id: Mapped[str] = mapped_column(String(100), nullable=False)
    token_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    selected_warehouse_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    selected_tables: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON or comma-separated table names
    status: Mapped[str] = mapped_column(String(50), default="configured", nullable=False)
    auto_index: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sync_interval_minutes: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    sync_jobs: Mapped[list[ConnectorSyncJob]] = relationship(
        back_populates="connector",
        cascade="all, delete-orphan",
    )
    entities: Mapped[list[SourceEntity]] = relationship(
        back_populates="connector",
        cascade="all, delete-orphan",
    )


# 2. Connector Sync Jobs Table
class ConnectorSyncJob(Base):
    __tablename__ = "connector_sync_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    connector_id: Mapped[str] = mapped_column(ForeignKey("connectors.id", ondelete="CASCADE"), nullable=False)
    mode: Mapped[str] = mapped_column(String(30), default="full", nullable=False)  # full | incremental
    status: Mapped[str] = mapped_column(String(30), default="queued", nullable=False)  # queued | running | completed | failed
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    records_synced: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    docs_indexed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    connector: Mapped[ConnectorConfig] = relationship(back_populates="sync_jobs")


# 3. Source Entities Table
class SourceEntity(Base):
    __tablename__ = "source_entities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    connector_id: Mapped[str] = mapped_column(ForeignKey("connectors.id", ondelete="CASCADE"), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)  # notebook, file, job, cluster, user
    source_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    workspace_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    project_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    owner_user_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    team_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    connector: Mapped[ConnectorConfig] = relationship(back_populates="entities")
    document_metadata: Mapped[list[DocumentMetadata]] = relationship(
        back_populates="source_entity",
        cascade="all, delete-orphan",
    )


# 4. Document Metadata Table
class DocumentMetadata(Base):
    __tablename__ = "document_metadata"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_entity_id: Mapped[str] = mapped_column(ForeignKey("source_entities.id", ondelete="CASCADE"), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(255), nullable=False)
    bucket_name: Mapped[str] = mapped_column(String(100), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    source_entity: Mapped[SourceEntity] = relationship(back_populates="document_metadata")
    versions: Mapped[list[DocumentVersion]] = relationship(
        back_populates="doc_meta",
        cascade="all, delete-orphan",
    )


# 5. Document Versions Table
class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(ForeignKey("document_metadata.id", ondelete="CASCADE"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    storage_key: Mapped[str] = mapped_column(String(255), nullable=False)
    checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    doc_meta: Mapped[DocumentMetadata] = relationship(back_populates="versions")


# 6. Permissions Table
class Permission(Base):
    __tablename__ = "permissions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)  # document, project, team
    entity_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    principal_type: Mapped[str] = mapped_column(String(50), nullable=False)  # user, team, public
    principal_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    access_level: Mapped[str] = mapped_column(String(50), default="READ", nullable=False)
    scope: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


# 7. People Table
class Person(Base):
    __tablename__ = "people"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(150), unique=True, index=True, nullable=False)
    role: Mapped[str | None] = mapped_column(String(100), nullable=True)
    team_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    department_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


# 8. Teams Table
class Team(Base):
    __tablename__ = "teams"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    department_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


# 9. Departments Table
class Department(Base):
    __tablename__ = "departments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


# 10. Projects Table
class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    workspace_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    owner_team_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


# 11. Documents Table
class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    source_system: Mapped[str] = mapped_column(String(50), default="databricks", nullable=False)
    source_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    project_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    team_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    owner_user_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    storage_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
