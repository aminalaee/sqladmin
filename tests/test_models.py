from typing import Any

import pytest
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from starlette.applications import Starlette

from sqladmin import Admin, ModelAdmin
from sqladmin.exceptions import InvalidColumnError, InvalidModelError
from tests.common import sync_engine as engine

Base = declarative_base()  # type: Any

LocalSession = sessionmaker(bind=engine)

app = Starlette()
admin = Admin(app=app, engine=engine)


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


def test_model_setup() -> None:
    class UserAdmin(ModelAdmin, model=User):
        pass

    assert UserAdmin.model == User
    assert UserAdmin.pk_column == User.id

    class AddressAdmin(ModelAdmin, model=Address):
        pass

    assert AddressAdmin.model == Address


def test_metadata_setup() -> None:
    class UserAdmin(ModelAdmin, model=User):
        pass

    assert UserAdmin.identity == "user"
    assert UserAdmin.name == "User"
    assert UserAdmin.name_plural == "Users"

    class TempModel(User):
        pass

    class TempAdmin(ModelAdmin, model=TempModel):
        icon = "fas fa-user"

    assert TempAdmin.icon == "fas fa-user"
    assert TempAdmin.identity == "temp-model"
    assert TempAdmin.name == "Temp Model"
    assert TempAdmin.name_plural == "Temp Models"


def test_setup_with_invalid_sqlalchemy_model() -> None:
    with pytest.raises(InvalidModelError) as exc:

        class AddressAdmin(ModelAdmin, model=Starlette):
            pass

    assert exc.match("Class Starlette is not a SQLAlchemy model.")


def test_column_list_default() -> None:
    class UserAdmin(ModelAdmin, model=User):
        pass

    assert UserAdmin().get_list_columns() == [("id", User.id)]


def test_column_list_by_model_columns() -> None:
    class UserAdmin(ModelAdmin, model=User):
        column_list = [User.id, User.name]

    assert UserAdmin.column_list == [User.id, User.name]


def test_column_list_by_str_name() -> None:
    class AddressAdmin(ModelAdmin, model=Address):
        column_list = ["id", "user_id"]

    assert AddressAdmin().get_list_columns() == [
        ("id", Address.id),
        ("user_id", Address.user_id),
    ]


def test_column_list_invalid_attribute() -> None:
    class ExampleAdmin(ModelAdmin, model=Address):
        column_list = ["example"]

    with pytest.raises(InvalidColumnError) as exc:
        ExampleAdmin().get_list_columns()

    assert exc.match("Model 'Address' has no attribute 'example'.")


def test_column_list_both_include_and_exclude() -> None:
    with pytest.raises(AssertionError) as exc:

        class InvalidAdmin(ModelAdmin, model=User):
            column_list = ["id"]
            column_exclude_list = ["name"]

    assert exc.match("Cannot use column_list and column_exclude_list together.")


def test_column_exclude_list_by_str_name() -> None:
    class UserAdmin(ModelAdmin, model=User):
        column_exclude_list = ["id"]

    assert sorted(UserAdmin().get_list_columns()) == [
        ("addresses", User.addresses.prop),
        ("name", User.name),
    ]


def test_column_exclude_list_by_model_column() -> None:
    class UserAdmin(ModelAdmin, model=User):
        column_exclude_list = [User.id]

    assert sorted(UserAdmin().get_list_columns()) == [
        ("addresses", User.addresses.prop),
        ("name", User.name),
    ]


def test_column_details_list_both_include_and_exclude() -> None:
    with pytest.raises(AssertionError) as exc:

        class InvalidAdmin(ModelAdmin, model=User):
            column_details_list = ["id"]
            column_details_exclude_list = ["name"]

    assert exc.match(
        "Cannot use column_details_list and column_details_exclude_list together."
    )


def test_column_details_list_default() -> None:
    class UserAdmin(ModelAdmin, model=User):
        pass

    assert UserAdmin().get_details_columns() == [
        ("addresses", User.addresses.prop),
        ("id", User.id),
        ("name", User.name),
    ]


def test_column_details_list_by_model_column() -> None:
    class UserAdmin(ModelAdmin, model=User):
        column_details_list = [User.name, User.id]

    assert UserAdmin().get_details_columns() == [("name", User.name), ("id", User.id)]


def test_column_details_exclude_list_by_model_column() -> None:
    class UserAdmin(ModelAdmin, model=User):
        column_details_exclude_list = [User.id]

    assert sorted(UserAdmin().get_details_columns()) == [
        ("addresses", User.addresses.prop),
        ("name", User.name),
    ]


def test_column_labels_by_string_name() -> None:
    class UserAdmin(ModelAdmin, model=User):
        column_list = [User.name]
        column_labels = {"name": "Name"}

    assert UserAdmin().get_list_columns() == [("Name", User.name)]

    class AddressAdmin(ModelAdmin, model=Address):
        column_details_list = [Address.user_id]
        column_labels = {"user_id": "User ID"}

    assert AddressAdmin().get_details_columns() == [("User ID", Address.user_id)]


def test_column_labels_by_model_columns() -> None:
    class UserAdmin(ModelAdmin, model=User):
        column_list = [User.name]
        column_labels = {User.name: "Name"}

    assert UserAdmin().get_list_columns() == [("Name", User.name)]

    class AddressAdmin(ModelAdmin, model=Address):
        column_details_list = [Address.user_id]
        column_labels = {Address.user_id: "User ID"}

    assert AddressAdmin().get_details_columns() == [("User ID", Address.user_id)]
