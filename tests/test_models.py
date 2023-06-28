import enum
from typing import Generator
from unittest.mock import Mock, call, patch

import pytest
from markupsafe import Markup
from sqlalchemy import Boolean, Column, Enum, ForeignKey, Integer, String, select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from starlette.applications import Starlette
from starlette.requests import Request

from sqladmin import Admin, ModelView
from sqladmin.exceptions import InvalidColumnError, InvalidModelError
from sqladmin.helpers import get_column_python_type, map_attr_to_prop
from tests.common import sync_engine as engine

pytestmark = pytest.mark.anyio

Base = declarative_base()  # type: ignore

LocalSession = sessionmaker(bind=engine)

app = Starlette()
admin = Admin(app=app, engine=engine)


class Status(enum.Enum):
    ACTIVE = "ACTIVE"
    DEACTIVE = "DEACTIVE"


class Role(int, enum.Enum):
    ADMIN = 1
    USER = 2


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    role = Column(Enum(Role))
    status = Column(Enum(Status))

    addresses = relationship("Address", back_populates="user")
    profile = relationship("Profile", back_populates="user", uselist=False)


class Address(Base):
    __tablename__ = "addresses"

    pk = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    user = relationship("User", back_populates="addresses")


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True)
    is_active = Column(Boolean)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)

    user = relationship("User", back_populates="profile")


@pytest.fixture(autouse=True)
def prepare_database() -> Generator[None, None, None]:
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


def test_metadata_setup() -> None:
    class UserAdmin(ModelView, model=User):
        pass

    assert UserAdmin.identity == "user"
    assert UserAdmin.name == "User"
    assert UserAdmin.name_plural == "Users"

    class TempModel(User):
        pass

    class TempAdmin(ModelView, model=TempModel):
        icon = "fa-solid fa-user"

    assert TempAdmin.icon == "fa-solid fa-user"
    assert TempAdmin.identity == "temp-model"
    assert TempAdmin.name == "Temp Model"
    assert TempAdmin.name_plural == "Temp Models"


def test_setup_with_invalid_sqlalchemy_model() -> None:
    with pytest.raises(InvalidModelError) as exc:

        class AddressAdmin(ModelView, model=Starlette):
            pass

    assert exc.match("Class Starlette is not a SQLAlchemy model.")


def test_column_list_default() -> None:
    class UserAdmin(ModelView, model=User):
        pass

    assert UserAdmin().get_list_columns() == [("id", User.id)]


def test_column_list_by_model_columns() -> None:
    class UserAdmin(ModelView, model=User):
        column_list = [User.id, User.name]

    assert UserAdmin.column_list == [User.id, User.name]


def test_column_list_by_str_name() -> None:
    class AddressAdmin(ModelView, model=Address):
        column_list = ["pk", "user_id"]

    assert AddressAdmin().get_list_columns() == [
        ("pk", Address.pk),
        ("user_id", Address.user_id),
    ]


def test_column_list_invalid_attribute() -> None:
    class ExampleAdmin(ModelView, model=Address):
        column_list = ["example"]

    with pytest.raises(InvalidColumnError) as exc:
        ExampleAdmin().get_list_columns()

    assert exc.match("Model 'Address' has no attribute 'example'.")


def test_column_list_both_include_and_exclude() -> None:
    with pytest.raises(AssertionError) as exc:

        class InvalidAdmin(ModelView, model=User):
            column_list = ["id"]
            column_exclude_list = ["name"]

    assert exc.match("Cannot use column_list and column_exclude_list together.")


def test_column_exclude_list_by_str_name() -> None:
    class UserAdmin(ModelView, model=User):
        column_exclude_list = ["id"]

    assert UserAdmin().get_list_columns() == [
        ("addresses", User.addresses.prop),
        ("profile", User.profile.prop),
        ("name", User.name),
    ]


def test_column_exclude_list_by_model_column() -> None:
    class UserAdmin(ModelView, model=User):
        column_exclude_list = [User.id]

    assert UserAdmin().get_list_columns() == [
        ("addresses", User.addresses.prop),
        ("profile", User.profile.prop),
        ("name", User.name),
    ]


def test_column_list_formatters() -> None:
    class UserAdmin(ModelView, model=User):
        column_formatters = {
            "id": lambda *args: 2,
            User.name: lambda m, a: m.name[:1],
        }

    user = User(id=1, name="Long Name")

    assert UserAdmin().get_list_value(user, User.id.prop)[0] == 1
    assert UserAdmin().get_list_value(user, User.id.prop)[1] == 2
    assert UserAdmin().get_list_value(user, User.name.prop)[0] == "Long Name"
    assert UserAdmin().get_list_value(user, User.name.prop)[1] == "L"


def test_column_formatters_detail() -> None:
    class UserAdmin(ModelView, model=User):
        column_formatters_detail = {
            "id": lambda *args: 2,
            User.name: lambda m, a: m.name[:1],
        }

    user = User(id=1, name="Long Name")

    assert UserAdmin().get_detail_value(user, User.id.prop)[0] == 1
    assert UserAdmin().get_detail_value(user, User.id.prop)[1] == 2
    assert UserAdmin().get_detail_value(user, User.name.prop)[0] == "Long Name"
    assert UserAdmin().get_detail_value(user, User.name.prop)[1] == "L"


