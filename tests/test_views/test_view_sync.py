import enum
from typing import Any, Generator

import pytest
from sqlalchemy import (
    JSON,
    Column,
    Date,
    Enum,
    ForeignKey,
    Integer,
    String,
    func,
    select,
)
from sqlalchemy.orm import declarative_base, relationship, selectinload, sessionmaker
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.testclient import TestClient

from sqladmin import Admin, ModelView
from tests.common import sync_engine as engine

Base = declarative_base()  # type: Any
session_maker = sessionmaker(bind=engine)

app = Starlette()
admin = Admin(app=app, engine=engine)


class Status(enum.Enum):
    ACTIVE = "ACTIVE"
    DEACTIVE = "DEACTIVE"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String(length=16))
    email = Column(String, unique=True)
    birthdate = Column(Date)
    status = Column(Enum(Status), default=Status.ACTIVE)
    meta_data = Column(JSON)

    addresses = relationship("Address", back_populates="user")
    profile = relationship("Profile", back_populates="user", uselist=False)

    addresses_formattable = relationship("AddressFormattable", back_populates="user")
    profile_formattable = relationship(
        "ProfileFormattable", back_populates="user", uselist=False
    )

    def __str__(self) -> str:
        return f"User {self.id}"


class Address(Base):
    __tablename__ = "addresses"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    user = relationship("User", back_populates="addresses")

    def __str__(self) -> str:
        return f"Address {self.id}"


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)

    user = relationship("User", back_populates="profile")

    def __str__(self) -> str:
        return f"Profile {self.id}"


class AddressFormattable(Base):
    __tablename__ = "addresses_formattable"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    user = relationship("User", back_populates="addresses_formattable")

    def __str__(self) -> str:
        return f"Address {self.id}"


class ProfileFormattable(Base):
    __tablename__ = "profiles_formattable"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)

    user = relationship("User", back_populates="profile_formattable")

    def __str__(self) -> str:
        return f"Profile {self.id}"


class Movie(Base):
    __tablename__ = "movies"

    id = Column(Integer, primary_key=True)


@pytest.fixture
def prepare_database() -> Generator[None, None, None]:
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def client(prepare_database: Any) -> Generator[TestClient, None, None]:
    with TestClient(app=app, base_url="http://testserver") as c:
        yield c


class UserAdmin(ModelView, model=User):
    column_list = [
        User.id,
        User.name,
        User.email,
        User.addresses,
        User.profile,
        User.addresses_formattable,
        User.profile_formattable,
        User.status,
    ]
    column_labels = {User.email: "Email"}
    column_searchable_list = [User.name]
    column_sortable_list = [User.id]
    column_export_list = [User.name, User.status]
    column_formatters = {
        User.addresses_formattable: lambda m, a: [
            f"Formatted {a}" for a in m.addresses_formattable
        ],
        User.profile_formattable: lambda m, a: f"Formatted {m.profile_formattable}",
    }
    column_formatters_detail = {
        User.addresses_formattable: lambda m, a: [
            f"Formatted {a}" for a in m.addresses_formattable
        ],
        User.profile_formattable: lambda m, a: f"Formatted {m.profile_formattable}",
    }
    save_as = True


class AddressAdmin(ModelView, model=Address):
    column_list = ["id", "user_id", "user", "user.profile.id"]
    name_plural = "Addresses"
    export_max_rows = 3


class ProfileAdmin(ModelView, model=Profile):
    column_list = ["id", "user_id", "user"]


class MovieAdmin(ModelView, model=Movie):
    can_edit = False
    can_delete = False
    can_view_details = False

    def is_accessible(self, request: Request) -> bool:
        return False

    def is_visible(self, request: Request) -> bool:
        return False


admin.add_view(UserAdmin)
admin.add_view(AddressAdmin)
admin.add_view(ProfileAdmin)
admin.add_view(MovieAdmin)


def test_root_view(client: TestClient) -> None:
    response = client.get("/admin")

    assert response.status_code == 200
    assert '<span class="nav-link-title">Users</span>' in response.text
    assert '<span class="nav-link-title">Addresses</span>' in response.text


