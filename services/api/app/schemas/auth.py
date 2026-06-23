from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=False)


class UserCreate(_Model):
    username: str = Field(min_length=3, max_length=32, pattern=r"^[A-Za-z0-9_-]+$")
    password: str = Field(min_length=8, max_length=128)
    email: EmailStr | None = None
    display_name: str | None = Field(default=None, min_length=1, max_length=80)


class UserLogin(_Model):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8, max_length=128)


class TokenPair(_Model):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    access_expires_at: datetime
    refresh_expires_at: datetime


class AuthResponse(_Model):
    user: "UserOut"
    tokens: TokenPair


class TokenRefreshRequest(_Model):
    refresh_token: str


class AppleSignInRequest(_Model):
    identity_token: str
    display_name: str | None = Field(default=None, min_length=1, max_length=80)
    email: EmailStr | None = None


class GoogleSignInRequest(_Model):
    id_token: str
    display_name: str | None = Field(default=None, min_length=1, max_length=80)
    email: EmailStr | None = None


class UserOut(_Model):
    id: UUID
    auth_provider: str
    username: str | None
    email: EmailStr | None
    display_name: str | None
    avatar_color: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    created_at: datetime
    last_login_at: datetime | None


class UserUpdate(_Model):
    display_name: str | None = Field(default=None, min_length=1, max_length=80)
    email: EmailStr | None = None
    avatar_color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")


AuthResponse.model_rebuild()
