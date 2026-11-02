from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


# 1. document_sections
class DocumentSection(Base):
    __tablename__ = "document_sections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    section_type: Mapped[str] = mapped_column(String(50), nullable=False)  # heading, paragraph, list, code, table, sql
    heading: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    source_start: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    source_end: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    extracted_entities: Mapped[list[ExtractedEntity]] = relationship(
        "ExtractedEntity",
        back_populates="source_section",
        cascade="all, delete-orphan",
    )


# 2. extracted_entities
class ExtractedEntity(Base):
    __tablename__ = "extracted_entities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)  # person, team, project, product, meeting, decision, ticket, artifact
    entity_value: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_value: Mapped[str] = mapped_column(String(255), nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    source_section_id: Mapped[str | None] = mapped_column(ForeignKey("document_sections.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    source_section: Mapped[DocumentSection | None] = relationship("DocumentSection", back_populates="extracted_entities")


# 3. document_mentions
class DocumentMention(Base):
    __tablename__ = "document_mentions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    mention_type: Mapped[str] = mapped_column(String(50), nullable=False)  # person, team, project, decision, ticket, meeting, artifact
    mention_value: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_value: Mapped[str] = mapped_column(String(255), nullable=False)
    source_section_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


# 4. project_mentions
class ProjectMention(Base):
    __tablename__ = "project_mentions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    project_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    mention_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    source_section_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


# 5. decision_mentions
class DecisionMention(Base):
    __tablename__ = "decision_mentions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    decision_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    mention_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    source_section_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

