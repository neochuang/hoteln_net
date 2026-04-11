import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from typing import Union

import bcrypt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.api_key import ApiKey
from app.models.user import User, UserRole
from app.services.auth import decode_token

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = decode_token(credentials.credentials)
    if payload is None or payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    return user


def require_role(*roles: UserRole):
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return current_user
    return role_checker


async def get_api_key(
    x_api_key: str = Header(...),
    db: AsyncSession = Depends(get_db),
) -> ApiKey:
    result = await db.execute(select(ApiKey).where(ApiKey.is_active == True))
    api_keys = result.scalars().all()
    for key in api_keys:
        if bcrypt.checkpw(x_api_key.encode(), key.key_hash.encode()):
            key.last_used_at = datetime.now(timezone.utc)
            await db.commit()
            await db.refresh(key)
            return key
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")


async def get_device_or_user(
    x_api_key: str | None = Header(None),
    credentials: HTTPAuthorizationCredentials | None = Depends(HTTPBearer(auto_error=False)),
    db: AsyncSession = Depends(get_db),
) -> Union[ApiKey, User]:
    if x_api_key:
        return await get_api_key(x_api_key=x_api_key, db=db)
    if credentials:
        return await get_current_user(credentials=credentials, db=db)
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
