from starlette.applications import Starlette
from starlette.datastructures import MutableHeaders
from starlette.testclient import TestClient
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from sqladmin import Admin
from tests.common import sync_engine as engine


def test_application_title() -> None:
    app = Starlette()
    Admin(app=app, engine=engine)

    with TestClient(app) as client:
        response = client.get("/admin")

    assert response.status_code == 200
    assert response.text.count("<h3>Admin</h3>") == 1
    assert response.text.count("<title>Admin</title>") == 1


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
        middlewares=[CorrelationIdMiddleware],
    )

    with TestClient(app) as client:
        response = client.get("/admin")

    assert response.status_code == 200
    assert "x-correlation-id" in response.headers
