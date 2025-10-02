import enum
from typing import Any, AsyncGenerator

import pytest
from httpx import AsyncClient
from sqlalchemy import (
    JSON,
    BigInteger,
    Column,
    Date,
    Enum,
    ForeignKey,
    Integer,
    String,
    Table,
    func,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import (
    declarative_base,
    relationship,
    selectinload,
    sessionmaker,
)
from starlette.applications import Starlette
from starlette.requests import Request

from sqladmin import Admin, ModelView
from tests.common import async_engine as engine

pytestmark = pytest.mark.anyio

Base = declarative_base()  # type: Any
session_maker = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

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
    date_of_birth = Column(Date)
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

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
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


class Product(Base):
    __tablename__ = "product"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    price = Column(BigInteger)


association_table = Table(
    "association_table",
    Base.metadata,
    Column("author_id", ForeignKey("authors.id")),
    Column("book_id", ForeignKey("books.id")),
)


class Author(Base):
    __tablename__ = "authors"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    books = relationship("Book", secondary=association_table)

    def __str__(self) -> str:
        return f"{self.name}"


class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True)
    title = Column(String)
    text = Column(String)

    def __str__(self) -> str:
        return f"{self.title}"


@pytest.fixture
async def prepare_database() -> AsyncGenerator[None, None]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def client(prepare_database: Any) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(app=app, base_url="http://testserver") as c:
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
    column_import_list = [User.name, User.status]
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
    can_import = True


class AddressAdmin(ModelView, model=Address):
    column_list = ["id", "user_id", "user", "user.profile.id"]
    name_plural = "Addresses"
    export_max_rows = 3
    column_import_list = ["user"]
    can_import = True


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


class ProductAdmin(ModelView, model=Product):
    pass


class AuthorAdmin(ModelView, model=Author):
    column_list = [Author.id, Author.name, Author.books]
    column_import_list = [Author.name, Author.books]
    can_import = True


class BookAdmin(ModelView, model=Book):
    column_list = [Book.id, Book.title, Book.text]
    column_import_list = [Book.id, Book.title, Book.text]
    can_import = True


admin.add_view(UserAdmin)
admin.add_view(AddressAdmin)
admin.add_view(ProfileAdmin)
admin.add_view(MovieAdmin)
admin.add_view(ProductAdmin)
admin.add_view(AuthorAdmin)
admin.add_view(BookAdmin)


async def test_root_view(client: AsyncClient) -> None:
    response = await client.get("/admin/")

    assert response.status_code == 200
    assert '<span class="nav-link-title">Users</span>' in response.text
    assert '<span class="nav-link-title">Addresses</span>' in response.text


async def test_invalid_list_page(client: AsyncClient) -> None:
    response = await client.get("/admin/example/list")

    assert response.status_code == 404


async def test_list_view_single_page(client: AsyncClient) -> None:
    async with session_maker() as session:
        for _ in range(5):
            user = User(name="John Doe")
            session.add(user)
        await session.commit()

    response = await client.get("/admin/user/list")
    assert response.status_code == 200

    # Showing active navigation link
    assert (
        '<a class="nav-link active" href="http://testserver/admin/user/list"'
        in response.text
    )

    # Next/Previous disabled
    assert response.text.count('<li class="page-item disabled">') == 2


async def test_list_view_with_relations(client: AsyncClient) -> None:
    async with session_maker() as session:
        for _ in range(5):
            user = User(name="John Doe")
            user.addresses.append(Address())
            user.profile = Profile()
            session.add(user)
        await session.commit()

    response = await client.get("/admin/user/list")

    assert response.status_code == 200

    # Show values of relationships
    assert (
        '<a href="http://testserver/admin/address/details/1">(Address 1)</a>'
        in response.text
    )

    assert (
        '<a href="http://testserver/admin/address/details/1">(Address 1)</a>'
        in response.text
    )
    assert (
        '<a href="http://testserver/admin/profile/details/1">Profile 1</a>'
        in response.text
    )


