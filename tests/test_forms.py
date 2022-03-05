import enum
from typing import Any, AsyncGenerator

import pytest
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    TypeDecorator,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

from sqladmin.forms import get_model_form
from tests.common import async_engine as engine

pytestmark = pytest.mark.anyio

Base = declarative_base()  # type: Any

LocalSession = sessionmaker(bind=engine, class_=AsyncSession)

session: AsyncSession = LocalSession()


class Status(enum.Enum):
    REGISTERED = 1
    ACTIVE = 2


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String(32), default="SQLAdmin")
    email = Column(String, nullable=False)
    bio = Column(Text)
    active = Column(Boolean)
    registered_at = Column(DateTime)
    status = Column(Enum(Status))
    balance = Column(Numeric)
    number = Column(Integer)

    addresses = relationship("Address", back_populates="user")


class Address(Base):
    __tablename__ = "addresses"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    user = relationship("User", back_populates="addresses")


@pytest.fixture(autouse=True, scope="function")
async def prepare_database() -> AsyncGenerator[None, None]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def test_model_form_converter_exception() -> None:
    class CustomType(TypeDecorator):
        impl = String

    class Example(User):
        data = Column(CustomType)

    with pytest.raises(Exception):
        await get_model_form(model=Example, engine=engine)


async def test_model_form_converter_with_default() -> None:
    class Point(Base):
        __tablename__ = "points"

        id = Column(Integer, primary_key=True)
        user = User()

    await get_model_form(model=Point, engine=engine)


async def test_model_form_only() -> None:
    Form = await get_model_form(model=User, engine=engine, only=["status"])
    assert len(Form()._fields) == 1


async def test_model_form_exclude() -> None:
    Form = await get_model_form(model=User, engine=engine, exclude=["status"])
    assert len(Form()._fields) == 8
