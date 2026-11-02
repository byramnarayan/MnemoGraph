from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel


class PermissionCheckRequest(BaseModel):
    user_id: str
    entity_type: str = "Document"  # Document | Project | Workspace
    entity_id: str
    required_level: str = "READ"


class PermissionCheckResponse(BaseModel):
    allowed: bool
    reason: str
    effective_access_level: Optional[str] = None


class GrantDetail(BaseModel):
    principal_type: str
    principal_id: str
    access_level: str
    scope: str = "DIRECT"
    inherited_from: Optional[str] = None


class PermissionResolveRequest(BaseModel):
    user_id: str
    entity_type: str = "Project"
    entity_id: str


class PermissionResolveResponse(BaseModel):
    allowed: bool
    reason: str
    grants: List[GrantDetail] = []


class DocumentPermissionsResponse(BaseModel):
    document_id: str
    grants: List[GrantDetail] = []

