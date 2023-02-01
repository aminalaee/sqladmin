from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from starlette.applications import Starlette
from starlette.datastructures import MutableHeaders
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.testclient import TestClient
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from sqladmin import Admin, ModelView
from tests.common import sync_engine as engine

Base = declarative_base()  # type: ignore

LocalSession = sessionmaker(bind=engine)

session = LocalSession()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String(32), default="SQLAdmin")


def test_application_title() -> None:
    app = Starlette()
    Admin(app=app, engine=engine)

    with TestClient(app) as client:
        response = client.get("/admin")

    assert response.status_code == 200
    assert "<h3>Admin</h3>" in response.text
    assert "<title>Admin</title>" in response.text


def test_application_logo() -> None:
    app = Starlette()
    Admin(
        app=app,
        engine=engine,
        logo_url="https://example.com/logo.svg",
        base_url="/dashboard",
    )

    with TestClient(app) as client:
        response = client.get("/dashboard")

    assert response.status_code == 200
    assert (
        '<img src="https://example.com/logo.svg" width="64" height="64"'
        in response.text
    )


def test_middlewares() -> None:
    class CorrelationIdMiddleware:
        def __init__(self, app: ASGIApp) -> None:
            self.app = app

        async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
            async def send_wrapper(message: Message) -> None:
                if message["type"] == "http.response.start":
                    headers = MutableHeaders(scope=message)
                    headers.append("X-Correlation-ID", "UUID")
                await send(message)

            await self.app(scope, receive, send_wrapper)

    app = Starlette()
    Admin(
        app=app,
        engine=engine,
        middlewares=[Middleware(CorrelationIdMiddleware)],
    )

    with TestClient(app) as client:
        response = client.get("/admin")

    assert response.status_code == 200
    assert "x-correlation-id" in response.headers


def test_get_save_redirect_url():
    app = Starlette()
    admin = Admin(app=app, engine=engine)

    class UserAdmin(ModelView, model=User):
        save_as = True

    admin.add_view(UserAdmin)

    @app.route("/{identity}", methods=["POST"])
    async def index(request: Request):
        obj = User(id=1)
        form_data = await request.form()
        url = admin.get_save_redirect_url(request, form_data, UserAdmin, obj)
        return Response(url)

    client = TestClient(app)

    response = client.post("/user", data={"save": "Save"})
    assert response.text == "http://testserver/admin/user/list"

    response = client.post("/user", data={"save": "Save and continue editing"})
    assert response.text == "http://testserver/admin/user/edit/1"

    response = client.post("/user", data={"save": "Save as new"})
    assert response.text == "http://testserver/admin/user/edit/1"

    response = client.post("/user", data={"save": "Save and add another"})
    assert response.text == "http://testserver/admin/user/create"
