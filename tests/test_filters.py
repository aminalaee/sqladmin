import re
from typing import Any, AsyncGenerator

import pytest
from httpx import AsyncClient
from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from starlette.applications import Starlette

from sqladmin import Admin, ModelView
from sqladmin.filters import (
    AllUniqueStringValuesFilter,
    BooleanFilter,
    ForeignKeyFilter,
    OperationColumnFilter,
    StaticValuesFilter,
)
from tests.common import async_engine as engine

# Try to import UUID type for SQLAlchemy 2.0+
try:
    from sqlalchemy import Uuid

    HAS_UUID_SUPPORT = True
except ImportError:
    HAS_UUID_SUPPORT = False
    Uuid = None

Base = declarative_base()  # type: Any
session_maker = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

app = Starlette()
admin = Admin(app=app, engine=engine)


def create_user_table():
    """Create User table with optional UUID column based on SQLAlchemy version"""

    class User(Base):
        __tablename__ = "users"

        id = Column(Integer, primary_key=True)
        name = Column(String)
        title = Column(String)
        is_admin = Column(Boolean)
        office_id = Column(Integer, ForeignKey("offices.id"), nullable=True)
        age = Column(Integer)
        salary = Column(Float)
        description = Column(String)

        # Add UUID column only if SQLAlchemy 2.0+ is available
        if HAS_UUID_SUPPORT:
            user_uuid = Column(Uuid, nullable=True)

    return User


User = create_user_table()


class Address(Base):
    __tablename__ = "addresses"

    id = Column(Integer, primary_key=True)
    street = Column(String)


class Office(Base):
    __tablename__ = "offices"

    id = Column(Integer, primary_key=True)
    name = Column(String)


class UserAdmin(ModelView, model=User):
    column_list = [User.name, User.title, User.age, User.salary, User.description]
    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True

    # Base filters
    column_filters = [
        AllUniqueStringValuesFilter(User.title),
        BooleanFilter(User.is_admin),
        ForeignKeyFilter(User.office_id, Office.name),
        StaticValuesFilter(
            User.name, [("Admin User", "adminadmin")], parameter_name="static_name"
        ),
        OperationColumnFilter(User.name),
        OperationColumnFilter(User.age),
        OperationColumnFilter(User.salary),
        OperationColumnFilter(User.description),
    ]

    # Add UUID filter only if UUID column exists
    if hasattr(User, "user_uuid"):
        column_filters.append(OperationColumnFilter(User.user_uuid))


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
            name="Admin User",
            title="Manager",
            is_admin=True,
            office_id=office1.id,
            age=35,
            salary=80000.50,
            description="Senior administrator with management responsibilities",
        )
        user2 = User(
            name="Regular User",
            title="Developer",
            is_admin=False,
            office_id=office2.id,
            age=28,
            salary=55000.75,
            description="Software developer specializing in web applications",
        )
        user3 = User(
            name="Test User",
            title="Analyst",
            is_admin=False,
            office_id=office1.id,
            age=42,
            salary=65000.00,
            description="Data analyst working on business intelligence",
        )
        session.add_all([user1, user2, user3])
        await session.commit()

    yield


@pytest.fixture
async def client(
    prepare_database: Any, prepare_data: Any
) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(app=app, base_url="http://testserver") as c:
        yield c


def assert_records_count(
    showing_records_from: int,
    showing_records_to: int,
    total_records_count: int,
    response_text: str,
) -> None:
    pattern = (
        rf"Showing\s*.*{showing_records_from}\s*.*to\s*.*"
        rf"{showing_records_to}\s*.*of\s*.*{total_records_count}"
    )

    assert re.search(
        pattern, response_text, re.DOTALL
    ), f"Expected pattern not found in response text: {pattern}"


@pytest.mark.anyio
async def test_column_filters_sidebar_existence(client: AsyncClient) -> None:
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
    assert_records_count(1, 2, 2, response.text)

    # Test filtering for admin users (is_admin=true)
    response = await client.get("/admin/user/list?is_admin=true")
    assert response.status_code == 200
    assert "Admin User" in response.text
    assert "Regular User" not in response.text
    assert_records_count(1, 1, 1, response.text)

    # Test filtering for non-admin users (is_admin=false)
    response = await client.get("/admin/user/list?is_admin=false")
    assert response.status_code == 200
    assert "Admin User" not in response.text
    assert "Regular User" in response.text
    assert_records_count(1, 1, 1, response.text)


