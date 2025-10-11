from typing import Any, AsyncGenerator

import pytest
from httpx import AsyncClient
from sqlalchemy import Integer, String, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    MappedAsDataclass,
    mapped_column,
)
from starlette.applications import Starlette

from sqladmin import Admin
from sqladmin.models import ModelView
from tests.common import async_engine

async_session_maker = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

pytestmark = pytest.mark.anyio


class Base(MappedAsDataclass, DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    name: Mapped[str] = mapped_column(String(length=16), init=True)
    email: Mapped[str] = mapped_column(String, unique=True)


class UserAdmin(ModelView, model=User):
    column_list = ["name", "email"]
    column_labels = {"name": "Name", "email": "Email"}


app = Starlette()
async_admin = Admin(app=app, engine=async_engine)
async_admin.add_view(UserAdmin)


@pytest.fixture
async def async_prepare_database() -> AsyncGenerator[None, None]:
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await async_engine.dispose()


@pytest.fixture
async def async_client(
    async_prepare_database: Any,
) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(app=app, base_url="http://testserver") as c:
        yield c


async def test_async_create_dataclass(async_client: AsyncClient) -> None:
    await async_client.post("/admin/user/create", data={"name": "foo", "email": "bar"})
    stmt = select(func.count(User.id))
    async with async_session_maker() as s:
        result = await s.execute(stmt)
    assert result.scalar_one() == 1
