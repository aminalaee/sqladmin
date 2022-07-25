from typing import Any, Generator

import pytest
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from starlette.applications import Starlette
from starlette.requests import Request

from sqladmin import Admin
from sqladmin.models import BaseView
from tests.common import sync_engine as engine

Base = declarative_base()  # type: Any

Session = sessionmaker(bind=engine)

app = Starlette()
admin = Admin(app=app, engine=engine)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String)

    addresses = relationship("Address", back_populates="user")
    profile = relationship("Profile", back_populates="user", uselist=False)


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


@pytest.fixture(autouse=True)
def prepare_database() -> Generator[None, None, None]:
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


def test_register_view() -> None:
    admin = Admin(app=Starlette(), engine=engine)
    admin.register_view(CustomAdmin)

    url = CustomAdmin().url_path_for(CustomAdmin.name_plural)
    assert url == "/custom/test_page"
