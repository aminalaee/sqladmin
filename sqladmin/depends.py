from typing import Optional

from fast_tmp.apps.exceptions import credentials_exception
from fast_tmp.conf import settings
from fast_tmp.db import get_db_session
from fast_tmp.models import User
from fast_tmp.schemas import LoginSchema
from fast_tmp.utils.token import decode_access_token
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=settings.FAST_TMP_URL + "/auth/token")


async def get_username(token: str = Depends(oauth2_scheme)) -> str:
    """
    从token获取username
    """
    try:
        payload = decode_access_token(token)
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    return username


async def get_user(
    username: str = Depends(get_username),
    session: AsyncSession = Depends(get_db_session),
) -> Optional[User]:
    """
    从数据库读取数据
    """
    async with session.begin():
        res = await session.execute(
            select(User).where(User.username == username).limit(1)
        )
        ret = res.scalar_one_or_none()
    return ret


async def _get_user(
    session: AsyncSession,
    username: str = Depends(get_username),
) -> Optional[User]:
    """
    从数据库读取数据
    """
    res = await session.execute(select(User).where(User.username == username).limit(1))
    return res.scalar_one_or_none()


async def authenticate_user(
    logininfo: LoginSchema, session: AsyncSession = Depends(get_db_session)
) -> Optional[User]:
    """
    验证密码
    """
    user = await _get_user(
        session,
        logininfo.username,
    )
    if not user:
        return None
    if not user.verify_password(logininfo.password):
        return None
    return user


async def get_current_user(
    user: Optional[User] = Depends(get_user),
) -> User:
    """
    获取存在的用户
    """
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)):
    """
    获取活跃的用户
    """
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user
