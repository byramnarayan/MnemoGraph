from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ActionProposalDraft(Base):
    """
    Relational draft storage for Action Proposals generated from validated predictive scenarios.
    Ensures zero mutation to the canonical FalkorDB knowledge graph.
    """

    __tablename__ = "action_proposal_drafts"

    id: Mapped[str] = mapped_column(String(50), primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    scenario_id: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    problem_statement: Mapped[str] = mapped_column(Text, nullable=False)
    affected_scope: Mapped[str] = mapped_column(String(120), nullable=False)
    proposed_action: Mapped[str] = mapped_column(Text, nullable=False)
    implementation_steps: Mapped[list[str]] = mapped_column(JSON, default=list)
    suggested_role: Mapped[str | None] = mapped_column(String(100), nullable=True)
    priority: Mapped[str] = mapped_column(String(20), default="High", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="DRAFT", nullable=False)  # DRAFT, IN_REVIEW, APPROVED
    verification_criteria: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_citations: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    created_by_email: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