@pytest.mark.anyio
async def test_foreign_key_filter_functionality(client: AsyncClient) -> None:
    """Test that foreign key filters correctly filter users based on their office."""
    response = await client.get("/admin/user/list")
    assert response.status_code == 200
    assert "Office1" in response.text
    assert "Office2" in response.text
    assert_records_count(1, 2, 2, response.text)

    response = await client.get("/admin/user/list?office_id=1")
    assert response.status_code == 200
    assert "Admin User" in response.text
    assert "Regular User" not in response.text
    assert_records_count(1, 1, 1, response.text)


@pytest.mark.anyio
async def test_static_values_filter_functionality(client: AsyncClient) -> None:
    """Test that static values filters correctly filter users based on their name."""
    response = await client.get("/admin/user/list?static_name=Admin User")
    assert response.status_code == 200
    assert "adminadmin" in response.text
    assert "Admin User" in response.text
    assert "Regular User" not in response.text
    assert_records_count(1, 1, 1, response.text)


@pytest.mark.anyio
async def test_column_filter_string_operations(client: AsyncClient) -> None:
    """Test that ColumnFilter correctly handles string operations."""
    # Test contains operation
    url = "/admin/user/list?name=Admin&name_op=contains"
    response = await client.get(url)
    assert response.status_code == 200
    assert "Admin User" in response.text
    assert "Regular User" not in response.text
    assert "Test User" not in response.text

    # Test equals operation
    url = "/admin/user/list?name=Test User&name_op=equals"
    response = await client.get(url)
    assert response.status_code == 200
    assert "Test User" in response.text
    assert "Admin User" not in response.text
    assert "Regular User" not in response.text

    # Test starts_with operation
    url = "/admin/user/list?name=Regular&name_op=starts_with"
    response = await client.get(url)
    assert response.status_code == 200
    assert "Regular User" in response.text
    assert "Admin User" not in response.text
    assert "Test User" not in response.text

    # Test ends_with operation
    url = "/admin/user/list?name=User&name_op=ends_with"
    response = await client.get(url)
    assert response.status_code == 200
    assert "Admin User" in response.text
    assert "Regular User" in response.text
    assert "Test User" in response.text


@pytest.mark.anyio
async def test_column_filter_numeric_operations(client: AsyncClient) -> None:
    """Test that ColumnFilter correctly handles numeric operations."""
    # Test equals operation for age
    response = await client.get("/admin/user/list?age=35&age_op=equals")
    assert response.status_code == 200
    assert "Admin User" in response.text
    assert "Regular User" not in response.text
    assert "Test User" not in response.text

    # Test greater_than operation for age
    response = await client.get("/admin/user/list?age=30&age_op=greater_than")
    assert response.status_code == 200
    assert "Admin User" in response.text
    assert "Test User" in response.text
    assert "Regular User" not in response.text

    # Test less_than operation for age
    response = await client.get("/admin/user/list?age=30&age_op=less_than")
    assert response.status_code == 200
    assert "Regular User" in response.text
    assert "Admin User" not in response.text
    assert "Test User" not in response.text

    # Test equals operation for salary (float)
    url = "/admin/user/list?salary=55000.75&salary_op=equals"
    response = await client.get(url)
    assert response.status_code == 200
    assert "Regular User" in response.text
    assert "Admin User" not in response.text
    assert "Test User" not in response.text

    # Test greater_than operation for salary
    url = "/admin/user/list?salary=60000&salary_op=greater_than"
    response = await client.get(url)
    assert response.status_code == 200
    assert "Admin User" in response.text
    assert "Test User" in response.text
    assert "Regular User" not in response.text


@pytest.mark.anyio
async def test_column_filter_description_operations(client: AsyncClient) -> None:
    """Test ColumnFilter string operations on description field."""
    # Test contains operation
    url = "/admin/user/list?description=administrator&description_op=contains"
    response = await client.get(url)
    assert response.status_code == 200
    assert "Admin User" in response.text
    assert "Regular User" not in response.text
    assert "Test User" not in response.text

    # Test contains operation - case insensitive
    url = "/admin/user/list?description=SOFTWARE&description_op=contains"
    response = await client.get(url)
    assert response.status_code == 200
    assert "Regular User" in response.text
    assert "Admin User" not in response.text
    assert "Test User" not in response.text

    # Test starts_with operation
    url = "/admin/user/list?description=Data&description_op=starts_with"
    response = await client.get(url)
    assert response.status_code == 200
    assert "Test User" in response.text
    assert "Admin User" not in response.text
    assert "Regular User" not in response.text

    # Test ends_with operation
    url = "/admin/user/list?description=applications&description_op=ends_with"
    response = await client.get(url)
    assert response.status_code == 200
    assert "Regular User" in response.text
    assert "Admin User" not in response.text
    assert "Test User" not in response.text