async def test_list_view_with_formatted_relations(client: AsyncClient) -> None:
    async with session_maker() as session:
        for _ in range(5):
            user = User(name="John Doe")
            user.addresses_formattable.append(AddressFormattable())
            user.profile_formattable = ProfileFormattable()
            session.add(user)
        await session.commit()

    response = await client.get("/admin/user/list")

    assert response.status_code == 200

    # Show values of relationships
    assert "(Formatted Address 1)" in response.text
    assert "Formatted Profile 1" in response.text


async def test_list_view_multi_page(client: AsyncClient) -> None:
    async with session_maker() as session:
        for _ in range(45):
            user = User(name="John Doe")
            session.add(user)
        await session.commit()

    response = await client.get("/admin/user/list")
    assert response.status_code == 200

    # Previous disabled
    assert response.text.count('<li class="page-item disabled">') == 1
    assert response.text.count('<li class="page-item ">') == 5

    response = await client.get("/admin/user/list?page=3")
    assert response.status_code == 200
    assert response.text.count('<li class="page-item ">') == 6

    response = await client.get("/admin/user/list?page=5")
    assert response.status_code == 200

    # Next disabled
    assert response.text.count('<li class="page-item disabled">') == 1
    assert response.text.count('<li class="page-item ">') == 5


async def test_list_page_permission_actions(client: AsyncClient) -> None:
    async with session_maker() as session:
        for _ in range(10):
            user = User(name="John Doe")
            session.add(user)
            await session.flush()

            address = Address(user_id=user.id)
            session.add(address)

        await session.commit()

    response = await client.get("/admin/user/list")

    assert response.status_code == 200
    assert response.text.count('<i class="fa-solid fa-eye"></i>') == 10
    assert response.text.count('<i class="fa-solid fa-trash"></i>') == 10

    response = await client.get("/admin/address/list")

    assert response.status_code == 200
    assert response.text.count('<i class="fa-solid fa-eye"></i>') == 10
    assert response.text.count('<i class="fa-solid fa-pencil"></i>') == 0
    assert response.text.count('<i class="fa-solid fa-trash"></i>') == 10


async def test_unauthorized_detail_page(client: AsyncClient) -> None:
    response = await client.get("/admin/movie/details/1")

    assert response.status_code == 403


async def test_not_found_detail_page(client: AsyncClient) -> None:
    response = await client.get("/admin/user/details/1")

    assert response.status_code == 404


async def test_detail_page(client: AsyncClient) -> None:
    async with session_maker() as session:
        user = User(name="Amin Alaee")
        session.add(user)
        await session.flush()

        for _ in range(2):
            address = Address(user_id=user.id)
            session.add(address)
            address_formattable = AddressFormattable(user_id=user.id)
            session.add(address_formattable)
        profile = Profile(user_id=user.id)
        session.add(profile)
        profile_formattable = ProfileFormattable(user=user)
        session.add(profile_formattable)
        await session.commit()

    response = await client.get("/admin/user/details/1")

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
    assert "Formatted Profile 1</a>" in response.text

    # Action Buttons
    assert response.text.count("http://testserver/admin/user/list") == 2
    assert response.text.count("Go Back") == 1

    # Delete modal
    assert response.text.count("Cancel") == 1
    assert response.text.count("Delete") == 2


async def test_column_labels(client: AsyncClient) -> None:
    async with session_maker() as session:
        user = User(name="Foo")
        session.add(user)
        await session.commit()

    response = await client.get("/admin/user/list")

    assert response.status_code == 200
    assert "Email" in response.text

    response = await client.get("/admin/user/details/1")

    assert response.status_code == 200
    assert "Email" in response.text


async def test_delete_endpoint_unauthorized_response(client: AsyncClient) -> None:
    response = await client.delete("/admin/movie/delete")

    assert response.status_code == 403


async def test_delete_endpoint_not_found_response(client: AsyncClient) -> None:
    response = await client.delete("/admin/user/delete?pks=1")

    assert response.status_code == 404

    stmt = select(func.count(User.id))
    async with session_maker() as s:
        result = await s.execute(stmt)

    assert result.scalar_one() == 0


async def test_delete_endpoint(client: AsyncClient) -> None:
    async with session_maker() as session:
        user = User(name="Bar")
        session.add(user)
        await session.commit()

    stmt = select(func.count(User.id))

    async with session_maker() as s:
        result = await s.execute(stmt)
    assert result.scalar_one() == 1

    response = await client.delete("/admin/user/delete?pks=1")

    assert response.status_code == 200

    async with session_maker() as s:
        result = await s.execute(stmt)
    assert result.scalar_one() == 0