def test_column_formatters_default() -> None:
    class ProfileAdmin(ModelView, model=Profile):
        ...

    user = User(id=1, name="Long Name")
    profile = Profile(user=user, is_active=True)

    assert ProfileAdmin().get_list_value(profile, Profile.is_active.prop) == (
        True,
        Markup("<i class='fa fa-check text-success'></i>"),
    )
    assert ProfileAdmin().get_detail_value(profile, Profile.is_active.prop) == (
        True,
        Markup("<i class='fa fa-check text-success'></i>"),
    )


def test_column_details_list_both_include_and_exclude() -> None:
    with pytest.raises(AssertionError) as exc:

        class InvalidAdmin(ModelView, model=User):
            column_details_list = ["id"]
            column_details_exclude_list = ["name"]

    assert exc.match(
        "Cannot use column_details_list and column_details_exclude_list together."
    )


def test_column_details_list_default() -> None:
    class UserAdmin(ModelView, model=User):
        pass

    assert UserAdmin().get_details_columns() == [
        ("addresses", User.addresses.prop),
        ("profile", User.profile.prop),
        ("id", User.id),
        ("name", User.name),
    ]


def test_column_details_list_by_model_column() -> None:
    class UserAdmin(ModelView, model=User):
        column_details_list = [User.name, User.id]

    assert UserAdmin().get_details_columns() == [("name", User.name), ("id", User.id)]


def test_column_details_exclude_list_by_model_column() -> None:
    class UserAdmin(ModelView, model=User):
        column_details_exclude_list = [User.id]

    assert UserAdmin().get_details_columns() == [
        ("addresses", User.addresses.prop),
        ("profile", User.profile.prop),
        ("name", User.name),
    ]


def test_column_labels_by_string_name() -> None:
    class UserAdmin(ModelView, model=User):
        column_list = [User.name]
        column_labels = {"name": "Name"}

    assert UserAdmin().get_list_columns() == [("Name", User.name)]

    class AddressAdmin(ModelView, model=Address):
        column_details_list = [Address.user_id]
        form_columns = ["user_id"]
        column_labels = {"user_id": "User ID"}

    assert AddressAdmin().get_details_columns() == [("User ID", Address.user_id)]
    assert AddressAdmin().get_form_columns() == [("User ID", Address.user_id)]


def test_column_labels_by_model_columns() -> None:
    class UserAdmin(ModelView, model=User):
        column_list = [User.name]
        column_labels = {User.name: "Name"}

    assert UserAdmin().get_list_columns() == [("Name", User.name)]

    class AddressAdmin(ModelView, model=Address):
        column_details_list = [Address.user_id]
        column_labels = {Address.user_id: "User ID"}

    assert AddressAdmin().get_details_columns() == [("User ID", Address.user_id)]


def test_get_model_attr_by_column() -> None:
    class UserAdmin(ModelView, model=User):
        ...

    assert map_attr_to_prop("name", UserAdmin()) == User.name
    assert map_attr_to_prop(User.name, UserAdmin()) == User.name


def test_form_columns_default() -> None:
    class UserAdmin(ModelView, model=User):
        pass

    assert UserAdmin().get_form_columns() == [
        ("addresses", User.addresses.prop),
        ("profile", User.profile.prop),
        ("id", User.id),
        ("name", User.name),
    ]


def test_form_columns_by_model_columns() -> None:
    class UserAdmin(ModelView, model=User):
        form_columns = [User.id, User.name]

    assert UserAdmin.form_columns == [User.id, User.name]


def test_form_columns_by_str_name() -> None:
    class AddressAdmin(ModelView, model=Address):
        form_columns = ["pk", "user_id"]

    assert AddressAdmin().get_form_columns() == [
        ("pk", Address.pk),
        ("user_id", Address.user_id),
    ]


def test_form_columns_both_include_and_exclude() -> None:
    with pytest.raises(AssertionError) as exc:

        class InvalidAdmin(ModelView, model=User):
            form_columns = ["id"]
            form_excluded_columns = ["name"]

    assert exc.match("Cannot use form_columns and form_excluded_columns together.")


def test_form_excluded_columns_by_str_name() -> None:
    class UserAdmin(ModelView, model=User):
        form_excluded_columns = ["id"]

    assert UserAdmin().get_form_columns() == [
        ("addresses", User.addresses.prop),
        ("profile", User.profile.prop),
        ("name", User.name),
    ]


def test_form_excluded_columns_by_model_column() -> None:
    class UserAdmin(ModelView, model=User):
        form_excluded_columns = [User.id]

    assert UserAdmin().get_form_columns() == [
        ("addresses", User.addresses.prop),
        ("profile", User.profile.prop),
        ("name", User.name),
    ]