@pytest.mark.anyio
async def test_column_filter_dropdown_ui_presence(client: AsyncClient) -> None:
    """Test that ColumnFilter provides dropdown UI elements."""
    response = await client.get("/admin/user/list")
    assert response.status_code == 200

    # Check for the filter sidebar container
    assert '<div id="filter-sidebar"' in response.text

    # Check for dropdown operation selectors for ColumnFilter fields (has_operator=True)
    # Name filter dropdown (string operations)
    assert 'name="name_op"' in response.text
    assert 'class="form-select form-select-sm"' in response.text
    assert "Select operation..." in response.text
    assert '<option value="contains"' in response.text
    assert '<option value="equals"' in response.text
    assert '<option value="starts_with"' in response.text
    assert '<option value="ends_with"' in response.text

    # Age filter dropdown (numeric operations)
    assert 'name="age_op"' in response.text
    assert '<option value="greater_than"' in response.text
    assert '<option value="less_than"' in response.text

    # Salary filter dropdown (numeric operations)
    assert 'name="salary_op"' in response.text

    # Description filter dropdown (string operations)
    assert 'name="description_op"' in response.text

    # UUID filter dropdown if supported
    if HAS_UUID_SUPPORT and hasattr(User, "user_uuid"):
        assert 'name="user_uuid_op"' in response.text

    # Check for text input fields for filter values
    assert 'name="name"' in response.text
    assert 'placeholder="Enter value"' in response.text
    assert 'class="form-control form-control-sm"' in response.text

    # Check for Apply Filter buttons
    assert "Apply Filter" in response.text
    assert 'type="submit"' in response.text
    assert 'class="btn btn-sm btn-outline-primary"' in response.text


@pytest.mark.anyio
async def test_column_filter_invalid_values(client: AsyncClient) -> None:
    """Test that ColumnFilter handles invalid values gracefully."""
    # Test invalid numeric value for age
    response = await client.get("/admin/user/list?age=invalid&age_op=equals")
    assert response.status_code == 200
    # Should show all users when invalid value is provided
    assert "Admin User" in response.text
    assert "Regular User" in response.text
    assert "Test User" in response.text

    # Test invalid numeric value for salary
    url = "/admin/user/list?salary=not_a_number&salary_op=greater_than"
    response = await client.get(url)
    assert response.status_code == 200
    # Should show all users when invalid value is provided
    assert "Admin User" in response.text
    assert "Regular User" in response.text
    assert "Test User" in response.text


@pytest.mark.anyio
async def test_column_filter_empty_values(client: AsyncClient) -> None:
    """Test that ColumnFilter handles empty values gracefully."""
    # Test empty value for string field
    response = await client.get("/admin/user/list?name=&name_op=contains")
    assert response.status_code == 200
    # Should show all users when empty value is provided
    assert "Admin User" in response.text
    assert "Regular User" in response.text
    assert "Test User" in response.text

    # Test empty value for numeric field
    response = await client.get("/admin/user/list?age=&age_op=equals")
    assert response.status_code == 200
    # Should show all users when empty value is provided
    assert "Admin User" in response.text
    assert "Regular User" in response.text
    assert "Test User" in response.text


@pytest.mark.skipif(
    not HAS_UUID_SUPPORT, reason="UUID support requires SQLAlchemy 2.0+"
)
@pytest.mark.anyio
async def test_column_filter_uuid_operations(client: AsyncClient) -> None:
    """Test that ColumnFilter correctly handles UUID operations when supported."""
    import uuid

    # Create a test user with UUID if UUID column exists
    if hasattr(User, "user_uuid"):
        test_uuid = uuid.uuid4()
        user_with_uuid = User(
            name="UUID User",
            title="UUID Dev",
            is_admin=False,
            age=40,
            salary=60000.0,
            description="User with UUID",
            user_uuid=test_uuid,
        )

        # Add to database
        async with session_maker() as session:
            session.add(user_with_uuid)
            await session.commit()

        # Test UUID contains operation
        uuid_str = str(test_uuid)
        partial_uuid = uuid_str[:8]  # Use first 8 characters

        url = f"/admin/user/list?user_uuid={partial_uuid}&user_uuid_op=contains"
        response = await client.get(url)
        assert response.status_code == 200
        assert "UUID User" in response.text

        # Test UUID starts_with operation
        url = f"/admin/user/list?user_uuid={partial_uuid}&user_uuid_op=starts_with"
        response = await client.get(url)
        assert response.status_code == 200
        assert "UUID User" in response.text

        # Test UUID equals operation (full UUID)
        url = f"/admin/user/list?user_uuid={uuid_str}&user_uuid_op=equals"
        response = await client.get(url)
        assert response.status_code == 200
        assert "UUID User" in response.text