def test_invalid_list_page(client: TestClient) -> None:
    response = client.get("/admin/example/list")

    assert response.status_code == 404


def test_list_view_single_page(client: TestClient) -> None:
    with session_maker() as session:
        for _ in range(5):
            user = User(name="John Doe")
            session.add(user)
        session.commit()

    response = client.get("/admin/user/list")

    assert response.status_code == 200

    # Showing active navigation link
    assert (
        '<a class="nav-link active" href="http://testserver/admin/user/list"'
        in response.text
    )

    # Next/Previous disabled
    assert response.text.count('<li class="page-item disabled">') == 2


def test_list_view_with_relationships(client: TestClient) -> None:
    with session_maker() as session:
        for _ in range(5):
            user = User(name="John Doe")
            user.addresses.append(Address())
            user.profile = Profile()
            session.add(user)
        session.commit()

    response = client.get("/admin/user/list")

    assert response.status_code == 200

    # Show values of relationships
    assert (
        '<a href="http://testserver/admin/address/details/1">(Address 1)</a>'
        in response.text
    )
    assert (
        '<a href="http://testserver/admin/profile/details/1">Profile 1</a>'
        in response.text
    )


def test_list_view_with_formatted_relationships(client: TestClient) -> None:
    with session_maker() as session:
        for _ in range(5):
            user = User(name="John Doe")
            user.addresses_formattable.append(AddressFormattable())
            user.profile_formattable = ProfileFormattable()
            session.add(user)
        session.commit()

    response = client.get("/admin/user/list")

    assert response.status_code == 200

    # Show formatted values of relationships
    assert "(Formatted Address 1)" in response.text
    assert "Formatted Profile 1" in response.text


def test_list_view_multi_page(client: TestClient) -> None:
    with session_maker() as session:
        for _ in range(45):
            user = User(name="John Doe")
            session.add(user)
        session.commit()

    response = client.get("/admin/user/list")

    assert response.status_code == 200

    # Previous disabled
    assert response.text.count('<li class="page-item disabled">') == 1
    assert response.text.count('<li class="page-item ">') == 5

    response = client.get("/admin/user/list?page=3")

    assert response.status_code == 200
    assert response.text.count('<li class="page-item ">') == 6

    response = client.get("/admin/user/list?page=5")
    assert response.status_code == 200

    # Next disabled
    assert response.text.count('<li class="page-item disabled">') == 1
    assert response.text.count('<li class="page-item ">') == 5


def test_list_page_permission_actions(client: TestClient) -> None:
    with session_maker() as session:
        for _ in range(10):
            user = User(name="John Doe")
            session.add(user)
            session.flush()

            address = Address(user_id=user.id)
            session.add(address)

        session.commit()

    response = client.get("/admin/user/list")

    assert response.status_code == 200
    assert response.text.count('<i class="fa-solid fa-eye"></i>') == 10
    assert response.text.count('<i class="fa-solid fa-trash"></i>') == 10

    response = client.get("/admin/address/list")

    assert response.status_code == 200
    assert response.text.count('<i class="fa-solid fa-eye"></i>') == 10
    assert response.text.count('<i class="fa-solid fa-pencil"></i>') == 0
    assert response.text.count('<i class="fa-solid fa-trash"></i>') == 10


def test_unauthorized_detail_page(client: TestClient) -> None:
    response = client.get("/admin/movie/details/1")

    assert response.status_code == 403


def test_not_found_detail_page(client: TestClient) -> None:
    response = client.get("/admin/user/details/1")

    assert response.status_code == 404


