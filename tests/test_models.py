import enum
from typing import Generator
from unittest.mock import Mock, call, patch

import pytest
from markupsafe import Markup
from sqlalchemy import Boolean, Column, Enum, ForeignKey, Integer, String, select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from starlette.applications import Starlette
from starlette.requests import Request

from sqladmin import Admin, ModelView
from sqladmin.exceptions import InvalidModelError
from sqladmin.helpers import get_column_python_type
from tests.common import sync_engine as engine

pytestmark = pytest.mark.anyio

Base = declarative_base()  # type: ignore
session_maker = sessionmaker(bind=engine)

app = Starlette()
admin = Admin(app=app, session_maker=session_maker)


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

    addresses = relationship("Address", back_populates="user")
    profile = relationship("Profile", back_populates="user", uselist=False)

    @property
    def name_with_id(self) -> str:
        return f"{self.name} - {self.id}"


class Address(Base):
    __tablename__ = "addresses"

    pk = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    user = relationship("User", back_populates="addresses")


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True)
    is_active = Column(Boolean)
    role = Column(Enum(Role))
    status = Column(Enum(Status))
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

    assert UserAdmin().get_list_columns() == ["id"]


def test_column_list_by_model_columns() -> None:
    class UserAdmin(ModelView, model=User):
        column_list = [User.id, User.name]

    assert UserAdmin().get_list_columns() == ["id", "name"]


def test_column_list_by_str_name() -> None:
    class AddressAdmin(ModelView, model=Address):
        column_list = ["pk", "user_id"]

    assert AddressAdmin().get_list_columns() == ["pk", "user_id"]


def test_column_list_both_include_and_exclude() -> None:
    with pytest.raises(AssertionError) as exc:

        class InvalidAdmin(ModelView, model=User):
            column_list = ["id"]
            column_exclude_list = ["name"]

    assert exc.match("Cannot use column_list and column_exclude_list together.")


def test_column_exclude_list_by_str_name() -> None:
    class UserAdmin(ModelView, model=User):
        column_exclude_list = ["id"]

    assert UserAdmin().get_list_columns() == ["addresses", "profile", "name"]


def test_column_exclude_list_by_model_column() -> None:
    class UserAdmin(ModelView, model=User):
        column_exclude_list = [User.id]

    assert UserAdmin().get_list_columns() == ["addresses", "profile", "name"]


def test_column_list_formatters() -> None:
    class UserAdmin(ModelView, model=User):
        column_formatters = {
            "id": lambda *args: 2,
            User.name: lambda m, a: m.name[:1],
        }

    user = User(id=1, name="Long Name")

    assert UserAdmin().get_list_value(user, "id")[0] == 1
    assert UserAdmin().get_list_value(user, "id")[1] == 2
    assert UserAdmin().get_list_value(user, "name")[0] == "Long Name"
    assert UserAdmin().get_list_value(user, "name")[1] == "L"


def test_column_formatters_detail() -> None:
    class UserAdmin(ModelView, model=User):
        column_formatters_detail = {
            "id": lambda *args: 2,
            User.name: lambda m, a: m.name[:1],
        }

    user = User(id=1, name="Long Name")

    assert UserAdmin().get_detail_value(user, "id")[0] == 1
    assert UserAdmin().get_detail_value(user, "id")[1] == 2
    assert UserAdmin().get_detail_value(user, "name")[0] == "Long Name"
    assert UserAdmin().get_detail_value(user, "name")[1] == "L"


