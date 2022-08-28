from typing import Any, Generator

import pytest
from markupsafe import Markup
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from starlette.applications import Starlette

from sqladmin import Admin, ModelView
from sqladmin.exceptions import InvalidColumnError, InvalidModelError
from sqladmin.helpers import get_column_python_type
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


class Address(Base):
    __tablename__ = "addresses"

    id = Column(Integer, primary_key=True)
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


def test_model_setup() -> None:
    class UserAdmin(ModelView, model=User):
        pass

    assert UserAdmin.model == User
    assert UserAdmin.pk_column == User.id

    class AddressAdmin(ModelView, model=Address):
        pass

    assert AddressAdmin.model == Address

    class ProfileAdmin(ModelView, model=Profile):
        pass

    assert ProfileAdmin.model == Profile


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
        column_list = ["id", "user_id"]

    assert sorted(AddressAdmin().get_list_columns()) == [
        ("id", Address.id),
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

    assert sorted(UserAdmin().get_list_columns()) == [
        ("addresses", User.addresses.prop),
        ("name", User.name),
        ("profile", User.profile.prop),
    ]


def test_column_exclude_list_by_model_column() -> None:
    class UserAdmin(ModelView, model=User):
        column_exclude_list = [User.id]

    assert sorted(UserAdmin().get_list_columns()) == [
        ("addresses", User.addresses.prop),
        ("name", User.name),
        ("profile", User.profile.prop),
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

    assert sorted(UserAdmin().get_details_columns()) == [
        ("addresses", User.addresses.prop),
        ("id", User.id),
        ("name", User.name),
        ("profile", User.profile.prop),
    ]


def test_column_details_list_by_model_column() -> None:
    class UserAdmin(ModelView, model=User):
        column_details_list = [User.name, User.id]

    assert UserAdmin().get_details_columns() == [("name", User.name), ("id", User.id)]


def test_column_details_exclude_list_by_model_column() -> None:
    class UserAdmin(ModelView, model=User):
        column_details_exclude_list = [User.id]

    assert sorted(UserAdmin().get_details_columns()) == [
        ("addresses", User.addresses.prop),
        ("name", User.name),
        ("profile", User.profile.prop),
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

    assert UserAdmin().get_model_attr("name") == User.name
    assert UserAdmin().get_model_attr(User.name) == User.name


def test_get_model_attr_by_column_labels() -> None:
    class UserAdmin(ModelView, model=User):
        column_labels = {User.name: "Name"}

    assert UserAdmin().get_model_attr("Name") == User.name
    assert UserAdmin().get_model_attr("name") == User.name
    assert UserAdmin().get_model_attr(User.name) == User.name


def test_form_columns_default() -> None:
    class UserAdmin(ModelView, model=User):
        pass

    assert sorted(UserAdmin().get_form_columns()) == [
        ("addresses", User.addresses.prop),
        ("id", User.id),
        ("name", User.name),
        ("profile", User.profile.prop),
    ]


def test_form_columns_by_model_columns() -> None:
    class UserAdmin(ModelView, model=User):
        form_columns = [User.id, User.name]

    assert UserAdmin.form_columns == [User.id, User.name]


def test_form_columns_by_str_name() -> None:
    class AddressAdmin(ModelView, model=Address):
        form_columns = ["id", "user_id"]

    assert sorted(AddressAdmin().get_form_columns()) == [
        ("id", Address.id),
        ("user_id", Address.user_id),
    ]


def test_form_columns_invalid_attribute() -> None:
    class ExampleAdmin(ModelView, model=Address):
        form_columns = ["example"]

    with pytest.raises(InvalidColumnError) as exc:
        ExampleAdmin().get_form_columns()

    assert exc.match("Model 'Address' has no attribute 'example'.")


def test_form_columns_both_include_and_exclude() -> None:
    with pytest.raises(AssertionError) as exc:

        class InvalidAdmin(ModelView, model=User):
            form_columns = ["id"]
            form_excluded_columns = ["name"]

    assert exc.match("Cannot use form_columns and form_excluded_columns together.")


def test_form_excluded_columns_by_str_name() -> None:
    class UserAdmin(ModelView, model=User):
        form_excluded_columns = ["id"]

    assert sorted(UserAdmin().get_form_columns()) == [
        ("addresses", User.addresses.prop),
        ("name", User.name),
        ("profile", User.profile.prop),
    ]


def test_form_excluded_columns_by_model_column() -> None:
    class UserAdmin(ModelView, model=User):
        form_excluded_columns = [User.id]

    assert sorted(UserAdmin().get_form_columns()) == [
        ("addresses", User.addresses.prop),
        ("name", User.name),
        ("profile", User.profile.prop),
    ]


def test_export_columns_default() -> None:
    class UserAdmin(ModelView, model=User):
        pass

    assert sorted(UserAdmin().get_export_columns()) == [
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
        column_export_list = ["id", "user_id"]

    assert AddressAdmin().get_export_columns() == [
        ("id", Address.id),
        ("user_id", Address.user_id),
    ]


def test_export_columns_invalid_attribute() -> None:
    class ExampleAdmin(ModelView, model=Address):
        column_export_list = ["example"]

    with pytest.raises(InvalidColumnError) as exc:
        ExampleAdmin().get_export_columns()

    assert exc.match("Model 'Address' has no attribute 'example'.")


def test_export_columns_both_include_and_exclude() -> None:
    with pytest.raises(AssertionError) as exc:

        class InvalidAdmin(ModelView, model=User):
            column_export_list = ["id"]
            column_export_exclude_list = ["name"]

    assert exc.match(
        "Cannot use column_export_list and" " column_export_exclude_list together."
    )


def test_export_excluded_columns_by_str_name() -> None:
    class UserAdmin(ModelView, model=User):
        column_export_exclude_list = ["id"]

    assert sorted(UserAdmin().get_export_columns()) == [
        ("addresses", User.addresses.prop),
        ("name", User.name),
        ("profile", User.profile.prop),
    ]


def test_export_excluded_columns_by_model_column() -> None:
    class UserAdmin(ModelView, model=User):
        column_export_exclude_list = [User.id]

    assert sorted(UserAdmin().get_export_columns()) == [
        ("addresses", User.addresses.prop),
        ("name", User.name),
        ("profile", User.profile.prop),
    ]


@pytest.mark.skipif(engine.name != "postgresql", reason="PostgreSQL only")
def test_get_python_type_postgresql() -> None:
    class PostgresModel(Base):
        __tablename__ = "postgres_model"

        uuid = Column(UUID, primary_key=True)

    get_column_python_type(PostgresModel.uuid) is str


def test_get_url_for_details_from_object() -> None:
    class UserAdmin(ModelView, model=User):
        ...

    admin = Admin(app=Starlette(), engine=engine)
    admin.add_view(UserAdmin)

    with Session() as session:
        user = User()
        session.add(user)
        session.commit()

        url = UserAdmin()._url_for_details(user)

    assert url == "/admin/user/details/1"


def test_get_url_for_details_from_object_with_attr() -> None:
    class UserAdmin(ModelView, model=User):
        ...

    class AddressAdmin(ModelView, model=Address):
        ...

    admin = Admin(app=Starlette(), engine=engine)
    admin.add_view(UserAdmin)
    admin.add_view(AddressAdmin)

    with Session() as session:
        user = User()
        session.add(user)
        session.flush()

        address = Address(user_id=user.id)
        session.add(address)
        session.commit()

        address2 = Address()
        session.add(address2)
        session.commit()

        url = UserAdmin()._url_for_details_with_attr(address, Address.user)
        url_empty = UserAdmin()._url_for_details_with_attr(address2, Address.user)

    assert url == "/admin/user/details/1"
    assert url_empty == ""


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
