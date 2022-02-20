from typing import Any, Generator

import pytest
from sqlalchemy import (
    Column,
    Date,
    ForeignKey,
    Integer,
    String,
    create_engine,
    func,
    select,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, relationship, sessionmaker
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.testclient import TestClient

from sqladmin import Admin, ModelAdmin
from tests.common import TEST_DATABASE_URI_SYNC

Base = declarative_base()  # type: Any

engine = create_engine(
    TEST_DATABASE_URI_SYNC, connect_args={"check_same_thread": False}
)

LocalSession = sessionmaker(bind=engine)

session: Session = LocalSession()

app = Starlette()
admin = Admin(app=app, engine=engine)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String(length=16))
    email = Column(String)
    birthdate = Column(Date)

    addresses = relationship("Address", back_populates="user")

    def __str__(self) -> str:
        return f"User {self.id}"


class Address(Base):
    __tablename__ = "addresses"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    user = relationship("User", back_populates="addresses")

    def __str__(self) -> str:
        return f"Address {self.id}"


class Movie(Base):
    __tablename__ = "movies"

    id = Column(Integer, primary_key=True)


@pytest.fixture(autouse=True, scope="function")
def prepare_database() -> Generator[None, None, None]:
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


class UserAdmin(ModelAdmin, model=User):
    column_list = [User.id, User.name, User.email, User.addresses]
    column_labels = {User.email: "Email"}


class AddressAdmin(ModelAdmin, model=Address):
    column_list = ["id", "user_id", "user"]
    name_plural = "Addresses"


class MovieAdmin(ModelAdmin, model=Movie):
    can_edit = False
    can_delete = False
    can_view_details = False

    def is_accessible(self, request: Request) -> bool:
        return False

    def is_visible(self, request: Request) -> bool:
        return False


admin.register_model(UserAdmin)
admin.register_model(AddressAdmin)
admin.register_model(MovieAdmin)


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
        session.add(user)
    session.commit()

    with TestClient(app) as client:
        response = client.get("/admin/user/list")

    assert response.status_code == 200
    assert (
        "Showing <span>1</span> to <span>5</span> of <span>5</span> items</p>"
        in response.text
    )

    # Showing active navigation link
    assert (
        '<a class="nav-link active" href="http://testserver/admin/user/list"'
        in response.text
    )

    # Next/Previous disabled
    assert response.text.count('<li class="page-item disabled">') == 2


def test_list_view_multi_page() -> None:
    for _ in range(45):
        user = User(name="John Doe")
        session.add(user)
    session.commit()

    with TestClient(app) as client:
        response = client.get("/admin/user/list")

    assert response.status_code == 200
    assert (
        "Showing <span>1</span> to <span>10</span> of <span>45</span> items</p>"
        in response.text
    )

    # Previous disabled
    assert response.text.count('<li class="page-item disabled">') == 1
    assert response.text.count('<li class="page-item ">') == 5

    with TestClient(app) as client:
        response = client.get("/admin/user/list?page=3")

    assert response.status_code == 200
    assert (
        "Showing <span>21</span> to <span>30</span> of <span>45</span> items</p>"
        in response.text
    )
    assert response.text.count('<li class="page-item ">') == 6

    with TestClient(app) as client:
        response = client.get("/admin/user/list?page=5")

    assert response.status_code == 200
    assert (
        "Showing <span>41</span> to <span>45</span> of <span>45</span> items</p>"
        in response.text
    )

    # Next disabled
    assert response.text.count('<li class="page-item disabled">') == 1
    assert response.text.count('<li class="page-item ">') == 5


def test_list_page_permission_actions() -> None:
    for _ in range(10):
        user = User(name="John Doe")
        session.add(user)
        session.flush()

        address = Address(user_id=user.id)
        session.add(address)

    session.commit()

    with TestClient(app) as client:
        response = client.get("/admin/user/list")

    assert response.status_code == 200
    assert response.text.count('<i class="fas fa-eye"></i>') == 10
    assert response.text.count('<i class="fas fa-trash"></i>') == 10

    with TestClient(app) as client:
        response = client.get("/admin/address/list")

    assert response.status_code == 200
    assert response.text.count('<i class="fas fa-eye"></i>') == 10
    assert response.text.count('<i class="fas fa-pencil"></i>') == 0
    assert response.text.count('<i class="fas fa-trash"></i>') == 10


