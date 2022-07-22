from fastapi import FastAPI, APIRouter
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from starlette.requests import Request

from sqladmin import Admin, ModelAdmin
from sqladmin.models import ModelView

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
              template_path='tpl'
              )


class UserAdmin(ModelAdmin, model=User):
    column_list = [User.id, User.name]


admin.register_model(UserAdmin)


class CustomAdmin(ModelView):
    def test_html(self, request: Request):
        return self.templates.TemplateResponse("sample.html", context={"request": request})

    name = "Test me"
    icon = "fa-user"
    path = "/custom/hmlt"
    methods = ["GET"]
    endpoint = test_html


admin.register_view(CustomAdmin)