@pytest.mark.anyio
async def test_column_filter_edge_cases():
    """Test edge cases for ColumnFilter"""
    from sqladmin.filters import OperationColumnFilter

    # Test with empty/None values
    column_filter = OperationColumnFilter(User.name)

    # Test empty value handling
    query = column_filter._convert_value_for_column("", User.name.property.columns[0])
    assert query is None

    # Test None value handling
    query = column_filter._convert_value_for_column(None, User.name.property.columns[0])
    assert query is None

    # Test invalid numeric conversion
    age_filter = OperationColumnFilter(User.age)
    query = age_filter._convert_value_for_column(
        "invalid_number", User.age.property.columns[0]
    )
    assert query is None

    # Test invalid float conversion
    salary_filter = OperationColumnFilter(User.salary)
    query = salary_filter._convert_value_for_column(
        "invalid_float", User.salary.property.columns[0]
    )
    assert query is None


@pytest.mark.anyio
async def test_column_filter_type_detection():
    """Test ColumnFilter type detection methods"""
    from sqladmin.filters import OperationColumnFilter

    filter_instance = OperationColumnFilter(User.name)

    # Test string type detection
    assert filter_instance._is_string_type(User.name.property.columns[0]) is True
    assert filter_instance._is_numeric_type(User.name.property.columns[0]) is False

    # Test numeric type detection
    assert filter_instance._is_numeric_type(User.age.property.columns[0]) is True
    assert filter_instance._is_string_type(User.age.property.columns[0]) is False

    # Test float type detection
    assert filter_instance._is_numeric_type(User.salary.property.columns[0]) is True
    assert filter_instance._is_string_type(User.salary.property.columns[0]) is False

    # Test UUID type detection (if available)
    if hasattr(User, "user_uuid") and HAS_UUID_SUPPORT:
        uuid_col = User.user_uuid.property.columns[0]
        assert filter_instance._is_uuid_type(uuid_col) is True
        assert filter_instance._is_string_type(uuid_col) is False
        assert filter_instance._is_numeric_type(uuid_col) is False


@pytest.mark.anyio
async def test_column_filter_operations_comprehensive(client: AsyncClient) -> None:
    """Test all ColumnFilter operations comprehensively"""

    # Test string operations with ends_with
    url = "/admin/user/list?name=User&name_op=ends_with"
    response = await client.get(url)
    assert response.status_code == 200

    # Test numeric greater_than and less_than operations
    url = "/admin/user/list?age=25&age_op=greater_than"
    response = await client.get(url)
    assert response.status_code == 200

    url = "/admin/user/list?age=25&age_op=less_than"
    response = await client.get(url)
    assert response.status_code == 200

    # Test empty operation handling
    url = "/admin/user/list?name=Test&name_op="
    response = await client.get(url)
    assert response.status_code == 200

    # Test empty value handling
    url = "/admin/user/list?name=&name_op=contains"
    response = await client.get(url)
    assert response.status_code == 200


@pytest.mark.anyio
async def test_column_filter_operation_options():
    """Test ColumnFilter operation options for different column types"""
    from sqladmin.filters import OperationColumnFilter

    # Test string column operation options
    name_filter = OperationColumnFilter(User.name)
    options = name_filter.get_operation_options_for_model(User)
    expected_string_ops = ["contains", "equals", "starts_with", "ends_with"]
    assert len(options) == 4
    for op, _ in options:
        assert op in expected_string_ops

    # Test numeric column operation options
    age_filter = OperationColumnFilter(User.age)
    options = age_filter.get_operation_options_for_model(User)
    expected_numeric_ops = ["equals", "greater_than", "less_than"]
    assert len(options) == 3
    for op, _ in options:
        assert op in expected_numeric_ops

    # Test UUID column operation options (if available)
    if hasattr(User, "user_uuid") and HAS_UUID_SUPPORT:
        uuid_filter = OperationColumnFilter(User.user_uuid)
        options = uuid_filter.get_operation_options_for_model(User)
        expected_uuid_ops = ["equals", "contains", "starts_with"]
        assert len(options) == 3
        for op, _ in options:
            assert op in expected_uuid_ops