def test_unauthorized_detail_page() -> None:
    with TestClient(app) as client:
        response = client.get("/admin/movie/details/1")

    assert response.status_code == 403


def test_not_found_detail_page() -> None:
    with TestClient(app) as client:
        response = client.get("/admin/user/details/1")

    assert response.status_code == 404


def test_detail_page() -> None:
    user = User(name="Amin Alaee")
    session.add(user)
    session.flush()

    for _ in range(2):
        address = Address(user_id=user.id)
        session.add(address)
    session.commit()

    with TestClient(app) as client:
        response = client.get("/admin/user/details/1")

    assert response.status_code == 200
    assert response.text.count('<th class="w-1">Column</th>') == 1
    assert response.text.count('<th class="w-1">Value</th>') == 1
    assert response.text.count("<td>id</td>") == 1
    assert response.text.count("<td>1</td>") == 1
    assert response.text.count("<td>name</td>") == 1
    assert response.text.count("<td>Amin Alaee</td>") == 1
    assert response.text.count("<td>addresses</td>") == 1
    assert response.text.count("<td>Address 1, Address 2</td>") == 1

    # Action Buttons
    assert response.text.count("http://testserver/admin/user/list") == 2
    assert response.text.count("Go Back") == 1

    # Delete modal
    assert response.text.count("Cancel") == 1
    assert response.text.count("Delete") == 2


def test_column_labels() -> None:
    user = User(name="Foo")
    session.add(user)
    session.commit()

    with TestClient(app) as client:
        response = client.get("/admin/user/list")

    assert response.status_code == 200
    assert response.text.count("<th>Email</th>") == 1

    with TestClient(app) as client:
        response = client.get("/admin/user/details/1")

    assert response.status_code == 200
    assert response.text.count("<td>Email</td>") == 1


def test_delete_endpoint_unauthorized_response() -> None:
    with TestClient(app) as client:
        response = client.delete("/admin/movie/delete/1")

    assert response.status_code == 403


def test_delete_endpoint_not_found_response() -> None:
    with TestClient(app) as client:
        response = client.delete("/admin/user/delete/1")

    assert response.status_code == 404
    assert session.query(User).count() == 0


def test_delete_endpoint() -> None:
    user = User(name="Bar")
    session.add(user)
    session.commit()

    assert session.query(User).count() == 1

    with TestClient(app) as client:
        response = client.delete("/admin/user/delete/1")

    assert response.status_code == 200
    assert session.query(User).count() == 0


def test_create_endpoint_unauthorized_response() -> None:
    with TestClient(app) as client:
        response = client.get("/admin/movie/create")

    assert response.status_code == 403


def test_create_endpoint_get_form() -> None:
    with TestClient(app) as client:
        response = client.get("/admin/user/create")

    assert response.status_code == 200
    assert (
        '<select class="form-control" id="addresses" multiple name="addresses">'
        in response.text
    )
    assert 'id="name" maxlength="16" name="name" type="text" value="">' in response.text
    assert (
        '<input class="form-control" id="email" name="email" type="text" value="">'
        in response.text
    )


