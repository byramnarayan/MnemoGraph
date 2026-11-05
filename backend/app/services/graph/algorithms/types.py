from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class GraphPath(BaseModel):
    source_id: str
    target_id: str
    nodes: list[str] = Field(default_factory=list)
    relationships: list[str] = Field(default_factory=list)
    length: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class CentralityScore(BaseModel):
    node_id: str
    score: float
    algorithm: str


class CommunityAssignment(BaseModel):
    node_id: str
    community_id: int
    algorithm: str