def test_detail_page(client: TestClient) -> None:
    with session_maker() as session:
        user = User(name="Amin Alaee")
        session.add(user)
        session.flush()

        for _ in range(2):
            address = Address(user_id=user.id)
            session.add(address)
            address_formattable = AddressFormattable(user_id=user.id)
            session.add(address_formattable)
        profile = Profile(user=user)
        session.add(profile)
        profile_formattable = ProfileFormattable(user=user)
        session.add(profile_formattable)
        session.commit()

    response = client.get("/admin/user/details/1")

    assert response.status_code == 200
    assert '<th class="w-1">Column</th>' in response.text
    assert '<th class="w-1">Value</th>' in response.text
    assert "<td>id</td>" in response.text
    assert "<td>1</td>" in response.text
    assert "<td>name</td>" in response.text
    assert "<td>Amin Alaee</td>" in response.text
    assert "<td>addresses</td>" in response.text
    assert (
        '<a href="http://testserver/admin/address/details/1">(Address 1)</a>'
        in response.text
    )
    assert "<td>profile</td>" in response.text
    assert (
        '<a href="http://testserver/admin/profile/details/1">Profile 1</a>'
        in response.text
    )
    assert "<td>addresses_formattable</td>" in response.text
    assert "(Formatted Address 1)" in response.text
    assert "<td>profile_formattable</td>" in response.text
    assert "Formatted Profile 1" in response.text

    # Action Buttons
    assert response.text.count("http://testserver/admin/user/list") == 2
    assert response.text.count("Go Back") == 1

    # Delete modal
    assert response.text.count("Cancel") == 1
    assert response.text.count("Delete") == 2


def test_column_labels(client: TestClient) -> None:
    with session_maker() as session:
        user = User(name="Foo")
        session.add(user)
        session.commit()

    response = client.get("/admin/user/list")

    assert response.status_code == 200
    assert "Email" in response.text

    response = client.get("/admin/user/details/1")

    assert response.status_code == 200
    assert "Email" in response.text


def test_delete_endpoint_unauthorized_response(client: TestClient) -> None:
    response = client.delete("/admin/movie/delete")

    assert response.status_code == 403


def test_delete_endpoint_not_found_response(client: TestClient) -> None:
    response = client.delete("/admin/user/delete?pks=1")

    assert response.status_code == 404

    with session_maker() as s:
        assert s.query(User).count() == 0


def test_delete_endpoint(client: TestClient) -> None:
    with session_maker() as session:
        user = User(name="Bar")
        session.add(user)
        session.commit()

    with session_maker() as s:
        assert s.query(User).count() == 1

    response = client.delete("/admin/user/delete?pks=1")

    assert response.status_code == 200

    with session_maker() as s:
        assert s.query(User).count() == 0


def test_create_endpoint_unauthorized_response(client: TestClient) -> None:
    response = client.get("/admin/movie/create")

    assert response.status_code == 403


def test_create_endpoint_get_form(client: TestClient) -> None:
    response = client.get("/admin/user/create")

    assert response.status_code == 200
    assert (
        '<select class="form-control" id="addresses" multiple name="addresses">'
        in response.text
    )
    assert '<select class="form-control" id="profile" name="profile">' in response.text
    assert 'id="name" maxlength="16" name="name" type="text" value="">' in response.text
    assert (
        '<input class="form-control" id="email" name="email" type="text" value="">'
        in response.text
    )


