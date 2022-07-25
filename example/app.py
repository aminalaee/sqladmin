from fastapi import FastAPI, APIRouter
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from starlette.requests import Request

from sqladmin import Admin, ModelAdmin
from sqladmin.models import BaseView

Base = declarative_base()
engine = create_engine(
    "sqlite:///example.db",
    connect_args={"check_same_thread": False},
)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String)


Base.metadata.create_all(engine)

app = FastAPI()
admin = Admin(app, engine,
              templates_dir='tpl'
              )


class UserAdmin(ModelAdmin, model=User):
    column_list = [User.id, User.name]


admin.register_model(UserAdmin)


class CustomAdmin(BaseView):
    def test_page(self, request: Request):
        return self.templates.TemplateResponse("custom.html", context={"request": request})

    name_plural = "Test me"
    icon = "fa-user"
    path = "/custom/test_page"
    methods = ["GET"]
    endpoint = test_page


admin.register_view(CustomAdmin)
