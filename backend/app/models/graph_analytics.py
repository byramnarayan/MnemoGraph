from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from sqlalchemy import DateTime, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class GraphAnalyticsSnapshot(Base):
    """
    Persisted topological analytics snapshot (PageRank, Betweenness, Centrality, Communities).
    Enforces that heavy global algorithms are precomputed and read from fast snapshots.
    """
    __tablename__ = "graph_analytics_snapshots"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    algorithm_name: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    target_label: Mapped[str | None] = mapped_column(String(50), nullable=True)
    relationship_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    parameters: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    metric_values: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    node_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

