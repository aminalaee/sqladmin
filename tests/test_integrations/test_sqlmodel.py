from typing import Any, AsyncGenerator, Optional, List
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import sessionmaker
from sqlmodel import Field, Session, SQLModel, Relationship

from sqladmin.forms import get_model_form
from tests.common import sync_engine as engine

pytestmark = pytest.mark.anyio

LocalSession = sessionmaker(bind=engine, class_=Session)

session: Session = LocalSession()


class Team(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    headquarters: str

    heroes: List["Hero"] = Relationship()


class Hero(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    uuid: UUID = Field(default_factory=uuid4)
    name: str = Field(index=True, max_length=5)
    secret_name: str
    age: Optional[int] = None

    team_id: Optional[int] = Field(default=None, foreign_key="team.id")
    team: Optional[Team] = Relationship()


@pytest.fixture
def prepare_database() -> AsyncGenerator[None, None]:
    SQLModel.metadata.create_all(engine)
    yield
    SQLModel.metadata.drop_all(engine)


@pytest.fixture
async def client(prepare_database: Any) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(base_url="http://testserver") as c:
        yield c


async def test_model_form_converter(client: AsyncClient) -> None:
    hero_form = await get_model_form(model=Hero, engine=engine)

    assert "age" in hero_form()._fields
    assert "team" in hero_form()._fields

    team_form = await get_model_form(model=Team, engine=engine)

    assert "headquarters" in team_form()._fields
    assert "heroes" in team_form()._fields