async def test_create_endpoint_unauthorized_response(client: AsyncClient) -> None:
    response = await client.get("/admin/movie/create")

    assert response.status_code == 403


async def test_create_endpoint_get_form(client: AsyncClient) -> None:
    response = await client.get("/admin/user/create")

    assert response.status_code == 200
    assert (
        '<select class="form-control" id="addresses" multiple name="addresses">'
        in response.text
    )
    assert '<select class="form-control" id="profile" name="profile">' in response.text
    assert (
        '<input class="form-control" id="name" maxlength="16" name="name"'
        in response.text
    )
    assert (
        '<input class="form-control" id="email" name="email" type="text" value="">'
        in response.text
    )


async def test_create_endpoint_with_required_fields(client: AsyncClient) -> None:
    response = await client.get("/admin/product/create")

    assert response.status_code == 200
    assert (
        '<label class="form-label col-sm-2 col-form-label required-label" for="name" '
        'title="This is a required field">Name</label>' in response.text
    )
    assert (
        '<label class="form-label col-sm-2 col-form-label" for="price">Price</label>'
        in response.text
    )


async def test_create_endpoint_post_form(client: AsyncClient) -> None:
    data = {"date_of_birth": "Wrong Date Format"}
    response = await client.post("/admin/user/create", data=data)

    assert response.status_code == 400
    assert (
        '<div class="invalid-feedback">Not a valid date value.</div>' in response.text
    )

    data = {"name": "SQLAlchemy", "email": "amin"}
    response = await client.post("/admin/user/create", data=data)

    stmt = select(func.count(User.id))
    async with session_maker() as s:
        result = await s.execute(stmt)
    assert result.scalar_one() == 1

    stmt = (
        select(User)
        .limit(1)
        .options(selectinload(User.addresses))
        .options(selectinload(User.profile))
    )
    async with session_maker() as s:
        result = await s.execute(stmt)
    user = result.scalar_one()
    assert user.name == "SQLAlchemy"
    assert user.email == "amin"
    assert user.addresses == []
    assert user.profile is None

    data = {"user": user.id}
    response = await client.post("/admin/address/create", data=data)

    stmt = select(func.count(Address.id))
    async with session_maker() as s:
        result = await s.execute(stmt)
    assert result.scalar_one() == 1

    stmt = select(Address).limit(1).options(selectinload(Address.user))
    async with session_maker() as s:
        result = await s.execute(stmt)
    address = result.scalar_one()
    assert address.user.id == user.id
    assert address.user_id == user.id

    data = {"user": user.id}
    response = await client.post("/admin/profile/create", data=data)

    stmt = select(func.count(Profile.id))
    async with session_maker() as s:
        result = await s.execute(stmt)
    assert result.scalar_one() == 1

    stmt = select(Profile).limit(1).options(selectinload(Profile.user))
    async with session_maker() as s:
        result = await s.execute(stmt)
    profile = result.scalar_one()
    assert profile.user.id == user.id

    data = {
        "name": "SQLAdmin",
        "addresses": [address.id],
        "profile": profile.id,
    }
    response = await client.post("/admin/user/create", data=data)

    stmt = select(func.count(User.id))
    async with session_maker() as s:
        result = await s.execute(stmt)
    assert result.scalar_one() == 2

    stmt = (
        select(User)
        .offset(1)
        .limit(1)
        .options(selectinload(User.addresses))
        .options(selectinload(User.profile))
    )
    async with session_maker() as s:
        result = await s.execute(stmt)
    user = result.scalar_one()
    assert user.name == "SQLAdmin"
    assert user.addresses[0].id == address.id
    assert user.profile.id == profile.id

    data = {"name": "SQLAlchemy", "email": "amin"}
    response = await client.post("/admin/user/create", data=data)
    assert response.status_code == 400
    assert "alert alert-danger" in response.text


async def test_list_view_page_size_options(client: AsyncClient) -> None:
    response = await client.get("/admin/user/list")

    assert response.status_code == 200
    assert "http://testserver/admin/user/list?pageSize=10" in response.text
    assert "http://testserver/admin/user/list?pageSize=25" in response.text
    assert "http://testserver/admin/user/list?pageSize=50" in response.text
    assert "http://testserver/admin/user/list?pageSize=100" in response.text


