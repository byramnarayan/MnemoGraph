from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field


# User Schemas
class UserBase(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    tenant_slug: str | None = Field(None, max_length=50)
    company_name: str | None = Field(None, max_length=150)
    industry_vertical: str | None = Field(None, max_length=100)
    department: str | None = Field(None, max_length=100)


class UserRegister(UserBase):
    password: str = Field(..., min_length=8, max_length=128)
    role: str = "Executive Admin"


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    full_name: str | None = Field(None, min_length=2, max_length=100)
    company_name: str | None = Field(None, max_length=150)
    industry_vertical: str | None = Field(None, max_length=100)
    department: str | None = Field(None, max_length=100)


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=8, max_length=128)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)


class UserResponse(UserBase):
    id: int
    role: str
    image_file: str | None = None
    image_url: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class MsgResponse(BaseModel):
    message: str

