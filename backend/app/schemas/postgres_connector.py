from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class PostgresConnectionTestRequest(BaseModel):
    host: str = Field(..., description="PostgreSQL host IP or domain")
    port: int = Field(5432, description="PostgreSQL port")
    database: str = Field(..., description="Target database name")
    username: str = Field(..., description="Username with read-only access")
    password: str = Field(..., description="User password")
    ssl_mode: str = Field("prefer", description="SSL connection mode")


class PostgresConnectionTestResponse(BaseModel):
    ok: bool = True
    success: bool = True
    server_version: str | None = None
    database_name: str | None = None
    connected_user: str | None = None
    message: str | None = None
    error: str | None = None


class PostgresDiscoveredColumn(BaseModel):
    name: str
    data_type: str
    is_nullable: bool = True
    is_primary_key: bool = False
    is_cursor_candidate: bool = False


class PostgresDiscoveredTable(BaseModel):
    schema_name: str
    table_name: str
    primary_keys: list[str] = Field(default_factory=list)
    suggested_cursor_col: str | None = None
    suggested_entity_type: str = "Document"
    columns: list[PostgresDiscoveredColumn] = Field(default_factory=list)


class PostgresDiscoveredSchemaResponse(BaseModel):
    tables: list[PostgresDiscoveredTable] = Field(default_factory=list)


class PostgresTableConfigDTO(BaseModel):
    id: str | None = None
    schema_name: str
    table_name: str
    primary_key_columns: list[str] = Field(default_factory=list)
    cursor_column: str | None = None
    included_columns: list[str] = Field(default_factory=list)
    excluded_columns: list[str] = Field(default_factory=list)
    text_columns: list[str] = Field(default_factory=list)
    entity_type: str = "Document"
    visibility_policy: str = "Internal"
    enabled: bool = True
    last_cursor_value: str | None = None


class PostgresConnectorCreateRequest(BaseModel):
    name: str = Field(..., description="Display name for the connector")
    host: str
    port: int = 5432
    database: str
    username: str
    password: str
    ssl_mode: str = "prefer"
    tables: list[PostgresTableConfigDTO] = Field(default_factory=list)