async def test_is_accessible_method(client: AsyncClient) -> None:
    response = await client.get("/admin/movie/list")

    assert response.status_code == 403


async def test_is_visible_method(client: AsyncClient) -> None:
    response = await client.get("/admin/")

    assert response.status_code == 200
    assert '<span class="nav-link-title">Users</span>' in response.text
    assert '<span class="nav-link-title">Addresses</span>' in response.text
    assert "Movie" not in response.text


async def test_edit_endpoint_unauthorized_response(client: AsyncClient) -> None:
    response = await client.get("/admin/movie/edit/1")

    assert response.status_code == 403


async def test_not_found_edit_page(client: AsyncClient) -> None:
    response = await client.get("/admin/user/edit/1")

    assert response.status_code == 404


async def test_update_get_page(client: AsyncClient) -> None:
    async with session_maker() as session:
        user = User(name="Joe", meta_data={"A": "B"})
        session.add(user)
        await session.flush()

        address = Address(user=user)
        session.add(address)
        profile = Profile(user=user)
        session.add(profile)
        await session.commit()

    response = await client.get("/admin/user/edit/1")

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

    response = await client.get("/admin/address/edit/1")

    assert '<select class="form-control" id="user" name="user">' in response.text
    assert '<option value="__None"></option>' in response.text
    assert '<option selected value="1">User 1</option>' in response.text

    response = await client.get("/admin/profile/edit/1")

    assert '<select class="form-control" id="user" name="user">' in response.text
    assert '<option value="__None"></option>' in response.text
    assert '<option selected value="1">User 1</option>' in response.text


async def test_update_submit_form(client: AsyncClient) -> None:
    async with session_maker() as session:
        user = User(name="Joe")
        session.add(user)
        await session.flush()

        address = Address(user=user)
        session.add(address)
        address_2 = Address(id=2)
        session.add(address_2)
        profile = Profile(user=user)
        session.add(profile)
        await session.commit()

    data = {"name": "Jack", "email": "amin"}
    response = await client.post("/admin/user/edit/1", data=data)

    stmt = (
        select(User)
        .limit(1)
        .options(selectinload(User.addresses))
        .options(selectinload(User.profile))
    )
    async with session_maker() as s:
        result = await s.execute(stmt)
    user = result.scalar_one()
    assert user.name == "Jack"
    assert user.addresses == []
    assert user.profile is None
    assert user.email == "amin"

    data = {"name": "Jack", "addresses": "1", "profile": "1"}
    response = await client.post("/admin/user/edit/1", data=data)

    stmt = select(Address).filter(Address.id == 1).limit(1)
    async with session_maker() as s:
        result = await s.execute(stmt)
    address = result.scalar_one()
    assert address.user_id == 1

    stmt = select(Profile).limit(1)
    async with session_maker() as s:
        result = await s.execute(stmt)
    profile = result.scalar_one()
    assert profile.user_id == 1

    data = {"name": "Jack" * 10}
    response = await client.post("/admin/user/edit/1", data=data)

    assert response.status_code == 400

    data = {"user": user.id}
    response = await client.post("/admin/address/edit/1", data=data)

    stmt = select(Address).filter(Address.id == 1).limit(1)
    async with session_maker() as s:
        result = await s.execute(stmt)
    address = result.scalar_one()
    assert address.user_id == 1

    data = {"name": "Jack", "email": "", "save": "Save as new"}
    response = await client.post("/admin/user/edit/1", data=data, follow_redirects=True)
    assert response.url == "http://testserver/admin/user/edit/2"

    data = {"name": "Jack", "email": "amin"}
    await client.post("/admin/user/edit/1", data=data)
    response = await client.post("/admin/user/edit/2", data=data)
    assert response.status_code == 400
    assert "alert alert-danger" in response.text

    data = {"name": "Jack", "addresses": ["1", "2"], "profile": "1"}
    response = await client.post("/admin/user/edit/1", data=data)

    stmt = select(Address).limit(1)
    async with session_maker() as s:
        result = await s.execute(stmt)
    for address in result:
        assert address[0].user_id == 1


