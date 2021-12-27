from typing import TYPE_CHECKING, List, Type

from jinja2 import ChoiceLoader, FileSystemLoader, PackageLoader
from sqlalchemy.orm import Session
from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Mount, Route, Router
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

if TYPE_CHECKING:
    from sqladmin.models import ModelAdmin


class BaseAdmin:
    def __init__(self, app: Starlette, db: Session, base_url: str = "/admin") -> None:
        self.app = app
        self.db = db
        self.base_url = base_url
        self._model_admins: List[Type["ModelAdmin"]] = []

        self.templates = Jinja2Templates("templates")
        self.templates.env.loader = ChoiceLoader(
            [
                FileSystemLoader("templates"),
                PackageLoader("sqladmin", "templates"),
            ]
        )
        self.templates.env.globals["min"] = min

    @property
    def model_admins(self) -> List[Type["ModelAdmin"]]:
        """
        Get list of model_admins lazily.
        """

        return self._model_admins

    def _find_model_admin(self, identity: str) -> Type["ModelAdmin"]:
        for model_admin in self.model_admins:
            if model_admin.identity == identity:
                return model_admin

        raise HTTPException(status_code=404)

    def register_model(self, model: Type["ModelAdmin"]) -> None:
        # Set global db if it's not set per model
        if model.db is None:
            model.db = self.db

        self._model_admins.append(model)


class Admin(BaseAdmin):
    def __init__(self, app: Starlette, db: Session, base_url: str = "/admin") -> None:
        super().__init__(app=app, db=db, base_url=base_url)

        statics = StaticFiles(packages=["sqladmin"])

        router = Router(
            routes=[
                Mount("/statics", app=statics, name="statics"),
                Route("/", endpoint=self.index, name="index"),
                Route("/{identity}/list", endpoint=self.list, name="list"),
            ]
        )
        self.app.mount(base_url, app=router, name="admin")

        self.templates.env.globals["model_admins"] = self.model_admins

    async def index(self, request: Request) -> Response:
        return self.templates.TemplateResponse("index.html", {"request": request})

    async def list(self, request: Request) -> Response:
        model_admin = self._find_model_admin(request.path_params["identity"])
        pagination = await model_admin.paginate(request)

        context = {
            "request": request,
            "model_admin": model_admin,
            "pagination": pagination,
        }

        return self.templates.TemplateResponse("list.html", context)
