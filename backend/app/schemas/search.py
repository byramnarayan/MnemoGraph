from typing import Any
from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=2, description="Natural language question or search phrase")
    limit: int = Field(10, ge=1, le=50)


class SearchResultItem(BaseModel):
    entity_type: str
    title: str
    score: float
    source_url: str | None = None
    owners: list[str] = Field(default_factory=list)
    teams: list[str] = Field(default_factory=list)
    excerpt: str | None = None
    storage_key: str | None = None


class SearchResponse(BaseModel):
    results: list[SearchResultItem]