async def test_searchable_list(client: AsyncClient) -> None:
    async with session_maker() as session:
        user = User(name="Ross")
        session.add(user)
        user = User(name="Boss")
        session.add(user)
        await session.commit()

    response = await client.get("/admin/user/list")
    assert "Search: name" in response.text
    assert "/admin/user/details/1" in response.text

    response = await client.get("/admin/user/list?search=ro")
    assert "/admin/user/details/1" in response.text

    response = await client.get("/admin/user/list?search=rose")
    assert "/admin/user/details/1" not in response.text


async def test_sortable_list(client: AsyncClient) -> None:
    async with session_maker() as session:
        user = User(name="Lisa")
        session.add(user)
        await session.commit()

    response = await client.get("/admin/user/list?sortBy=id&sort=asc")

    assert "http://testserver/admin/user/list?sortBy=id&amp;sort=desc" in response.text

    response = await client.get("/admin/user/list?sortBy=id&sort=desc")

    assert "http://testserver/admin/user/list?sortBy=id&amp;sort=asc" in response.text


async def test_export_csv(client: AsyncClient) -> None:
    async with session_maker() as session:
        user = User(name="Daniel", status="ACTIVE")
        session.add(user)
        await session.commit()

    response = await client.get("/admin/user/export/csv")
    assert response.text == "name,status\r\nDaniel,ACTIVE\r\n"


async def test_export_csv_row_count(client: AsyncClient) -> None:
    def row_count(resp) -> int:
        return resp.text.count("\r\n") - 1

    async with session_maker() as session:
        for _ in range(20):
            user = User(name="Raymond")
            session.add(user)
            await session.flush()

            address = Address(user_id=user.id)
            session.add(address)

        await session.commit()

    response = await client.get("/admin/user/export/csv")
    assert row_count(response) == 20

    response = await client.get("/admin/address/export/csv")
    assert row_count(response) == 3


async def test_export_csv_utf8(client: AsyncClient) -> None:
    async with session_maker() as session:
        user_1 = User(name="Daniel", status="ACTIVE")
        user_2 = User(name="دانيال", status="ACTIVE")
        user_3 = User(name="積極的", status="ACTIVE")
        user_4 = User(name="Даниэль", status="ACTIVE")
        session.add(user_1)
        session.add(user_2)
        session.add(user_3)
        session.add(user_4)
        await session.commit()

    response = await client.get("/admin/user/export/csv")
    assert response.text == (
        "name,status\r\nDaniel,ACTIVE\r\nدانيال,ACTIVE\r\n"
        "積極的,ACTIVE\r\nДаниэль,ACTIVE\r\n"
    )


async def test_export_json(client: AsyncClient) -> None:
    async with session_maker() as session:
        user = User(name="Daniel", status="ACTIVE")
        session.add(user)
        await session.commit()

    response = await client.get("/admin/user/export/json")
    assert response.text == '[{"name": "Daniel", "status": "ACTIVE"}]'


async def test_export_json_utf8(client: AsyncClient) -> None:
    async with session_maker() as session:
        user_1 = User(name="Daniel", status="ACTIVE")
        user_2 = User(name="دانيال", status="ACTIVE")
        user_3 = User(name="積極的", status="ACTIVE")
        user_4 = User(name="Даниэль", status="ACTIVE")
        session.add(user_1)
        session.add(user_2)
        session.add(user_3)
        session.add(user_4)
        await session.commit()

    response = await client.get("/admin/user/export/json")
    assert response.text == (
        '[{"name": "Daniel", "status": "ACTIVE"},'
        '{"name": "دانيال", "status": "ACTIVE"},'
        '{"name": "積極的", "status": "ACTIVE"},'
        '{"name": "Даниэль", "status": "ACTIVE"}]'
    )


async def test_export_bad_type_is_404(client: AsyncClient) -> None:
    response = await client.get("/admin/user/export/bad_type")
    assert response.status_code == 404


async def test_export_permission_csv(client: AsyncClient) -> None:
    response = await client.get("/admin/movie/export/csv")
    assert response.status_code == 403


async def test_export_permission_json(client: AsyncClient) -> None:
    response = await client.get("/admin/movie/export/json")
    assert response.status_code == 403


