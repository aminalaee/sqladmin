from pathlib import Path

import jinja2
import pytest
from starlette.datastructures import Headers
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Router


@pytest.fixture()
def templates_path() -> Path:
    return Path(__file__).parent.parent.parent / "sqladmin" / "templates"


@pytest.fixture()
def resources_path(request_without_access: Request) -> Path:
    return Path(__file__).parent / "resources"


@pytest.fixture()
def jinja_env(templates_path: Path) -> jinja2.Environment:
    loader = jinja2.FileSystemLoader(templates_path)
    return jinja2.Environment(loader=loader, autoescape=True, enable_async=True)


@pytest.fixture()
def macros_content(templates_path: Path) -> str:
    with open(templates_path / "_macros.html") as macros:
        return macros.read()


@pytest.fixture()
def request_without_access() -> Request:
    router = Router()
    router.add_route(
        "/{identity}/list",
        lambda request: Response("okay"),
        ["GET"],
        name="admin:list",
    )

    return Request(
        {
            "type": "http",
            "router": router,
            "headers": Headers(),
        }
    )


@pytest.fixture()
def request_with_access(request_without_access: Request) -> Request:
    request_without_access.scope["show_hidden"] = True
    return request_without_access
