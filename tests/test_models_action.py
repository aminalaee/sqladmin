from typing import Any, Generator

import pytest
from markupsafe import Markup
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from starlette.applications import Starlette
from starlette.requests import Request

from sqladmin import Admin, ModelView
from sqladmin.application import action
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

@pytest.fixture(autouse=True)
def prepare_database() -> Generator[None, None, None]:
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


def test_model_action() -> None:
    class UserAdmin(ModelView, model=User):
        @action(name='Trigger Update', add_in_detail=True, add_in_list=True)
        async def action_on_user(self, request: Request):
            model = await self.get_model_by_pk(request.path_params["pk"])

            return model.id

    admin = Admin(app=Starlette(), engine=engine)
    admin.add_view(UserAdmin)

    assert UserAdmin.custom_actions_in_list == ['Trigger Update']
    assert UserAdmin.custom_actions_in_detail == ['Trigger Update']

    with Session() as session:
        user = User()
        session.add(user)
        session.commit()

        url = UserAdmin()._url_for_action(user, 'Trigger Update')

    assert url == '/admin/user/action/1/Trigger Update'
