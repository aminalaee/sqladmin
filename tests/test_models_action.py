from typing import Any, Generator, List
from unittest.mock import Mock

import pytest
from sqlalchemy import Column, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response
from starlette.testclient import TestClient

from sqladmin import Admin, ModelView
from sqladmin.application import action
from tests.common import sync_engine as engine

Base: Any = declarative_base()

Session = sessionmaker(bind=engine)

app = Starlette()
admin = Admin(app=app, engine=engine)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)

    def __repr__(self) -> str:
        return f"User: {self.id}"


class UserAdmin(ModelView, model=User):
    async def _action_stub(self, request: Request) -> Response:
        pks = request.query_params.get("pks", "")

        obj_strs: List[str] = []
        for pk in pks.split(","):
            obj = await self.get_object_for_edit(pk)

            obj_strs.append(repr(obj))

        response = RedirectResponse(
            request.url_for("admin:list", identity=self.identity)
        )
        response.headers["X-Objs"] = ",".join(obj_strs)
        return response

    @action(name="detail", add_in_detail=True, add_in_list=False)
    async def action_detail(self, request: Request) -> Response:
        return await self._action_stub(request)  # pragma: no cover

    @action(name="list", add_in_detail=False, add_in_list=True)
    async def action_list(self, request: Request) -> Response:
        return await self._action_stub(request)  # pragma: no cover

    @action(name="detail_list", add_in_detail=True, add_in_list=True)
    async def action_detail_list(self, request: Request) -> Response:
        return await self._action_stub(request)  # pragma: no cover

    @action(
        name="detail_confirm",
        confirmation_message="!Detail Confirm?!",
        add_in_detail=True,
        add_in_list=False,
    )
    async def action_detail_confirm(self, request: Request) -> Response:
        return await self._action_stub(request)  # pragma: no cover

    @action(
        name="list_confirm",
        confirmation_message="!List Confirm?!",
        add_in_detail=False,
        add_in_list=True,
    )
    async def action_list_confirm(self, request: Request) -> Response:
        return await self._action_stub(request)  # pragma: no cover

    @action(
        name="detail_list_confirm",
        confirmation_message="!Detail List Confirm?!",
        add_in_detail=True,
        add_in_list=True,
    )
    async def action_detail_list_confirm(self, request: Request) -> Response:
        return await self._action_stub(request)  # pragma: no cover

    @action(
        name="label_detail", label="Label Detail", add_in_detail=True, add_in_list=False
    )
    async def action_label_detail(self, request: Request) -> Response:
        return await self._action_stub(request)  # pragma: no cover

    @action(
        name="label_list", label="Label List", add_in_detail=False, add_in_list=True
    )
    async def action_label_list(self, request: Request) -> Response:
        return await self._action_stub(request)  # pragma: no cover

    @action(
        name="label_detail_list",
        label="Label Detail List",
        add_in_detail=True,
        add_in_list=True,
    )
    async def action_label_detail_list(self, request: Request) -> Response:
        return await self._action_stub(request)  # pragma: no cover

    @action(
        name="label_detail_confirm",
        label="Label Detail Confirm",
        confirmation_message="!Label Detail Confirm?!",
        add_in_detail=True,
        add_in_list=False,
    )
    async def action_label_detail_confirm(self, request: Request) -> Response:
        return await self._action_stub(request)  # pragma: no cover

    @action(
        name="label_list_confirm",
        label="Label List Confirm",
        confirmation_message="!Label List Confirm?!",
        add_in_detail=False,
        add_in_list=True,
    )
    async def action_label_list_confirm(self, request: Request) -> Response:
        return await self._action_stub(request)  # pragma: no cover

    @action(
        name="label_detail_list_confirm",
        label="Label Detail List Confirm",
        confirmation_message="!Label Detail List Confirm?!",
        add_in_detail=True,
        add_in_list=True,
    )
    async def action_label_detail_list_confirm(self, request: Request) -> Response:
        return await self._action_stub(request)  # pragma: no cover


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
        "list": "list",
        "detail_list": "detail_list",
        "label_list": "Label List",
        "label_detail_list": "Label Detail List",
        "list_confirm": "list_confirm",
        "detail_list_confirm": "detail_list_confirm",
        "label_list_confirm": "Label List Confirm",
        "label_detail_list_confirm": "Label Detail List Confirm",
    }

    assert admin.views[0]._custom_actions_in_detail == {
        "detail": "detail",
        "detail_confirm": "detail_confirm",
        "detail_list": "detail_list",
        "detail_list_confirm": "detail_list_confirm",
        "label_detail": "Label Detail",
        "label_detail_confirm": "Label Detail Confirm",
        "label_detail_list": "Label Detail List",
        "label_detail_list_confirm": "Label Detail List Confirm",
    }

    assert admin.views[0]._custom_actions_confirmation == {
        "detail_confirm": "!Detail Confirm?!",
        "detail_list_confirm": "!Detail List Confirm?!",
        "label_detail_confirm": "!Label Detail Confirm?!",
        "label_detail_list_confirm": "!Label Detail List Confirm?!",
        "label_list_confirm": "!Label List Confirm?!",
        "list_confirm": "!List Confirm?!",
    }

    request = Mock(Request)
    request.url_for = Mock()

    admin.views[0]._url_for_action(request, "test")
    request.url_for.assert_called_with("admin:user-test", identity="user")

    with Session() as session:
        user1 = User()
        user2 = User()
        session.add(user1)
        session.add(user2)
        session.commit()

        response = client.get(
            f"/admin/user/action/detail?pks={user1.id},{user2.id}",
            follow_redirects=False,
        )
        assert response.status_code == 307
        assert f"User: {user1.id}" in response.headers["X-Objs"]
        assert f"User: {user2.id}" in response.headers["X-Objs"]

        response = client.get("/admin/user/list")
        assert response.text.count("!Detail Confirm?!") == 0
        assert response.text.count("!List Confirm?!") == 1
        assert response.text.count("!Detail List Confirm?!") == 1
        assert response.text.count("!Label Detail Confirm?!") == 0
        assert response.text.count("!Label List Confirm?!") == 1
        assert response.text.count("!Label Detail List Confirm?!") == 1

        response = client.get(f"/admin/user/details/{user1.id}")
        assert response.text.count("!Detail Confirm?!") == 1
        assert response.text.count("!List Confirm?!") == 0
        assert response.text.count("!Detail List Confirm?!") == 1
        assert response.text.count("!Label Detail Confirm?!") == 1
        assert response.text.count("!Label List Confirm?!") == 0
        assert response.text.count("!Label Detail List Confirm?!") == 1
