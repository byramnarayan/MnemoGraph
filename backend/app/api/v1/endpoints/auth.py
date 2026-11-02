from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    generate_reset_token,
    hash_password,
    hash_reset_token,
    verify_password,
)
from app.models.user import PasswordResetToken, User
from app.schemas.user import (
    ForgotPasswordRequest,
    MsgResponse,
    ResetPasswordRequest,
    Token,
    UserLogin,
    UserRegister,
    UserResponse,
)
from app.services.email_service import send_password_reset_email

router = APIRouter()


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(
    data: UserRegister,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    # Check if email is already taken
    result = await db.execute(
        select(User).where(func.lower(User.email) == data.email.lower())
    )
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists.",
        )

    # Check if tenant slug is already taken (if provided)
    if data.tenant_slug:
        res_slug = await db.execute(
            select(User).where(func.lower(User.tenant_slug) == data.tenant_slug.lower())
        )
        if res_slug.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant identifier slug is already taken.",
            )

    new_user = User(
        full_name=data.full_name,
        email=data.email.lower(),
        tenant_slug=data.tenant_slug.lower() if data.tenant_slug else None,
        company_name=data.company_name,
        industry_vertical=data.industry_vertical,
        department=data.department,
        role=data.role,
        password_hash=hash_password(data.password),
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    token = create_access_token(data={"sub": str(new_user.id)})
    return Token(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(new_user),
    )


@router.post("/login", response_model=Token)
async def login(
    data: UserLogin,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(User).where(func.lower(User.email) == data.email.lower())
    )
    user = result.scalars().first()

    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive. Please contact your administrator.",
        )

    token = create_access_token(data={"sub": str(user.id)})
    return Token(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.post("/token", response_model=Token)
async def login_oauth2(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    # Standard OAuth2 endpoint for Swagger UI & API specs
    result = await db.execute(
        select(User).where(func.lower(User.email) == form_data.username.lower())
    )
    user = result.scalars().first()

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username (email) or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(data={"sub": str(user.id)})
    return Token(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.post("/forgot-password", response_model=MsgResponse)
async def forgot_password(
    request: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(User).where(func.lower(User.email) == request.email.lower())
    )
    user = result.scalars().first()
    if user:
        raw_token = generate_reset_token()
        token_hash = hash_reset_token(raw_token)
        expires_at = datetime.now(UTC) + timedelta(minutes=settings.reset_token_expire_minutes)

        reset_record = PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        db.add(reset_record)
        await db.commit()

        background_tasks.add_task(send_password_reset_email, user.email, raw_token)

    return MsgResponse(message="If the email exists, a password reset link has been dispatched.")


@router.post("/reset-password", response_model=MsgResponse)
async def reset_password(
    request: ResetPasswordRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    token_hash = hash_reset_token(request.token)
    result = await db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.expires_at > datetime.now(UTC),
        )
    )
    token_record = result.scalars().first()
    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token.",
        )

    user_res = await db.execute(select(User).where(User.id == token_record.user_id))
    user = user_res.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    user.password_hash = hash_password(request.new_password)
    await db.delete(token_record)
    await db.commit()

    return MsgResponse(message="Password has been successfully updated.")

