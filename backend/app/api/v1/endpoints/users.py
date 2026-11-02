from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from PIL import UnidentifiedImageError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import CurrentUser
from app.schemas.user import MsgResponse, UserResponse, UserUpdate
from app.services.s3_service import (
    delete_profile_image,
    process_profile_image,
    upload_profile_image,
)

router = APIRouter()


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