async def test_import_csv_file(client: AsyncClient) -> None:
    await client.post(
        "/admin/user/import",
        files={
            "csvfile": (
                "user.csv",
                b"name;status\r\nUSER_1;ACTIVE\r\nUSER_2;DEACTIVE\r\n",
                "text/csv",
            )
        },
    )
    async with session_maker() as s:
        result = await s.execute(select(User).order_by(User.id))
        users = list(result.scalars())
    assert users[0].name == "USER_1"
    assert users[0].id == 1
    assert users[0].status == Status.ACTIVE
    assert users[1].name == "USER_2"
    assert users[1].id == 2
    assert users[1].status == Status.DEACTIVE


async def test_import_csv_file_with_fk(client: AsyncClient) -> None:
    await client.post(
        "/admin/user/import",
        files={
            "csvfile": (
                "user.csv",
                b"id;name;status\r\n1;USER_1;ACTIVE\r\n2;USER_2;DEACTIVE\r\n",
                "text/csv",
            )
        },
    )
    async with session_maker() as s:
        result = await s.execute(select(User).order_by(User.id))
        users = list(result.scalars())
    assert users[0].name == "USER_1"
    assert users[0].id == 1
    assert users[1].name == "USER_2"
    assert users[1].id == 2

    await client.post(
        "/admin/address/import",
        files={
            "csvfile": (
                "address.csv",
                b"id;user\r\n1;User 1\r\n2;User 2\r\n",
                "text/csv",
            )
        },
    )
    async with session_maker() as s:
        result = await s.execute(
            select(Address).options(selectinload(Address.user)).order_by(Address.id)
        )
        addresses = list(result.scalars())
    assert addresses[0].id == 1
    assert addresses[0].user.name == "USER_1"
    assert addresses[0].user.id == 1
    assert addresses[1].id == 2
    assert addresses[1].user.name == "USER_2"
    assert addresses[1].user.id == 2


async def test_import_csv_file_with_many_to_many(client: AsyncClient) -> None:
    files = {
        "csvfile": (
            "book.csv",
            b"id;title;text\r\n1;cool book;Once upon a time\r\n2;good_book;Well...\r\n",
            "text/csv",
        )
    }
    await client.post("/admin/book/import", files=files)
    async with session_maker() as s:
        result = await s.execute(select(Book).order_by(Book.id))
        books = list(result.scalars())
    assert books[0].title == "cool book"
    assert books[0].text == "Once upon a time"
    assert books[0].id == 1
    assert books[1].title == "good_book"
    assert books[1].text == "Well..."
    assert books[1].id == 2

    files = {
        "csvfile": (
            "author.csv",
            b"name;books\r\nalex;cool book,good_book\r\nsam;cool book,good_book\r\n",
            "text/csv",
        )
    }
    await client.post(
        "/admin/author/import",
        files=files,
    )
    async with session_maker() as s:
        result = await s.execute(
            select(Author).options(selectinload(Author.books)).order_by(Author.id)
        )
        authors = list(result.scalars())
    assert authors[0].id == 1
    assert authors[0].books[0].text == "Once upon a time"
    assert authors[0].books[1].text == "Well..."
    assert authors[1].id == 2
    assert authors[1].books[0].text == "Once upon a time"
    assert authors[1].books[1].text == "Well..."


async def test_import_csv_button(client: AsyncClient) -> None:
    response = await client.get("/admin/user/list")
    assert response.status_code == 200
    assert (
        '<input id="csvfile" name="csvfile" type="file" accept="text/csv" />'
        in response.text
    )


async def test_import_csv_bad_type_is_404(client: AsyncClient) -> None:
    response = await client.post(
        "/admin/notfound/import",
        files={
            "csvfile": (
                "notfound.csv",
                b"id\r\n1\r\n2\r\n",
                "text/csv",
            )
        },
    )
    assert response.status_code == 404


async def test_import_csv_permission(client: AsyncClient) -> None:
    response = await client.post(
        "/admin/movie/import",
        files={
            "csvfile": (
                "movie.csv",
                b"id\r\n1\r\n2\r\n",
                "text/csv",
            )
        },
    )
    assert response.status_code == 403
