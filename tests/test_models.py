from typing import Any

import pytest
from sqlalchemy import Column, ForeignKey, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, relationship, sessionmaker
from starlette.applications import Starlette

from sqladmin import Admin, ModelAdmin
from sqladmin.exceptions import InvalidColumnError, InvalidModelError
from tests.common import TEST_DATABASE_URI

Base = declarative_base()  # type: Any

engine = create_engine(TEST_DATABASE_URI, connect_args={"check_same_thread": False})

LocalSession = sessionmaker(bind=engine)

db: Session = LocalSession()

app = Starlette()
admin = Admin(app=app, db=db)


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
    assert UserAdmin.db is None
    assert UserAdmin.pk_column == User.id
    assert UserAdmin.identity == "user"

    class AddressAdmin(ModelAdmin, model=Address, db=db):
        pass

    assert AddressAdmin.model == Address
    assert AddressAdmin.db == db


def test_setup_with_invalid_sqlalchemy_model() -> None:
    with pytest.raises(InvalidModelError) as exc:

        class AddressAdmin(ModelAdmin, model=Starlette):
            pass

    assert exc.match("Class Starlette is not a SQLAlchemy model.")


def test_column_list_default() -> None:
    class UserAdmin(ModelAdmin, model=User):
        pass

    assert UserAdmin.column_list == [User.id]


def test_column_list_by_model_columns() -> None:
    class UserAdmin(ModelAdmin, model=User):
        column_list = [User.id, User.name]

    assert UserAdmin.column_list == [User.id, User.name]


def test_column_list_by_str_name() -> None:
    class AddressAdmin(ModelAdmin, model=Address):
        column_list = ["id", "user_id"]

    assert AddressAdmin.column_list == [Address.id, Address.user_id]


def test_column_list_invalid_attribute() -> None:
    with pytest.raises(InvalidColumnError) as exc:

        class ExampleAdmin(ModelAdmin, model=Address):
            column_list = ["example"]

    assert exc.match("Model 'Address' has no attribute 'example'.")


def test_column_list_both_include_and_exclude() -> None:
    with pytest.raises(Exception) as exc:

        class InvalidAdmin(ModelAdmin, model=User):
            column_list = ["id"]
            column_exclude_list = ["name"]

    assert exc.match("Cannot use 'column_list' and 'column_exclude_list' together.")


def test_column_exclude_list_by_str_name() -> None:
    class UserAdmin(ModelAdmin, model=User):
        column_exclude_list = ["id"]

    assert UserAdmin.column_list == [User.name]


def test_column_exclude_list_by_model_column() -> None:
    class UserAdmin(ModelAdmin, model=User):
        column_exclude_list = [User.id]

    assert UserAdmin.column_list == [User.name]


def test_column_details_list_both_include_and_exclude() -> None:
    with pytest.raises(Exception) as exc:

        class InvalidAdmin(ModelAdmin, model=User):
            column_details_list = ["id"]
            column_details_exclude_list = ["name"]

    assert exc.match(
        "Cannot use 'column_details_list' and 'column_details_exclude_list' together."
    )


def test_column_details_list_default() -> None:
    class UserAdmin(ModelAdmin, model=User):
        pass

    assert UserAdmin.column_details_list == [User.id, User.name]


def test_column_details_list_by_model_column() -> None:
    class UserAdmin(ModelAdmin, model=User):
        column_details_list = [User.name, User.id]

    assert UserAdmin.column_details_list == [User.name, User.id]


def test_column_details_exclude_list_by_model_column() -> None:
    class UserAdmin(ModelAdmin, model=User):
        column_details_exclude_list = [User.id]

    assert UserAdmin.column_details_list == [User.name]
