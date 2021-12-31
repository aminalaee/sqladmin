from typing import TYPE_CHECKING, List, Type, Union

from jinja2 import ChoiceLoader, FileSystemLoader, PackageLoader
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine
from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Mount, Route, Router
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

if TYPE_CHECKING:
    from sqladmin.models import ModelAdmin


__all__ = [
    "Admin",
]


class BaseAdmin:
    def __init__(
        self,
        app: Starlette,
        engine: Union[Engine, AsyncEngine],
        base_url: str = "/admin",
    ) -> None:
        self.app = app
        self.engine = engine
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

    def _not_found_response(self, request: Request) -> Response:
        context = {"request": request, "status_code": 404, "message": "Not found."}
        return self.templates.TemplateResponse("error.html", context, status_code=404)

    def _unathorized_response(self, request: Request) -> Response:
        context = {"request": request, "status_code": 401, "message": "Unauthorized."}
        return self.templates.TemplateResponse("error.html", context, status_code=401)

    def register_model(self, model: Type["ModelAdmin"]) -> None:
        """
        Register ModelAdmin to the Admin.

        Usage:
            from sqladmin import Admin, ModelAdmin

            class UserAdmin(ModelAdmin, model=User):
                pass

            admin.register_model(UserAdmin)
        """

        # Set database engine from Admin instance
        model.engine = self.engine
        model.session_maker = model._get_sessionmaker(model.engine)

        self._model_admins.append(model)


class Admin(BaseAdmin):
    """
    Main entrypoint to admin interface.
    """

    def __init__(
        self,
        app: Starlette,
        engine: Union[Engine, AsyncEngine],
        base_url: str = "/admin",
    ) -> None:
        """
        :param app:
            Starlette application instance
        :param db:
            SQLAlchemy database session.
        :param base_url:
            Base url for admin application.
        """

        super().__init__(app=app, engine=engine, base_url=base_url)

        statics = StaticFiles(packages=["sqladmin"])

        router = Router(
            routes=[
                Mount("/statics", app=statics, name="statics"),
                Route("/", endpoint=self.index, name="index"),
                Route("/{identity}/list", endpoint=self.list, name="list"),
                Route("/{identity}/detail/{pk}", endpoint=self.detail, name="detail"),
            ]
        )
        self.app.mount(base_url, app=router, name="admin")

        self.templates.env.globals["model_admins"] = self.model_admins

    async def index(self, request: Request) -> Response:
        """
        Index view for admin app which can be overriden.
        """

        return self.templates.TemplateResponse("index.html", {"request": request})

    async def list(self, request: Request) -> Response:
        """
        List view for model showing paginated list of items.
        """

        model_admin = self._find_model_admin(request.path_params["identity"])
        pagination = await model_admin.paginate(request)

        context = {
            "request": request,
            "model_admin": model_admin,
            "pagination": pagination,
        }

        return self.templates.TemplateResponse("list.html", context)

    async def detail(self, request: Request) -> Response:
        model_admin = self._find_model_admin(request.path_params["identity"])
        if not model_admin.can_view_details:
            return self._unathorized_response(request)

        model = await model_admin.get_model_by_pk(request.path_params["pk"])
        if not model:
            return self._not_found_response(request)

        context = {
            "request": request,
            "model_admin": model_admin,
            "model": model,
            "title": model_admin.name,
        }

        return self.templates.TemplateResponse("detail.html", context)
