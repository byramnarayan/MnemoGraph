from __future__ import annotations

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser
from app.schemas.permissions import (
    DocumentPermissionsResponse,
    GrantDetail,
    PermissionCheckRequest,
    PermissionCheckResponse,
    PermissionResolveRequest,
    PermissionResolveResponse,
)
from app.services.permissions.inherited_permission_resolver import InheritedPermissionResolver
from app.services.permissions.permission_resolver import PermissionResolver

router = APIRouter(tags=["Permissions"])


# 1. POST /api/v1/permissions/check
@router.post("/permissions/check", response_model=PermissionCheckResponse)
async def check_permission(
    payload: PermissionCheckRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """
    Check if a user is authorized to perform action on an entity.
    """
    resolver = PermissionResolver()
    result = await resolver.check_access(
        user_id=payload.user_id,
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        required_level=payload.required_level,
        db=db,
    )
    return PermissionCheckResponse(
        allowed=result.allowed,
        reason=result.reason,
        effective_access_level=result.effective_access_level,
    )


# 2. POST /api/v1/permissions/resolve
@router.post("/permissions/resolve", response_model=PermissionResolveResponse)
async def resolve_permissions(
    payload: PermissionResolveRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """
    Resolve all direct and inherited grants on an entity.
    """
    resolver = PermissionResolver()
    result = await resolver.check_access(
        user_id=payload.user_id,
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        db=db,
    )
    grants = [
        GrantDetail(
            principal_type=g.principal_type,
            principal_id=g.principal_id,
            access_level=g.access_level,
            scope=g.scope,
            inherited_from=g.inherited_from,
        )
        for g in result.grants
    ]
    return PermissionResolveResponse(
        allowed=result.allowed,
        reason=result.reason,
        grants=grants,
    )


# 3. GET /api/v1/documents/{document_id}/permissions
@router.get("/documents/{document_id}/permissions", response_model=DocumentPermissionsResponse)
async def get_document_permissions(
    document_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """
    Return all grants attached or inherited by a document.
    """
    inherited_resolver = InheritedPermissionResolver()
    grants_raw = await inherited_resolver.resolve_inherited_grants("Document", document_id, db)
    grants = [
        GrantDetail(
            principal_type=g.principal_type,
            principal_id=g.principal_id,
            access_level=g.access_level,
            scope=g.scope,
            inherited_from=g.inherited_from,
        )
        for g in grants_raw
    ]
    return DocumentPermissionsResponse(document_id=document_id, grants=grants)