def test_export_columns_default() -> None:
    class UserAdmin(ModelView, model=User):
        pass

    assert UserAdmin().get_export_columns() == [
        ("id", User.id.prop),
    ]


def test_export_columns_default_to_list_columns() -> None:
    class UserAdmin(ModelView, model=User):
        column_list = [User.id, User.name]

    assert UserAdmin().get_export_columns() == [
        ("id", User.id.prop),
        ("name", User.name.prop),
    ]

    class UserAdmin2(ModelView, model=User):
        column_list = [User.id]

    assert UserAdmin2().get_export_columns() == [("id", User.id)]


def test_export_columns_by_model_columns() -> None:
    class UserAdmin(ModelView, model=User):
        column_export_list = [User.id, User.name]

    assert UserAdmin.column_export_list == [User.id, User.name]


def test_export_columns_by_str_name() -> None:
    class AddressAdmin(ModelView, model=Address):
        column_export_list = ["pk", "user_id"]

    assert AddressAdmin().get_export_columns() == [
        ("pk", Address.pk),
        ("user_id", Address.user_id),
    ]


def test_export_columns_both_include_and_exclude() -> None:
    with pytest.raises(AssertionError) as exc:

        class InvalidAdmin(ModelView, model=User):
            column_export_list = ["id"]
            column_export_exclude_list = ["name"]

    assert exc.match(
        "Cannot use column_export_list and column_export_exclude_list together."
    )


def test_export_excluded_columns_by_str_name() -> None:
    class UserAdmin(ModelView, model=User):
        column_export_exclude_list = ["id"]

    assert UserAdmin().get_export_columns() == [
        ("addresses", User.addresses.prop),
        ("profile", User.profile.prop),
        ("name", User.name),
    ]


def test_export_excluded_columns_by_model_column() -> None:
    class UserAdmin(ModelView, model=User):
        column_export_exclude_list = [User.id]

    assert UserAdmin().get_export_columns() == [
        ("addresses", User.addresses.prop),
        ("profile", User.profile.prop),
        ("name", User.name),
    ]


@pytest.mark.skipif(engine.name != "postgresql", reason="PostgreSQL only")
def test_get_python_type_postgresql() -> None:
    class PostgresModel(Base):
        __tablename__ = "postgres_model"

        uuid = Column(UUID, primary_key=True)

    get_column_python_type(PostgresModel.uuid) is str


def test_model_default_sort() -> None:
    class UserAdmin(ModelView, model=User):
        ...

    assert UserAdmin()._get_default_sort() == [("id", False)]

    class UserAdmin(ModelView, model=User):
        column_default_sort = "name"

    assert UserAdmin()._get_default_sort() == [("name", False)]

    class UserAdmin(ModelView, model=User):
        column_default_sort = ("name", True)

    assert UserAdmin()._get_default_sort() == [("name", True)]

    class UserAdmin(ModelView, model=User):
        column_default_sort = [("name", True), ("id", False)]

    assert UserAdmin()._get_default_sort() == [("name", True), ("id", False)]


async def test_get_model_objects_uses_list_query() -> None:
    session = LocalSession()
    batman = User(name="batman")
    session.add(batman)
    session.commit()
    session.refresh(batman)
    session.close()

    class UserAdmin(ModelView, model=User):
        async_engine = False
        sessionmaker = LocalSession

    view = UserAdmin()

    view.list_query = select(User).filter(User.name.endswith("man"))
    assert len(await view.get_model_objects()) == 1

    view.list_query = select(User).filter(User.name.endswith("man").is_(False))
    assert len(await view.get_model_objects()) == 0


def test_url_for() -> None:
    class UserAdmin(ModelView, model=User):
        ...

    view = UserAdmin()
    request = Request({"type": "http"})
    user = User(id=1)
    address = Address(pk=2, user=user)

    with patch("starlette.requests.Request.url_for", Mock()) as mock:
        view._url_for_details(request, user)
        view._url_for_edit(request, address)
        view._url_for_delete(request, address)

    assert mock.call_args_list == [
        call("admin:details", identity="user", pk=1),
        call("admin:edit", identity="address", pk=2),
        call("admin:delete", identity="address"),
    ]


def test_model_columns_all_keyword() -> None:
    class AddressAdmin(ModelView, model=Address):
        column_list = "__all__"
        column_details_list = "__all__"

    all_columns = [
        ("user", Address.user.prop),
        ("pk", Address.pk),
        ("user_id", Address.user_id),
    ]

    assert AddressAdmin().get_list_columns() == all_columns
    assert AddressAdmin().get_details_columns() == all_columns


def test_get_prop_value() -> None:
    class UserAdmin(ModelView, model=User):
        ...

    user = User(name="batman", role=Role.ADMIN, status=Status.ACTIVE)

    assert UserAdmin().get_prop_value(user, User.name) == "batman"
    assert UserAdmin().get_prop_value(user, User.role) == "ADMIN"
    assert UserAdmin().get_prop_value(user, User.status) == "ACTIVE"
