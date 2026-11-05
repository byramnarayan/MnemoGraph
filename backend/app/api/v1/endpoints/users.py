from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from PIL import UnidentifiedImageError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import CurrentUser
from app.schemas.user import (
    DiscoveredPersonResponse,
    MsgResponse,
    ProvisionUserRequest,
    ProvisionedUserResponse,
    UserResponse,
    UserUpdate,
)
from app.services.email_service import send_onboarding_welcome_email
from app.services.s3_service import (
    delete_profile_image,
    process_profile_image,
    upload_profile_image,
)
from app.services.users.user_provisioning_service import UserProvisioningService

router = APIRouter()
provisioning_service = UserProvisioningService()


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(current_user: CurrentUser):
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_current_user_profile(
    update_data: UserUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, val in update_dict.items():
        setattr(current_user, field, val)

    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.post("/me/avatar", response_model=UserResponse)
async def upload_avatar(
    file: Annotated[UploadFile, File(...)],
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPEG, PNG, and WebP images are allowed.",
        )

    content = await file.read()
    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds maximum allowed upload size (5MB).",
        )

    try:
        processed_bytes, filename = process_profile_image(content)
    except (UnidentifiedImageError, OSError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image file or corrupted image data.",
        )

    # Delete old avatar from S3 if exists
    old_avatar = current_user.image_file
    if old_avatar:
        try:
            await delete_profile_image(old_avatar)
        except Exception as e:
            print(f"[S3 Delete Error]: {e}")

    # Upload new avatar to S3
    try:
        await upload_profile_image(processed_bytes, filename)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload image to S3: {str(e)}",
        )

    current_user.image_file = filename
    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.delete("/me/avatar", response_model=UserResponse)
async def delete_avatar(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if current_user.image_file:
        try:
            await delete_profile_image(current_user.image_file)
        except Exception as e:
            print(f"[S3 Delete Error]: {e}")

        current_user.image_file = None
        await db.commit()
        await db.refresh(current_user)

    return current_user


# =====================================================================
# UKGOE Part 8: Discovered Person Provisioning & Manual User Onboarding
# =====================================================================
@router.get("/discovered-personnel", response_model=list[DiscoveredPersonResponse])
async def list_discovered_personnel(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Lists all un-provisioned human names and Person entities extracted
    from ingested institutional documents.
    """
    if "admin" not in current_user.role.lower():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can review discovered personnel.",
        )
    return await provisioning_service.list_discovered_personnel(db)


@router.post("/provision-discovered-person", response_model=ProvisionedUserResponse)
async def provision_discovered_person(
    req: ProvisionUserRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    background_tasks: BackgroundTasks,
):
    """
    Admin workflow: assigns email, password, role, position, location, and clearance
    to a discovered person, creating their system User login account and synchronizing FalkorDB.
    Dispatches welcome onboarding email with credentials.
    """
    if "admin" not in current_user.role.lower():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can provision new users.",
        )
    try:
        res = await provisioning_service.provision_discovered_person(
            req=req,
            db=db,
            admin_email=current_user.email,
        )

        # Dispatch welcome email with credentials in background
        background_tasks.add_task(
            send_onboarding_welcome_email,
            to_email=req.email,
            full_name=req.full_name,
            temp_password=req.password,
            role=req.role,
            clearance_level=req.clearance_level,
        )

        return res
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/personnel/{person_id}/status")
async def get_personnel_status(
    person_id: str,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Returns graph and auth account status for a given person entity ID.
    """
    return await provisioning_service.get_personnel_status(person_id, db)
