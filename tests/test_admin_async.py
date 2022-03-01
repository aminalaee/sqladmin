from typing import Any, AsyncGenerator

import pytest
from sqlalchemy import Column, Date, ForeignKey, Integer, String, func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, selectinload, sessionmaker
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.testclient import TestClient

from sqladmin import Admin, ModelAdmin
from tests.common import TEST_DATABASE_URI_ASYNC

pytestmark = pytest.mark.anyio

Base = declarative_base()  # type: Any

engine = create_async_engine(
    TEST_DATABASE_URI_ASYNC, connect_args={"check_same_thread": False}
)

LocalSession = sessionmaker(bind=engine, class_=AsyncSession)

session: AsyncSession = LocalSession()

app = Starlette()
admin = Admin(app=app, engine=engine)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String(length=16))
    email = Column(String)
    date_of_birth = Column(Date)

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
async def prepare_database() -> AsyncGenerator[None, None]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


class UserAdmin(ModelAdmin, model=User):
    column_list = [User.id, User.name, User.email, User.addresses]
    column_labels = {User.email: "Email"}
    column_searchable_list = [User.name]
    column_sortable_list = [User.id]


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


async def test_root_view() -> None:
    with TestClient(app) as client:
        response = client.get("/admin")

    assert response.status_code == 200
    assert response.text.count('<span class="nav-link-title">Users</span>') == 1
    assert response.text.count('<span class="nav-link-title">Addresses</span>') == 1


async def test_invalid_list_page() -> None:
    with TestClient(app) as client:
        response = client.get("/admin/example/list")

    assert response.status_code == 404


async def test_list_view_single_page() -> None:
    for _ in range(5):
        user = User(name="John Doe")
        session.add(user)
    await session.commit()

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


async def test_list_view_multi_page() -> None:
    for _ in range(45):
        user = User(name="John Doe")
        session.add(user)
    await session.commit()

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


async def test_list_page_permission_actions() -> None:
    for _ in range(10):
        user = User(name="John Doe")
        session.add(user)
        await session.flush()

        address = Address(user_id=user.id)
        session.add(address)

    await session.commit()

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


async def test_unauthorized_detail_page() -> None:
    with TestClient(app) as client:
        response = client.get("/admin/movie/details/1")

    assert response.status_code == 403


async def test_not_found_detail_page() -> None:
    with TestClient(app) as client:
        response = client.get("/admin/user/details/1")

    assert response.status_code == 404


async def test_detail_page() -> None:
    user = User(name="Amin Alaee")
    session.add(user)
    await session.flush()

    for _ in range(2):
        address = Address(user_id=user.id)
        session.add(address)
    await session.commit()

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


async def test_column_labels() -> None:
    user = User(name="Foo")
    session.add(user)
    await session.commit()

    with TestClient(app) as client:
        response = client.get("/admin/user/list")

    assert response.status_code == 200
    assert response.text.count("Email") == 1

    with TestClient(app) as client:
        response = client.get("/admin/user/details/1")

    assert response.status_code == 200
    assert response.text.count("Email") == 1


async def test_delete_endpoint_unauthorized_response() -> None:
    with TestClient(app) as client:
        response = client.delete("/admin/movie/delete/1")

    assert response.status_code == 403


async def test_delete_endpoint_not_found_response() -> None:
    with TestClient(app) as client:
        response = client.delete("/admin/user/delete/1")

    assert response.status_code == 404

    stmt = select(func.count(User.id))
    result = await session.execute(stmt)
    assert result.scalar_one() == 0


async def test_delete_endpoint() -> None:
    user = User(name="Bar")
    session.add(user)
    await session.commit()

    stmt = select(func.count(User.id))

    result = await session.execute(stmt)
    assert result.scalar_one() == 1

    with TestClient(app) as client:
        response = client.delete("/admin/user/delete/1")

    assert response.status_code == 200

    result = await session.execute(stmt)
    assert result.scalar_one() == 0


async def test_create_endpoint_unauthorized_response() -> None:
    with TestClient(app) as client:
        response = client.get("/admin/movie/create")

    assert response.status_code == 403


async def test_create_endpoint_get_form() -> None:
    with TestClient(app) as client:
        response = client.get("/admin/user/create")

    assert response.status_code == 200
    assert (
        '<select class="form-control" id="addresses" multiple name="addresses">'
        in response.text
    )
    assert (
        '<input class="form-control" id="name" maxlength="16" name="name"'
        in response.text
    )
    assert (
        '<input class="form-control" id="email" name="email" type="text" value="">'
        in response.text
    )


