from typing import TYPE_CHECKING, Any, List, Type

from jinja2 import (
    ChoiceLoader,
    Environment,
    FileSystemLoader,
    PackageLoader,
    Template,
    pass_context,
)
from sqlalchemy.orm import Session
from starlette.applications import Starlette
from starlette.background import BackgroundTask
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Mount, Route, Router
from starlette.staticfiles import StaticFiles

if TYPE_CHECKING:
    from sqladmin.models import ModelAdmin


class _TemplateResponse(Response):
    media_type = "text/html"

    def __init__(
        self,
        template: Template,
        context: dict,
        status_code: int = 200,
        headers: dict = None,
        media_type: str = None,
        background: BackgroundTask = None,
    ) -> None:
        self.template = template
        self.context = context
        content = template.render(context)
        super().__init__(content, status_code, headers, media_type, background)


class BaseAdmin:
    def __init__(self, app: Starlette, db: Session, base_url: str = "/admin") -> None:
        self.app = app
        self.db = db
        self.base_url = base_url
        self._model_admins: List[Type["ModelAdmin"]] = []

        loader = ChoiceLoader(
            [
                FileSystemLoader("templates"),
                PackageLoader("sqladmin", "templates"),
            ]
        )
        self.templates = Environment(loader=loader, autoescape=True)
        self.templates.globals["min"] = min

    @property
    def model_admins(self) -> List[Type["ModelAdmin"]]:
        """
        Get list of model_admins lazily.
        """

        return self._model_admins

    def _get_template(self, name: str) -> Template:
        return self.templates.get_template(name)

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

        @pass_context
        def url_for(context: dict, name: str, **path_params: Any) -> str:
            request = context["request"]
            return request.url_for(name, **path_params)

        self.templates.globals["url_for"] = url_for
        self.templates.globals["model_admins"] = self.model_admins

    async def index(self, request: Request) -> _TemplateResponse:
        template = self._get_template("index.html")
        return _TemplateResponse(template, {"request": request})

    async def list(self, request: Request) -> _TemplateResponse:
        template = self._get_template("list.html")
        model_admin = self._find_model_admin(request.path_params["identity"])
        pagination = await model_admin.paginate(request)

        context = {
            "request": request,
            "model_admin": model_admin,
            "pagination": pagination,
        }

        return _TemplateResponse(template, context)
