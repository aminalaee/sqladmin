from typing import Any

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker
from starlette.applications import Starlette
from starlette.testclient import TestClient

from sqladmin import Admin
from tests.common import sync_engine as engine

Base = declarative_base()  # type: Any

LocalSession = sessionmaker(bind=engine)

session: Session = LocalSession()

app = Starlette()


def test_application_title() -> None:
    Admin(app=app, engine=engine)

    with TestClient(app) as client:
        response = client.get("/admin")

    assert response.status_code == 200
    assert response.text.count("<h3>Admin</h3>") == 1


def test_application_logo() -> None:
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