@pytest.mark.anyio
async def test_column_filter_lookups_method():
    """Test ColumnFilter lookups method (returns empty for has_operator filters)"""
    from sqladmin.filters import OperationColumnFilter

    filter_instance = OperationColumnFilter(User.name)

    # Mock request and run_query function
    from unittest.mock import MagicMock

    mock_request = MagicMock()
    mock_run_query = MagicMock()

    # Test that lookups returns empty list for has_operator=True filters
    result = await filter_instance.lookups(mock_request, User, mock_run_query)
    assert result == []


@pytest.mark.anyio
async def test_column_filter_unknown_operation():
    """Test ColumnFilter with unknown operation type"""
    from sqlalchemy.sql.expression import select

    from sqladmin.filters import OperationColumnFilter

    filter_instance = OperationColumnFilter(User.name)

    # Create a mock query
    stmt = select(User)

    # Test with unknown operation - should return query unchanged
    result = await filter_instance.get_filtered_query(
        stmt, "unknown_operation", "test_value", User
    )
    assert result == stmt


@pytest.mark.anyio
async def test_column_filter_conversion_edge_cases():
    """Test ColumnFilter value conversion edge cases"""
    from sqladmin.filters import OperationColumnFilter

    filter_instance = OperationColumnFilter(User.name)

    # Test empty string
    result = filter_instance._convert_value_for_column(
        "", User.name.property.columns[0]
    )
    assert result is None

    # Test whitespace-only string for numeric conversion
    age_filter = OperationColumnFilter(User.age)
    result = age_filter._convert_value_for_column("   ", User.age.property.columns[0])
    assert result is None

    # Test valid string with whitespace
    result = filter_instance._convert_value_for_column(
        "  test  ", User.name.property.columns[0]
    )
    assert result == "  test  "

    # Test valid integer conversion
    result = age_filter._convert_value_for_column("42", User.age.property.columns[0])
    assert result == 42

    # Test valid float conversion
    salary_filter = OperationColumnFilter(User.salary)
    result = salary_filter._convert_value_for_column(
        "1234.56", User.salary.property.columns[0]
    )
    assert result == 1234.56


@pytest.mark.skipif(
    not HAS_UUID_SUPPORT, reason="UUID support requires SQLAlchemy 2.0+"
)
@pytest.mark.anyio
async def test_column_filter_uuid_conversion():
    """Test ColumnFilter UUID value conversion"""
    import uuid

    from sqladmin.filters import OperationColumnFilter

    if hasattr(User, "user_uuid"):
        filter_instance = OperationColumnFilter(User.user_uuid)
        uuid_col = User.user_uuid.property.columns[0]

        # Test valid UUID conversion for equals operation
        test_uuid = "550e8400-e29b-41d4-a716-446655440000"
        result = filter_instance._convert_value_for_column(
            test_uuid, uuid_col, "equals"
        )
        assert isinstance(result, uuid.UUID)
        assert str(result) == test_uuid

        # Test UUID conversion for contains operation (keeps as string)
        result = filter_instance._convert_value_for_column(
            test_uuid, uuid_col, "contains"
        )
        assert isinstance(result, str)
        assert result == test_uuid

        # Test invalid UUID conversion
        result = filter_instance._convert_value_for_column(
            "invalid-uuid", uuid_col, "equals"
        )
        assert result is None


@pytest.mark.anyio
async def test_column_filter_no_operation_or_value():
    """Test ColumnFilter behavior with missing operation or value"""
    from sqlalchemy.sql.expression import select

    from sqladmin.filters import OperationColumnFilter

    filter_instance = OperationColumnFilter(User.name)
    stmt = select(User)

    # Test with empty operation
    result = await filter_instance.get_filtered_query(stmt, "", "test_value", User)
    assert result == stmt

    # Test with no operation
    result = await filter_instance.get_filtered_query(stmt, None, "test_value", User)
    assert result == stmt

    # Test with empty value
    result = await filter_instance.get_filtered_query(stmt, "contains", "", User)
    assert result == stmt
