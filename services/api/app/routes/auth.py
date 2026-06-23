from __future__ import annotations

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.apple import validate_apple_identity_token
from app.auth.google import validate_google_id_token
from app.auth.jwt import decode, encode_access, encode_refresh
from app.db.session import get_db
from app.schemas.auth import (
    AppleSignInRequest,
    AuthResponse,
    GoogleSignInRequest,
    TokenPair,
    TokenRefreshRequest,
    UserCreate,
    UserLogin,
    UserOut,
)
from app.services.user_service import (
    authenticate,
    create_local_user,
    get_or_create_apple_user,
    get_or_create_google_user,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])
_logger = structlog.get_logger()


def _user_out(user: object) -> UserOut:
    from app.db.models.user import User as UserModel

    assert isinstance(user, UserModel)
    return UserOut(
        id=user.id,
        auth_provider=user.auth_provider,
        username=user.username,
        email=user.email,
        display_name=user.display_name,
        avatar_color=user.avatar_color,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )


def _make_token_pair(user_id: object) -> tuple[TokenPair, object]:
    import uuid

    assert isinstance(user_id, uuid.UUID)
    access, access_exp = encode_access(user_id)
    refresh, refresh_exp, _ = encode_refresh(user_id)
    pair = TokenPair(
        access_token=access,
        refresh_token=refresh,
        access_expires_at=access_exp,
        refresh_expires_at=refresh_exp,
    )
    return pair, None


@router.post("/signup", status_code=201, response_model=AuthResponse)
async def signup(
    payload: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthResponse:
    try:
        user = await create_local_user(db, payload)
    except ValueError as exc:
        code = str(exc)
        raise HTTPException(status_code=400, detail={"error_code": code}) from exc

    pair, _ = _make_token_pair(user.id)
    return AuthResponse(user=_user_out(user), tokens=pair)


@router.post("/login", status_code=200, response_model=AuthResponse)
async def login(
    payload: UserLogin,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthResponse:
    try:
        user = await authenticate(db, payload.username, payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail={"error_code": "invalid_credentials"}) from exc

    pair, _ = _make_token_pair(user.id)
    return AuthResponse(user=_user_out(user), tokens=pair)


@router.post("/refresh", status_code=200, response_model=TokenPair)
async def refresh(payload: TokenRefreshRequest) -> TokenPair:
    import uuid

    try:
        claims = decode(payload.refresh_token, expected_type="refresh")
    except ValueError as exc:
        raise HTTPException(status_code=401, detail={"error_code": "invalid_token"}) from exc

    user_id = uuid.UUID(claims.sub)
    access, access_exp = encode_access(user_id)
    ref, refresh_exp, _ = encode_refresh(user_id)
    _logger.info("auth.token_refreshed", user_id=claims.sub)
    return TokenPair(
        access_token=access,
        refresh_token=ref,
        access_expires_at=access_exp,
        refresh_expires_at=refresh_exp,
    )


@router.post("/apple", response_model=AuthResponse)
async def apple_signin(
    payload: AppleSignInRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    response: Response,
) -> AuthResponse:
    try:
        claims = await validate_apple_identity_token(payload.identity_token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail={"error_code": str(exc)}) from exc

    email = payload.email or claims.email
    user, created = await get_or_create_apple_user(
        db,
        apple_sub=claims.sub,
        email=email,
        display_name=payload.display_name,
    )
    response.status_code = 201 if created else 200
    pair, _ = _make_token_pair(user.id)
    return AuthResponse(user=_user_out(user), tokens=pair)


@router.post("/google", response_model=AuthResponse)
async def google_signin(
    payload: GoogleSignInRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    response: Response,
) -> AuthResponse:
    try:
        claims = await validate_google_id_token(payload.id_token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail={"error_code": str(exc)}) from exc

    email = payload.email or claims.email
    user, created = await get_or_create_google_user(
        db,
        google_sub=claims.sub,
        email=email,
        display_name=payload.display_name,
    )
    response.status_code = 201 if created else 200
    pair, _ = _make_token_pair(user.id)
    return AuthResponse(user=_user_out(user), tokens=pair)
