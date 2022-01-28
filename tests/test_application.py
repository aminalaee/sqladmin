from typing import Any, Generator

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker
from starlette.applications import Starlette
from starlette.testclient import TestClient

from sqladmin import Admin
from sqladmin.auth.hashers import make_password
from sqladmin.auth.models import Base as AdminBase, User as AdminUser
from tests import get_test_token
from tests.common import TEST_DATABASE_URI_SYNC

Base = declarative_base()  # type: Any

engine = create_engine(
    TEST_DATABASE_URI_SYNC, connect_args={"check_same_thread": False}
)

LocalSession = sessionmaker(bind=engine)

session: Session = LocalSession()

app = Starlette()


@pytest.fixture(autouse=True, scope="function")
def prepare_database() -> Generator[None, None, None]:
    Base.metadata.create_all(engine)
    AdminBase.metadata.create_all(engine)
    res = session.execute(
        select(AdminUser).where(AdminUser.username == "root_sync").limit(1)
    )
    if not res.scalar_one_or_none():
        user = AdminUser(
            username="root_sync", is_active=True, password=make_password("root")
        )
        session.add(user)
        session.commit()
    yield
    Base.metadata.drop_all(engine)
    AdminBase.metadata.drop_all(engine)


def test_application_title() -> None:
    Admin(app=app, engine=engine)

    with TestClient(app) as client:
        client.cookies.setdefault("access_token", get_test_token("root_sync"))

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
        client.cookies.setdefault("access_token", get_test_token("root_sync"))
        response = client.get("/dashboard")

    assert response.status_code == 200
    assert (
        '<img src="https://example.com/logo.svg" width="64" height="64"'
        in response.text
    )
