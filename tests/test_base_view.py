from typing import Generator

import pytest
from sqlalchemy.orm import declarative_base
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.testclient import TestClient

from sqladmin_async import Admin, BaseView, expose
from tests.common import sync_engine as engine

Base = declarative_base()  # type: ignore

app = Starlette()
admin = Admin(app=app, engine=engine, templates_dir="tests/templates")


class CustomAdmin(BaseView):
    name = "test"
    icon = "fa fa-test"

    @expose("/custom", methods=["GET"])
    async def custom(self, request: Request):
        return await self.templates.TemplateResponse(request, "custom.html")

    @expose("/custom/report")
    async def custom_report(self, request: Request):
        return await self.templates.TemplateResponse(request, "custom.html")


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app=app, base_url="http://testserver") as c:
        yield c


def test_base_view(client: TestClient) -> None:
    admin.add_view(CustomAdmin)

    response = client.get("/admin/custom")

    assert response.status_code == 200
    assert "<p>Here I'm going to display some data.</p>" in response.text

    response = client.get("/admin/custom/report")
    assert response.status_code == 200
