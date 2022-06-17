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
)
from sqlalchemy.dialects.postgresql import INET, MACADDR, UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy_utils import EmailType, IPAddressType, UUIDType
from wtforms import Field, Form, StringField

from sqladmin import ModelAdmin
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


@pytest.fixture(autouse=True)
async def prepare_database() -> AsyncGenerator[None, None]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


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


async def test_model_form_form_args() -> None:
    form_args = {"name": {"label": "User Name"}}
    Form = await get_model_form(model=User, engine=engine, form_args=form_args)
    assert Form()._fields["name"].label.text == "User Name"


async def test_model_form_column_label() -> None:
    labels = {"name": "User Name"}
    Form = await get_model_form(model=User, engine=engine, column_labels=labels)
    assert Form()._fields["name"].label.text == "User Name"


@pytest.mark.filterwarnings("ignore:^Dialect sqlite\\+aiosqlite.*$")
async def test_model_form_column_label_precedence() -> None:
    # Validator takes precedence over label.
    form_args_user = {"name": {"label": "User Name (Use Me)"}}
    labels_user = {"name": "User Name (Do Not Use Me)"}
    Form = await get_model_form(
        model=User, engine=engine, form_args=form_args_user, column_labels=labels_user
    )
    assert Form()._fields["name"].label.text == "User Name (Use Me)"

    # If there are form args, but no "label", then read from labels mapping.
    form_args_user = {"user": {}}
    labels_user = {"user": "User (Use Me)"}
    Form = await get_model_form(
        model=Address,
        engine=engine,
        form_args=form_args_user,
        column_labels=labels_user,
    )
    assert Form()._fields["user"].label.text == "User (Use Me)"


async def test_model_form_override() -> None:
    class ExampleField(Field):
        pass

    Form = await get_model_form(
        model=User, engine=engine, form_overrides={"name": ExampleField}
    )
    assert isinstance(Form()._fields["name"], ExampleField)
    assert not isinstance(Form()._fields["email"], ExampleField)


@pytest.mark.skipif(engine.name != "postgresql", reason="PostgreSQL only")
async def test_model_form_postgresql() -> None:
    class PostgresModel(Base):
        __tablename__ = "postgres_model"

        id = Column(Integer, primary_key=True)
        uuid = Column(UUID)
        ip = Column(INET)
        mac = Column(MACADDR)

    Form = await get_model_form(model=PostgresModel, engine=engine)
    assert len(Form()._fields) == 3


async def test_model_form_sqlalchemy_utils() -> None:
    class SQLAlchemyUtilsModel(Base):
        __tablename__ = "sqlalchemy_utils_model"

        id = Column(Integer, primary_key=True)
        email = Column(EmailType)
        ip = Column(IPAddressType)
        uuid = Column(UUIDType)

    Form = await get_model_form(model=SQLAlchemyUtilsModel, engine=engine)
    assert len(Form()._fields) == 3


async def test_form_override_scaffold() -> None:
    class MyForm(Form):
        foo = StringField("Foo")

    class UserAdmin(ModelAdmin, model=User):
        form = MyForm

    form_type = await UserAdmin().scaffold_form()
    form = form_type()
    assert isinstance(form, MyForm)
    assert len(form._fields) == 1
    assert "foo" in form._fields