def test_create_endpoint_post_form(client: TestClient) -> None:
    data: dict = {"birthdate": "Wrong Date Format"}
    response = client.post("/admin/user/create", data=data)

    assert response.status_code == 400
    assert (
        '<div class="invalid-feedback">Not a valid date value.</div>' in response.text
    )

    data = {"name": "SQLAlchemy", "email": "amin"}
    response = client.post("/admin/user/create", data=data)

    stmt = select(func.count(User.id))
    with session_maker() as s:
        assert s.execute(stmt).scalar_one() == 1

    stmt = (
        select(User)
        .limit(1)
        .options(selectinload(User.addresses))
        .options(selectinload(User.profile))
    )
    with session_maker() as s:
        user = s.execute(stmt).scalar_one()
    assert user.name == "SQLAlchemy"
    assert user.email == "amin"
    assert user.addresses == []
    assert user.profile is None

    data = {"user": user.id}
    response = client.post("/admin/address/create", data=data)

    stmt = select(func.count(Address.id))
    with session_maker() as s:
        assert s.execute(stmt).scalar_one() == 1

    stmt = select(Address).limit(1).options(selectinload(Address.user))
    with session_maker() as s:
        address = s.execute(stmt).scalar_one()
    assert address.user.id == user.id
    assert address.user_id == user.id

    data = {"user": user.id}
    response = client.post("/admin/profile/create", data=data)

    stmt = select(func.count(Profile.id))
    with session_maker() as s:
        assert s.execute(stmt).scalar_one() == 1

    stmt = select(Profile).limit(1).options(selectinload(Profile.user))
    with session_maker() as s:
        profile = s.execute(stmt).scalar_one()
    assert profile.user.id == user.id
    assert profile.user_id == user.id

    data = {
        "name": "SQLAdmin",
        "addresses": [address.id],
        "profile": profile.id,
    }
    response = client.post("/admin/user/create", data=data)

    stmt = select(func.count(User.id))
    with session_maker() as s:
        assert s.execute(stmt).scalar_one() == 2

    stmt = (
        select(User)
        .offset(1)
        .limit(1)
        .options(selectinload(User.addresses))
        .options(selectinload(User.profile))
    )
    with session_maker() as s:
        user = s.execute(stmt).scalar_one()
    assert user.name == "SQLAdmin"
    assert user.addresses[0].id == address.id
    assert user.profile.id == profile.id

    data = {"name": "SQLAlchemy", "email": "amin"}
    response = client.post("/admin/user/create", data=data)
    assert response.status_code == 400
    assert "alert alert-danger" in response.text


def test_list_view_page_size_options(client: TestClient) -> None:
    response = client.get("/admin/user/list")

    assert response.status_code == 200
    assert 'href="http://testserver/admin/user/list?pageSize=10' in response.text
    assert 'href="http://testserver/admin/user/list?pageSize=25' in response.text
    assert 'href="http://testserver/admin/user/list?pageSize=50' in response.text
    assert 'href="http://testserver/admin/user/list?pageSize=100' in response.text


def test_is_accessible_method(client: TestClient) -> None:
    response = client.get("/admin/movie/list")

    assert response.status_code == 403


def test_is_visible_method(client: TestClient) -> None:
    response = client.get("/admin")

    assert response.status_code == 200
    assert '<span class="nav-link-title">Users</span>' in response.text
    assert '<span class="nav-link-title">Addresses</span>' in response.text
    assert "Movie" not in response.text


def test_edit_endpoint_unauthorized_response(client: TestClient) -> None:
    response = client.get("/admin/movie/edit/1")

    assert response.status_code == 403


def test_not_found_edit_page(client: TestClient) -> None:
    response = client.get("/admin/user/edit/1")

    assert response.status_code == 404


def test_update_get_page(client: TestClient) -> None:
    with session_maker() as session:
        user = User(name="Joe", meta_data={"A": "B"})
        session.add(user)
        session.flush()

        address = Address(user=user)
        session.add(address)
        profile = Profile(user=user)
        session.add(profile)
        session.commit()

    response = client.get("/admin/user/edit/1")

    assert response.status_code == 200
    assert (
        '<select class="form-control" id="addresses" multiple name="addresses">'
        in response.text
    )
    assert '<option selected value="1">Address 1</option>' in response.text
    assert '<select class="form-control" id="profile" name="profile">' in response.text
    assert '<option selected value="1">Profile 1</option>' in response.text
    assert (
        'id="name" maxlength="16" name="name" type="text" value="Joe">' in response.text
    )

    response = client.get("/admin/address/edit/1")

    assert '<select class="form-control" id="user" name="user">' in response.text
    assert '<option value="__None"></option>' in response.text
    assert '<option selected value="1">User 1</option>' in response.text

    response = client.get("/admin/profile/edit/1")

    assert '<select class="form-control" id="user" name="user">' in response.text
    assert '<option value="__None"></option>' in response.text
    assert '<option selected value="1">User 1</option>' in response.text


