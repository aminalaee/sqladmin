from typing import Any, AsyncGenerator

import pytest
from httpx import AsyncClient
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from starlette.applications import Starlette

from sqladmin import Admin, ModelView
from sqladmin.filters import (
    AllUniqueStringValuesFilter,
    BooleanFilter,
    ForeignKeyFilter,
    StaticValuesFilter,
)
from tests.common import async_engine as engine

Base = declarative_base()  # type: Any
session_maker = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

app = Starlette()
admin = Admin(app=app, engine=engine)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    title = Column(String)
    is_admin = Column(Boolean)
    office_id = Column(Integer, ForeignKey("offices.id"), nullable=True)


class Address(Base):
    __tablename__ = "addresses"

    id = Column(Integer, primary_key=True)
    street = Column(String)


class Office(Base):
    __tablename__ = "offices"

    id = Column(Integer, primary_key=True)
    name = Column(String)


class UserAdmin(ModelView, model=User):
    column_list = [User.name, User.title]
    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True
    filter_list = [
        AllUniqueStringValuesFilter(User.title),
        BooleanFilter(User.is_admin),
        ForeignKeyFilter(User.office_id, Office.name),
        StaticValuesFilter(
            User.name, [("Admin User", "adminadmin")], parameter_name="static_name"
        ),
    ]


class AddressAdmin(ModelView, model=Address):
    column_list = [Address.street]
    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True
    # This admin will NOT have filters defined


admin.add_view(UserAdmin)
admin.add_view(AddressAdmin)


@pytest.fixture
async def prepare_database() -> AsyncGenerator[None, None]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def prepare_data(prepare_database: Any) -> AsyncGenerator[None, None]:
    # Add test data
    async with session_maker() as session:
        office1 = Office(name="Office1")
        office2 = Office(name="Office2")
        session.add_all([office1, office2])
        await session.commit()

        # Create users with different boolean values and titles
        user1 = User(
            name="Admin User", title="Manager", is_admin=True, office_id=office1.id
        )
        user2 = User(
            name="Regular User",
            title="Developer",
            is_admin=False,
            office_id=office2.id,
        )
        session.add_all([user1, user2])
        await session.commit()

    yield


@pytest.fixture
async def client(
    prepare_database: Any, prepare_data: Any
) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(app=app, base_url="http://testserver") as c:
        yield c


@pytest.mark.anyio
async def test_filter_list_sidebar_existence(client: AsyncClient) -> None:
    """Test that the filter list sidebar appears only when filters are defined."""
    # Test view with filters (UserAdmin)
    response = await client.get("/admin/user/list")
    assert response.status_code == 200

    # Check for the filter sidebar container
    assert '<div id="filter-sidebar"' in response.text

    # Test view without filters (AddressAdmin)
    response = await client.get("/admin/address/list")
    assert response.status_code == 200

    # Verify filter sidebar does not appear
    assert '<div id="filter-sidebar"' not in response.text


@pytest.mark.anyio
async def test_filter_lookups(client: AsyncClient) -> None:
    """Test that the filter lookups are correct."""
    response = await client.get("/admin/user/list")
    assert response.status_code == 200

    # Check for the filter sidebar container
    assert '<div id="filter-sidebar"' in response.text

    # Check for the filter lookups
    assert "All" in response.text
    assert "Manager" in response.text
    assert "Developer" in response.text
    assert "Yes" in response.text
    assert "No" in response.text


@pytest.mark.anyio
async def test_boolean_filter_functionality(client: AsyncClient) -> None:
    """Test that boolean filters correctly filter users
    based on their is_admin status."""
    # Test with no filter or 'all' filter - should show both users
    response = await client.get("/admin/user/list?is_admin=all")
    assert response.status_code == 200
    assert "Admin User" in response.text
    assert "Regular User" in response.text

    # Test filtering for admin users (is_admin=true)
    response = await client.get("/admin/user/list?is_admin=true")
    assert response.status_code == 200
    assert "Admin User" in response.text
    assert "Regular User" not in response.text

    # Test filtering for non-admin users (is_admin=false)
    response = await client.get("/admin/user/list?is_admin=false")
    assert response.status_code == 200
    assert "Admin User" not in response.text
    assert "Regular User" in response.text


@pytest.mark.anyio
async def test_foreign_key_filter_functionality(client: AsyncClient) -> None:
    """Test that foreign key filters correctly filter users based on their office."""
    response = await client.get("/admin/user/list")
    assert response.status_code == 200
    assert "Office1" in response.text
    assert "Office2" in response.text

    response = await client.get("/admin/user/list?office_id=1")
    assert response.status_code == 200
    assert "Admin User" in response.text
    assert "Regular User" not in response.text


@pytest.mark.anyio
async def test_static_values_filter_functionality(client: AsyncClient) -> None:
    """Test that static values filters correctly filter users based on their name."""
    response = await client.get("/admin/user/list?static_name=Admin User")
    assert response.status_code == 200
    assert "adminadmin" in response.text
    assert "Admin User" in response.text
    assert "Regular User" not in response.text
