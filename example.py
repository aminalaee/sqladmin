from fastapi import FastAPI, APIRouter
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from starlette.requests import Request

from sqladmin import Admin, ModelAdmin

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
admin = Admin(app, engine)


class UserAdmin(ModelAdmin, model=User):
    column_list = [User.id, User.name]


admin.register_model(UserAdmin)


class CustomAdmin:
    template_path = 'tpl'
    custom_admin_router = APIRouter(prefix='/custom_admin')

    def __init__(self):
        self.custom_admin_router.add_api_route("/hmlt", self.test_html, methods=["GET"], name="Test me")

    def render(self, template, data):
        return admin.templates.TemplateResponse(template, data)

    def test_html(self, request: Request):
        return self.render("sample.html", data={"request": request})


admin.register_view(CustomAdmin)
