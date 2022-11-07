from typing import Any, Generator

import pytest
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.testclient import TestClient

from sqladmin import Admin, BaseView, expose
from tests.common import sync_engine as engine

Base = declarative_base()  # type: Any

Session = sessionmaker(bind=engine)

app = Starlette()
admin = Admin(app=app, engine=engine, templates_dir="tests/templates")


class CustomAdmin(BaseView):
    name = "test"
    icon = "fa fa-test"

    @expose("/custom", methods=["GET"])
    def custom(self, request: Request):
        return self.templates.TemplateResponse(
            "custom.html", context={"request": request}
        )

    @expose("/custom/report")
    def custom_report(self, request: Request):
        return self.templates.TemplateResponse(
            "custom.html", context={"request": request}
        )


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app=app, base_url="http://testserver") as c:
        yield c


def test_base_view(client: TestClient) -> None:
    admin.add_view(CustomAdmin)

    response = client.get("/admin/custom")

    assert response.status_code == 200
    assert response.text.count("<p>Here I'm going to display some data.</p>") == 1

    response = client.get("/admin/custom/report")
    assert response.status_code == 200
