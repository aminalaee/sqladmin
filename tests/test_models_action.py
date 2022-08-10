from typing import Any, Generator

import pytest
from sqlalchemy import Column, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
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
    @action(name="approve", add_in_detail=True, add_in_list=True)
    async def approve_user(self, request: Request):
        model = await self.get_model_by_pk(request.path_params["pk"])

        return JSONResponse({"user_id": model.id})

    @action(
        name="send_notification",
        label="Send Notification",
        confirmation_message="Are you sure to send a notification ? ",
        add_in_detail=False,
        add_in_list=True,
    )
    async def send_notification_user(self, request: Request):
        model = await self.get_model_by_pk(request.path_params["pk"])

        detail_url = self._url_for_details(model)
        return Response(
            content=detail_url
        )  # redirect to a specific url / use None to return to same page


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

    assert admin.views[0]._custom_actions_in_list == {
        "approve": "approve",
        "send_notification": "Send Notification",
    }

    assert admin.views[0]._custom_actions_in_detail == {"approve": "approve"}

    assert admin.views[0]._custom_actions_confirmation == {
        "send_notification": "Are you sure to send a notification ? "
    }

    with Session() as session:
        user = User()
        session.add(user)
        session.commit()

        url_approve = UserAdmin()._url_for_action(user, "approve")
        url_notification = UserAdmin()._url_for_action(user, "send_notification")

    assert url_approve == "/admin/user/action/1/approve"
    assert url_notification == "/admin/user/action/1/send_notification"

    response = client.get("/admin/user/action/1/approve")
    assert response.status_code == 200
    assert response.json() == {"user_id": 1}

    response = client.get("/admin/user/action/1/send_notification")
    assert response.status_code == 200
    assert response.text == "/admin/user/details/1"

    response = client.get("/admin/user/list")
    assert response.text.count("Are you sure to send a notification") == 1
