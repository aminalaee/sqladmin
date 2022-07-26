from typing import Any, Generator

import pytest
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.testclient import TestClient

from sqladmin import Admin
from sqladmin.models import BaseView
from tests.common import sync_engine as engine

Base = declarative_base()  # type: Any

Session = sessionmaker(bind=engine)

app = Starlette()
admin = Admin(app=app, engine=engine, templates_dir="tests/tpl")


class CustomAdmin(BaseView):
    def test_page(self, request: Request):
        return self.templates.TemplateResponse(
            "custom.html", context={"request": request}
        )

    name_plural = "Test me"
    icon = "fa-user"
    path = "/custom/test_page"
    methods = ["GET"]
    endpoint = test_page


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app=app, base_url="http://testserver") as c:
        yield c


def test_register_view(client: TestClient) -> None:
    admin.register_view(CustomAdmin)

    url = CustomAdmin().url_path_for(CustomAdmin.name_plural)
    assert url == "/custom/test_page"

    response = client.get("/custom/test_page")

    assert response.status_code == 200
    assert response.text.count("<p>Here I'm going to display some data.</p>") == 1
