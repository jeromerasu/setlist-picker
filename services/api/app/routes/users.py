from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import current_user
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.auth import UserOut, UserUpdate
from app.schemas.groups import MyGroupListResponse
from app.services.group_service import list_my_groups
from app.services.user_service import patch_user

router = APIRouter(prefix="/api/users", tags=["users"])


def _user_out(user: User) -> UserOut:
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


@router.get("/me", response_model=UserOut)
async def get_me(
    caller: Annotated[User, Depends(current_user)],
) -> UserOut:
    return _user_out(caller)


@router.get("/me/groups", response_model=MyGroupListResponse)
async def get_my_groups(
    caller: Annotated[User, Depends(current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MyGroupListResponse:
    return await list_my_groups(db, caller)


@router.patch("/me", response_model=UserOut)
async def patch_me(
    payload: UserUpdate,
    caller: Annotated[User, Depends(current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserOut:
    try:
        user = await patch_user(db, caller, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"error_code": str(exc)}) from exc
    return _user_out(user)
