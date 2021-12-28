from typing import Any, Generator

import pytest
from sqlalchemy import Column, ForeignKey, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, relationship, sessionmaker
from starlette.applications import Starlette
from starlette.testclient import TestClient

from sqladmin import Admin, ModelAdmin
from tests.common import TEST_DATABASE_URI

Base = declarative_base()  # type: Any

engine = create_engine(TEST_DATABASE_URI, connect_args={"check_same_thread": False})

LocalSession = sessionmaker(bind=engine)

db: Session = LocalSession()

app = Starlette()
admin = Admin(app=app, db=db)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String)

    addresses = relationship("Address", back_populates="user")


class Address(Base):
    __tablename__ = "addresses"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    user = relationship("User", back_populates="addresses")


@pytest.fixture(autouse=True, scope="function")
def prepare_database() -> Generator[None, None, None]:
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


class UserAdmin(ModelAdmin, model=User):
    list_display = [User.id, User.name]


class AddressAdmin(ModelAdmin, model=Address, db=db):
    list_display = ["id", "user_id"]
    name_plural = "Addresses"


admin.register_model(UserAdmin)
admin.register_model(AddressAdmin)


def test_root_view() -> None:
    with TestClient(app) as client:
        response = client.get("/admin")

    assert response.status_code == 200
    assert response.text.count('<span class="nav-link-title">Users</span>') == 1
    assert response.text.count('<span class="nav-link-title">Addresses</span>') == 1


def test_invalid_list_page() -> None:
    with TestClient(app) as client:
        response = client.get("/admin/example/list")

    assert response.status_code == 404


def test_list_view_single_page() -> None:
    for _ in range(5):
        user = User(name="John Doe")
        db.add(user)
        db.commit()

    with TestClient(app) as client:
        response = client.get("/admin/user/list")

    assert response.status_code == 200
    assert (
        "Showing <span>1</span> to <span>5</span> of <span>5</span> items</p>"
        in response.text
    )

    # Next/Previous disabled
    assert response.text.count('<li class="page-item  disabled ">') == 2


def test_list_view_multi_page() -> None:
    for _ in range(45):
        user = User(name="John Doe")
        db.add(user)
        db.commit()

    with TestClient(app) as client:
        response = client.get("/admin/user/list")

    assert response.status_code == 200
    assert (
        "Showing <span>1</span> to <span>10</span> of <span>45</span> items</p>"
        in response.text
    )

    # Previous disabled
    assert response.text.count('<li class="page-item  disabled ">') == 1
    assert response.text.count('<li class="page-item ">') == 1

    with TestClient(app) as client:
        response = client.get("/admin/user/list?page=3")

    assert response.status_code == 200
    assert (
        "Showing <span>21</span> to <span>30</span> of <span>45</span> items</p>"
        in response.text
    )
    assert response.text.count('<li class="page-item ">') == 2

    with TestClient(app) as client:
        response = client.get("/admin/user/list?page=5")

    assert response.status_code == 200
    assert (
        "Showing <span>41</span> to <span>45</span> of <span>45</span> items</p>"
        in response.text
    )

    # Next disabled
    assert response.text.count('<li class="page-item  disabled ">') == 1
    assert response.text.count('<li class="page-item ">') == 1
