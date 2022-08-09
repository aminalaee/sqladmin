from typing import Any, Generator

import pytest
from sqlalchemy import Column, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.testclient import TestClient

from sqladmin import Admin, ModelView
from sqladmin.application import action
from tests.common import sync_engine as engine

Base = declarative_base()  # type: Any

Session = sessionmaker(bind=engine)

app = Starlette()
admin = Admin(app=app, engine=engine)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)


class UserAdmin(ModelView, model=User):
    @action(name="Trigger", add_in_detail=True, add_in_list=True)
    async def action_on_user(self, request: Request):
        model = await self.get_model_by_pk(request.path_params["pk"])

        return JSONResponse({"user_id": model.id})


@pytest.fixture(autouse=True)
def prepare_database() -> Generator[None, None, None]:
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app=app, base_url="http://testserver") as c:
        yield c


def test_model_action(client: TestClient) -> None:
    admin.add_view(UserAdmin)

    assert UserAdmin.custom_actions_in_list == ["Trigger"]
    assert UserAdmin.custom_actions_in_detail == ["Trigger"]

    with Session() as session:
        user = User()
        session.add(user)
        session.commit()

        url = UserAdmin()._url_for_action(user, "Trigger")

    assert url == "/admin/user/action/1/Trigger"

    response = client.get("/admin/user/action/1/Trigger")
    assert response.status_code == 200
    assert response.json() == {"user_id": 1}
