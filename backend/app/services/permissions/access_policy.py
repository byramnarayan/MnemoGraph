from __future__ import annotations

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel


class AccessLevel(str, Enum):
    READ = "READ"
    WRITE = "WRITE"
    ADMIN = "ADMIN"


class PrincipalType(str, Enum):
    USER = "User"
    TEAM = "Team"
    ROLE = "Role"
    PUBLIC = "Public"


class EntityType(str, Enum):
    DOCUMENT = "Document"
    PROJECT = "Project"
    WORKSPACE = "Workspace"
    DECISION = "Decision"


class AccessGrant(BaseModel):
    principal_type: str
    principal_id: str
    access_level: str
    scope: str = "DIRECT"
    inherited_from: Optional[str] = None


class AccessPolicyResult(BaseModel):
    allowed: bool
    reason: str
    effective_access_level: Optional[str] = None
    grants: List[AccessGrant] = []