def test_create_endpoint_post_form() -> None:
    data: dict = {"birthdate": "Wrong Date Format"}
    with TestClient(app) as client:
        response = client.post("/admin/user/create", data=data)

    assert response.status_code == 400
    assert (
        '<div class="invalid-feedback">Not a valid date value.</div>' in response.text
    )

    data = {"name": "SQLAlchemy"}
    with TestClient(app) as client:
        response = client.post("/admin/user/create", data=data)

    stmt = select(func.count(User.id))
    assert session.execute(stmt).scalar_one() == 1
    assert response.status_code == 302

    stmt = select(User).limit(1)
    user = session.execute(stmt).scalar_one()
    assert user.name == "SQLAlchemy"
    assert user.email is None
    assert user.addresses == []

    data = {"user": user.id}
    with TestClient(app) as client:
        response = client.post("/admin/address/create", data=data)

    stmt = select(func.count(Address.id))
    assert session.execute(stmt).scalar_one() == 1
    assert response.status_code == 302

    stmt = select(Address).limit(1)
    address = session.execute(stmt).scalar_one()
    assert address.user == user
    assert address.user_id == user.id

    data = {"name": "SQLAdmin", "addresses": [address.id]}
    with TestClient(app) as client:
        response = client.post("/admin/user/create", data=data)

    stmt = select(func.count(User.id))
    assert session.execute(stmt).scalar_one() == 2
    assert response.status_code == 302

    stmt = select(User).offset(1).limit(1)
    user = session.execute(stmt).scalar_one()
    assert user.name == "SQLAdmin"
    assert user.addresses == [address]


def test_list_view_page_size_options() -> None:
    with TestClient(app) as client:
        response = client.get("/admin/user/list")

    assert response.status_code == 200
    assert 'href="http://testserver/admin/user/list?page_size=10' in response.text
    assert 'href="http://testserver/admin/user/list?page_size=25' in response.text
    assert 'href="http://testserver/admin/user/list?page_size=50' in response.text
    assert 'href="http://testserver/admin/user/list?page_size=100' in response.text


def test_is_accessible_method() -> None:
    with TestClient(app) as client:
        response = client.get("/admin/movie/list")

    assert response.status_code == 403


def test_is_visible_method() -> None:
    with TestClient(app) as client:
        response = client.get("/admin")

    assert response.status_code == 200
    assert response.text.count('<span class="nav-link-title">Users</span>') == 1
    assert response.text.count('<span class="nav-link-title">Addresses</span>') == 1
    assert response.text.count("Movie") == 0


def test_edit_endpoint_unauthorized_response() -> None:
    with TestClient(app) as client:
        response = client.get("/admin/movie/edit/1")

    assert response.status_code == 403


def test_not_found_edit_page() -> None:
    with TestClient(app) as client:
        response = client.get("/admin/user/edit/1")

    assert response.status_code == 404


def test_update_get_page() -> None:
    user = User(name="Joe")
    session.add(user)
    session.flush()

    address = Address(user=user)
    session.add(address)
    session.commit()

    with TestClient(app) as client:
        response = client.get("/admin/user/edit/1")

    assert response.status_code == 200
    assert (
        response.text.count(
            '<select class="form-control" id="addresses" multiple name="addresses">'
        )
        == 1
    )
    assert response.text.count('<option selected value="1">Address 1</option>') == 1
    assert (
        response.text.count(
            'id="name" maxlength="16" name="name" type="text" value="Joe">'
        )
        == 1
    )

    with TestClient(app) as client:
        response = client.get("/admin/address/edit/1")

    assert response.text.count('<select class="form-control" id="user" name="user">')
    assert response.text.count('<option value="__None"></option>')
    assert response.text.count('<option selected value="1">User 1</option>')


def test_update_submit_form() -> None:
    user = User(name="Joe")
    session.add(user)
    session.flush()

    address = Address(user=user)
    session.add(address)
    session.commit()

    with TestClient(app) as client:
        data = {"name": "Jack"}
        response = client.post("/admin/user/edit/1", data=data)

    assert response.status_code == 302

    session.refresh(user)
    assert user.name == "Jack"
    assert user.addresses == []

    with TestClient(app) as client:
        data = {"name": "Jack", "addresses": address.id}
        response = client.post("/admin/user/edit/1", data=data)

    session.refresh(user)
    assert user.name == "Jack"
    assert user.addresses == [address]

    with TestClient(app) as client:
        data = {"name": "Jack" * 10}
        response = client.post("/admin/user/edit/1", data=data)

    assert response.status_code == 400
