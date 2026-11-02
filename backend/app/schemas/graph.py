from typing import Any
from pydantic import BaseModel, Field


class GraphEntityLookupResponse(BaseModel):
    id: str
    label: str
    properties: dict[str, Any]


class GraphNeighborEdge(BaseModel):
    relation: str
    target_id: str
    target_label: str
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphNeighborhoodResponse(BaseModel):
    entity_id: str
    label: str
    properties: dict[str, Any]
    incoming: list[GraphNeighborEdge] = Field(default_factory=list)
    outgoing: list[GraphNeighborEdge] = Field(default_factory=list)


class SearchDatabricksRequest(BaseModel):
    query: str = Field(..., min_length=2)
    limit: int = Field(10, ge=1, le=50)


class SearchDatabricksResult(BaseModel):
    entity_type: str
    title: str
    score: float
    source_url: str | None = None
    owners: list[str] = Field(default_factory=list)
    teams: list[str] = Field(default_factory=list)
    excerpt: str | None = None
    storage_key: str | None = None
    permissions: list[str] = Field(default_factory=list)


class SearchDatabricksResponse(BaseModel):
    results: list[SearchDatabricksResult]


class GraphQueryRequest(BaseModel):
    cypher: str = Field(..., min_length=3, description="Cypher query to execute")
    limit: int = Field(50, ge=1, le=200)


class GraphNodeItem(BaseModel):
    id: str
    label: str
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphEdgeItem(BaseModel):
    source: str
    target: str
    relation: str
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphQueryResponse(BaseModel):
    cypher: str
    nodes: list[GraphNodeItem] = Field(default_factory=list)
    edges: list[GraphEdgeItem] = Field(default_factory=list)
    raw_rows: list[list[Any]] = Field(default_factory=list)
    total_nodes: int = 0
    total_edges: int = 0

