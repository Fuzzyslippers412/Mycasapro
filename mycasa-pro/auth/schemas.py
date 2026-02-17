"""
Pydantic schemas for authentication routes.
"""
from __future__ import annotations

import re
from pydantic import BaseModel, Field, validator


USERNAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9._-]{1,28}[A-Za-z0-9]$")


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=6)


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)

    @validator("username")
    def validate_username(cls, value: str) -> str:
        cleaned = value.strip()
        if not USERNAME_PATTERN.match(cleaned):
            raise ValueError(
                "Username must be 3-30 chars, start with a letter, end with a letter/number, "
                "and contain only letters, numbers, '.', '_' or '-'"
            )
        if re.search(r"[._-]{2,}", cleaned):
            raise ValueError("Username cannot contain consecutive separators")
        return cleaned

    @validator("email")
    def normalize_email(cls, value: str) -> str:
        cleaned = value.strip()
        if "@" not in cleaned or "." not in cleaned.split("@")[-1]:
            raise ValueError("Email must be a valid address")
        return cleaned


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=10)


class LogoutRequest(BaseModel):
    refresh_token: str | None = Field(default=None, min_length=10)


class LogoutAllRequest(BaseModel):
    all_devices: bool = True


class ForgotPasswordRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)

    @validator("email")
    def normalize_email(cls, value: str) -> str:
        cleaned = value.strip()
        if "@" not in cleaned or "." not in cleaned.split("@")[-1]:
            raise ValueError("Email must be a valid address")
        return cleaned


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=10)
    new_password: str = Field(..., min_length=8, max_length=128)


class UpdateMeRequest(BaseModel):
    display_name: str | None = Field(default=None, max_length=120)


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    is_admin: bool
    display_name: str | None = None
    status: str | None = None
    org_id: str | None = None
    tenant_id: str | None = None
    avatar_url: str | None = None


class AdminUserResponse(UserResponse):
    roles: list[str] = []


class TokenResponse(BaseModel):
    token: str
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    user: UserResponse


class AdminCreateUserRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., min_length=5, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=128)
    role: str | None = None
    status: str | None = None
    org_id: str | None = None
    send_invite: bool = False


class AdminUpdateUserRequest(BaseModel):
    status: str | None = None
    role: str | None = None
    org_id: str | None = None


class AdminRoleRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)
    description: str | None = None
    scope: str = "global"


class AdminRolePermissionsRequest(BaseModel):
    permissions: list[str] = []


class AdminDBQueryRequest(BaseModel):
    sql: str = Field(..., min_length=1)
    danger_mode: bool = False