def test_column_formatters_default() -> None:
    class ProfileAdmin(ModelView, model=Profile):
        ...

    user = User(id=1, name="Long Name")
    profile = Profile(user=user, is_active=True)

    assert ProfileAdmin().get_list_value(profile, "is_active") == (
        True,
        Markup("<i class='fa fa-check text-success'></i>"),
    )
    assert ProfileAdmin().get_detail_value(profile, "is_active") == (
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

    assert UserAdmin().get_details_columns() == ["addresses", "profile", "id", "name"]


def test_column_details_list_by_model_column() -> None:
    class UserAdmin(ModelView, model=User):
        column_details_list = [User.name, User.id]

    assert UserAdmin().get_details_columns() == ["name", "id"]


def test_column_details_exclude_list_by_model_column() -> None:
    class UserAdmin(ModelView, model=User):
        column_details_exclude_list = [User.id]

    assert UserAdmin().get_details_columns() == ["addresses", "profile", "name"]


def test_form_columns_default() -> None:
    class UserAdmin(ModelView, model=User):
        pass

    assert UserAdmin().get_form_columns() == ["addresses", "profile", "id", "name"]


def test_form_columns_by_model_columns() -> None:
    class UserAdmin(ModelView, model=User):
        form_columns = [User.id, User.name]

    assert UserAdmin().get_form_columns() == ["id", "name"]


def test_form_columns_by_str_name() -> None:
    class AddressAdmin(ModelView, model=Address):
        form_columns = ["pk", "user_id"]

    assert AddressAdmin().get_form_columns() == ["pk", "user_id"]


def test_form_columns_both_include_and_exclude() -> None:
    with pytest.raises(AssertionError) as exc:

        class InvalidAdmin(ModelView, model=User):
            form_columns = ["id"]
            form_excluded_columns = ["name"]

    assert exc.match("Cannot use form_columns and form_excluded_columns together.")


def test_form_excluded_columns_by_str_name() -> None:
    class UserAdmin(ModelView, model=User):
        form_excluded_columns = ["id"]

    assert UserAdmin().get_form_columns() == ["addresses", "profile", "name"]


def test_form_excluded_columns_by_model_column() -> None:
    class UserAdmin(ModelView, model=User):
        form_excluded_columns = [User.id]

    assert UserAdmin().get_form_columns() == ["addresses", "profile", "name"]


def test_export_columns_default() -> None:
    class UserAdmin(ModelView, model=User):
        pass

    assert UserAdmin().get_export_columns() == ["id"]


def test_export_columns_default_to_list_columns() -> None:
    class UserAdmin(ModelView, model=User):
        column_list = [User.id, User.name]

    assert UserAdmin().get_export_columns() == ["id", "name"]

    class UserAdmin2(ModelView, model=User):
        column_list = [User.id]

    assert UserAdmin2().get_export_columns() == ["id"]


def test_export_columns_by_model_columns() -> None:
    class UserAdmin(ModelView, model=User):
        column_export_list = [User.id, User.name]

    assert UserAdmin().get_export_columns() == ["id", "name"]


def test_export_columns_by_str_name() -> None:
    class AddressAdmin(ModelView, model=Address):
        column_export_list = ["pk", "user_id"]

    assert AddressAdmin().get_export_columns() == ["pk", "user_id"]


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

    assert UserAdmin().get_export_columns() == ["addresses", "profile", "name"]


def test_export_excluded_columns_by_model_column() -> None:
    class UserAdmin(ModelView, model=User):
        column_export_exclude_list = [User.id]

    assert UserAdmin().get_export_columns() == ["addresses", "profile", "name"]


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
    session = session_maker()
    batman = User(name="batman")
    session.add(batman)
    session.commit()
    session.refresh(batman)
    session.close()

    class UserAdmin(ModelView, model=User):
        async_engine = False
        session_maker = session_maker

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

    assert AddressAdmin().get_list_columns() == ["user", "pk", "user_id"]
    assert AddressAdmin().get_details_columns() == ["user", "pk", "user_id"]


def test_get_prop_value() -> None:
    class ProfileAdmin(ModelView, model=Profile):
        ...

    profile = Profile(is_active=True, role=Role.ADMIN, status=Status.ACTIVE)

    assert ProfileAdmin().get_prop_value(profile, "is_active") is True
    assert ProfileAdmin().get_prop_value(profile, "role") == "ADMIN"
    assert ProfileAdmin().get_prop_value(profile, "status") == "ACTIVE"


def test_model_property_in_columns() -> None:
    class UserAdmin(ModelView, model=User):
        column_list = ["id", "name", "name_with_id"]

    user = User(id=1, name="batman")

    assert UserAdmin().get_list_columns() == ["id", "name", "name_with_id"]
    assert UserAdmin().get_details_columns() == ["addresses", "profile", "id", "name"]
    assert UserAdmin().get_prop_value(user, "name_with_id") == "batman - 1"
