from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=False)


class UserCreate(_Model):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str | None = Field(default=None, min_length=1, max_length=80)

    @field_validator("email", mode="before")
    @classmethod
    def lowercase_email(cls, v: object) -> object:
        if isinstance(v, str):
            return v.lower()
        return v


class UserLogin(_Model):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email", mode="before")
    @classmethod
    def lowercase_email(cls, v: object) -> object:
        if isinstance(v, str):
            return v.lower()
        return v


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
