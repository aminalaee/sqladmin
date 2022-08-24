from typing import Generator

import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.testclient import TestClient

from sqladmin import Admin
from sqladmin.authentication import AuthenticationBackend
from tests.common import sync_engine as engine


class CustomBackend(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        if form["username"] != "a":
            return False

        request.session.update({"token": "amin"})
        return True

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        print("!")
        return "token" in request.session


app = Starlette()
authentication_backend = CustomBackend(secret_key="sqladmin")
admin = Admin(app=app, engine=engine, authentication_backend=authentication_backend)


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app=app, base_url="http://testserver") as c:
        yield c


def test_access_logion_required_views(client: TestClient) -> None:
    response = client.get("/admin/")
    assert response.url == "http://testserver/admin/login"

    response = client.get("/admin/users/list")
    assert response.url == "http://testserver/admin/login"


def test_login_failure(client: TestClient) -> None:
    response = client.post("/admin/login", data={"username": "x", "password": "b"})

    assert response.status_code == 400
    assert response.url == "http://testserver/admin/login"


def test_login(client: TestClient) -> None:
    response = client.post("/admin/login", data={"username": "a", "password": "b"})

    assert len(response.cookies) == 1
    assert response.status_code == 302


def test_logout(client: TestClient) -> None:
    response = client.get("/admin/logout", data={"username": "a", "password": "b"})

    assert len(response.cookies) == 0
    assert response.status_code == 200
    assert response.url == "http://testserver/admin/login"