def test_update_submit_form(client: TestClient) -> None:
    with session_maker() as session:
        user = User(name="Joe")
        session.add(user)
        session.flush()

        address = Address(user=user)
        session.add(address)
        address_2 = Address(id=2)
        session.add(address_2)
        profile = Profile(user=user)
        session.add(profile)
        session.commit()

    data = {"name": "Jack", "email": "amin"}
    response = client.post("/admin/user/edit/1", data=data)

    stmt = (
        select(User)
        .limit(1)
        .options(selectinload(User.addresses))
        .options(selectinload(User.profile))
    )
    with session_maker() as s:
        user = s.execute(stmt).scalar_one()
    assert user.name == "Jack"
    assert user.addresses == []
    assert user.profile is None
    assert user.email == "amin"

    data = {"name": "Jack", "addresses": "1", "profile": "1"}
    response = client.post("/admin/user/edit/1", data=data)

    stmt = select(Address).filter(Address.id == 1).limit(1)
    with session_maker() as s:
        address = s.execute(stmt).scalar_one()
    assert address.user_id == 1

    stmt = select(Profile).limit(1)
    with session_maker() as s:
        profile = s.execute(stmt).scalar_one()
    assert profile.user_id == 1

    data = {"name": "Jack" * 10}
    response = client.post("/admin/user/edit/1", data=data)

    assert response.status_code == 400

    data = {"user": user.id}
    response = client.post("/admin/address/edit/1", data=data)

    stmt = select(Address).filter(Address.id == 1).limit(1)
    with session_maker() as s:
        address = s.execute(stmt).scalar_one()
    assert address.user_id == 1

    data = {"name": "Jack", "email": "", "save": "Save as new"}
    response = client.post("/admin/user/edit/1", data=data)
    assert response.url == "http://testserver/admin/user/edit/2"

    data = {"name": "Jack", "email": "amin"}
    client.post("/admin/user/edit/1", data=data)
    response = client.post("/admin/user/edit/2", data=data)
    assert response.status_code == 400
    assert "alert alert-danger" in response.text

    data = {"name": "Jack", "addresses": ["1", "2"], "profile": "1"}
    response = client.post("/admin/user/edit/1", data=data)

    stmt = select(Address).limit(2)
    with session_maker() as s:
        result = s.execute(stmt).all()
    for address in result:
        assert address[0].user_id == 1


def test_searchable_list(client: TestClient) -> None:
    with session_maker() as session:
        user = User(name="Ross")
        session.add(user)
        user = User(name="Boss")
        session.add(user)
        session.commit()

    response = client.get("/admin/user/list")
    assert "Search: name" in response.text
    assert "/admin/user/details/1" in response.text

    response = client.get("/admin/user/list?search=ro")
    assert "/admin/user/details/1" in response.text

    response = client.get("/admin/user/list?search=rose")
    assert "/admin/user/details/1" not in response.text


def test_sortable_list(client: TestClient) -> None:
    with session_maker() as session:
        user = User(name="Lisa")
        session.add(user)
        session.commit()

    response = client.get("/admin/user/list?sortBy=id&sort=asc")

    assert "http://testserver/admin/user/list?sortBy=id&amp;sort=desc" in response.text

    response = client.get("/admin/user/list?sortBy=id&sort=desc")

    assert "http://testserver/admin/user/list?sortBy=id&amp;sort=asc" in response.text


def test_export_csv(client: TestClient) -> None:
    with session_maker() as session:
        user = User(name="Daniel", status="ACTIVE")
        session.add(user)
        session.commit()

    response = client.get("/admin/user/export/csv")
    assert response.text == "name,status\r\nDaniel,ACTIVE\r\n"


def test_export_csv_row_count(client: TestClient) -> None:
    def row_count(resp) -> int:
        return resp.text.count("\r\n") - 1

    with session_maker() as session:
        for _ in range(20):
            user = User(name="Raymond")
            session.add(user)
            session.flush()

            address = Address(user_id=user.id)
            session.add(address)

        session.commit()

    response = client.get("/admin/user/export/csv")
    assert row_count(response) == 20

    response = client.get("/admin/address/export/csv")
    assert row_count(response) == 3


def test_export_bad_type_is_404(client: TestClient) -> None:
    response = client.get("/admin/user/export/bad_type")
    assert response.status_code == 404


def test_export_permission(client: TestClient) -> None:
    response = client.get("/admin/movie/export/csv")
    assert response.status_code == 403
