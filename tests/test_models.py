from typing import Any

import pytest
from sqlalchemy import Column, ForeignKey, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, relationship, sessionmaker
from starlette.applications import Starlette

from sqladmin.application import Admin
from sqladmin.exceptions import InvalidColumnError, InvalidModelError
from sqladmin.models import ModelAdmin

Base = declarative_base()  # type: Any

engine = create_engine("sqlite:///tmp.db", connect_args={"check_same_thread": False})

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


def test_list_display() -> None:
    class UserAdmin(ModelAdmin, model=User):
        list_display = [User.id, User.name]

    class AddressAdmin(ModelAdmin, model=Address):
        list_display = ["id", "user_id"]

    with pytest.raises(InvalidColumnError) as exc:

        class ExampleAdmin(ModelAdmin, model=Address):
            list_display = ["example"]

    assert exc.match("Model 'Address' has no attribute 'example'.")