async def test_create_endpoint_post_form() -> None:
    data: dict = {"date_of_birth": "Wrong Date Format"}
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
    result = await session.execute(stmt)
    assert result.scalar_one() == 1
    assert response.status_code == 302

    stmt = select(User).limit(1).options(selectinload(User.addresses))
    result = await session.execute(stmt)
    user = result.scalar_one()
    assert user.name == "SQLAlchemy"
    assert user.email is None
    assert user.addresses == []

    data = {"user": user.id}
    with TestClient(app) as client:
        response = client.post("/admin/address/create", data=data)

    stmt = select(func.count(Address.id))
    result = await session.execute(stmt)
    assert result.scalar_one() == 1
    assert response.status_code == 302

    stmt = select(Address).limit(1)
    result = await session.execute(stmt)
    address = result.scalar_one()
    assert address.user == user
    assert address.user_id == user.id

    data = {"name": "SQLAdmin", "addresses": [address.id]}
    with TestClient(app) as client:
        response = client.post("/admin/user/create", data=data)

    stmt = select(func.count(User.id))
    result = await session.execute(stmt)
    assert result.scalar_one() == 2
    assert response.status_code == 302

    stmt = select(User).offset(1).limit(1).options(selectinload(User.addresses))
    result = await session.execute(stmt)
    user = result.scalar_one()
    assert user.name == "SQLAdmin"
    assert user.addresses == [address]


async def test_list_view_page_size_options() -> None:
    with TestClient(app) as client:
        response = client.get("/admin/user/list")

    assert response.status_code == 200
    assert "http://testserver/admin/user/list?pageSize=10" in response.text
    assert "http://testserver/admin/user/list?pageSize=25" in response.text
    assert "http://testserver/admin/user/list?pageSize=50" in response.text
    assert "http://testserver/admin/user/list?pageSize=100" in response.text


async def test_is_accessible_method() -> None:
    with TestClient(app) as client:
        response = client.get("/admin/movie/list")

    assert response.status_code == 403


async def test_is_visible_method() -> None:
    with TestClient(app) as client:
        response = client.get("/admin")

    assert response.status_code == 200
    assert response.text.count('<span class="nav-link-title">Users</span>') == 1
    assert response.text.count('<span class="nav-link-title">Addresses</span>') == 1
    assert response.text.count("Movie") == 0


async def test_edit_endpoint_unauthorized_response() -> None:
    with TestClient(app) as client:
        response = client.get("/admin/movie/edit/1")

    assert response.status_code == 403


async def test_not_found_edit_page() -> None:
    with TestClient(app) as client:
        response = client.get("/admin/user/edit/1")

    assert response.status_code == 404


async def test_update_get_page() -> None:
    user = User(name="Joe")
    session.add(user)
    await session.flush()

    address = Address(user=user)
    session.add(address)
    await session.commit()

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


async def test_update_submit_form() -> None:
    user = User(name="Joe")
    session.add(user)
    await session.flush()

    address = Address(user=user)
    session.add(address)
    await session.commit()

    with TestClient(app) as client:
        data = {"name": "Jack"}
        response = client.post("/admin/user/edit/1", data=data)

    assert response.status_code == 302

    stmt = select(User).limit(1).options(selectinload(User.addresses))
    result = await session.execute(stmt)
    user = result.scalar_one()
    assert user.name == "Jack"
    assert user.addresses == []

    with TestClient(app) as client:
        data = {"name": "Jack", "addresses": "1"}
        response = client.post("/admin/user/edit/1", data=data)

    stmt = select(Address).limit(1)
    result = await session.execute(stmt)
    address = result.scalar_one()
    assert address.user_id == 1

    with TestClient(app) as client:
        data = {"name": "Jack" * 10}
        response = client.post("/admin/user/edit/1", data=data)

    assert response.status_code == 400


async def test_searchable_list() -> None:
    user = User(name="Ross")
    session.add(user)
    await session.commit()

    with TestClient(app) as client:
        response = client.get("/admin/user/list")

    assert (
        response.text.count(
            '<button id="search-button" class="btn" type="button">Search</button>'
        )
        == 1
    )

    assert response.text.count("Search: name") == 1
    assert "http://testserver/admin/user/details/1" in response.text

    with TestClient(app) as client:
        response = client.get("/admin/user/list?search=ro")

    assert "http://testserver/admin/user/details/1" in response.text

    with TestClient(app) as client:
        response = client.get("/admin/user/list?search=rose")

    assert "http://testserver/admin/user/details/1" not in response.text


async def test_sortable_list() -> None:
    user = User(name="Lisa")
    session.add(user)
    await session.commit()

    with TestClient(app) as client:
        response = client.get("/admin/user/list?sortBy=id&sort=asc")

    assert (
        response.text.count("http://testserver/admin/user/list?sortBy=id&amp;sort=desc")
        == 1
    )

    with TestClient(app) as client:
        response = client.get("/admin/user/list?sortBy=id&sort=desc")

    assert (
        response.text.count("http://testserver/admin/user/list?sortBy=id&amp;sort=asc")
        == 1
    )
