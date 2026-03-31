from typing import Any, Generator

import pytest
from sqlalchemy import (
    Integer,
    String,
    func,
    select,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    MappedAsDataclass,
    mapped_column,
    sessionmaker,
)
from starlette.applications import Starlette
from starlette.testclient import TestClient

from sqladmin import Admin, ModelView
from tests.common import sync_engine

session_maker = sessionmaker(bind=sync_engine)
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
admin = Admin(app=app, engine=sync_engine)
admin.add_model_view(UserAdmin)


@pytest.fixture
def prepare_database() -> Generator[None, None, None]:
    Base.metadata.create_all(sync_engine)
    yield
    Base.metadata.drop_all(sync_engine)


@pytest.fixture
def client(prepare_database: Any) -> Generator[TestClient, None, None]:
    with TestClient(app=app, base_url="http://testserver") as c:
        yield c


def test_sync_create_dataclass(client: TestClient) -> None:
    client.post("/admin/user/create", data={"name": "foo", "email": "bar"})
    stmt = select(func.count(User.id))
    with session_maker() as s:
        result = s.execute(stmt)
    assert result.scalar_one() == 1
