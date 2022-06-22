from typing import TYPE_CHECKING, List, Sequence, Type, Union

from jinja2 import ChoiceLoader, FileSystemLoader, PackageLoader
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import Session, sessionmaker
from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from sqladmin.utils import is_iterable

if TYPE_CHECKING:
    from sqladmin.models import ModelAdmin


__all__ = [
    "Admin",
]


class BaseAdmin:
    """Base class for implementing Admin interface.

    Danger:
        This class should almost never be used directly.
    """

    def __init__(
        self,
        app: Starlette,
        engine: Union[Engine, AsyncEngine],
        base_url: str = "/admin",
        title: str = "Admin",
        logo_url: str = None,
    ) -> None:
        self.app = app
        self.engine = engine
        self.base_url = base_url
        self._model_admins: List["ModelAdmin"] = []

        self.templates = Jinja2Templates("templates")
        self.templates.env.loader = ChoiceLoader(
            [
                FileSystemLoader("templates"),
                PackageLoader("sqladmin", "templates"),
            ]
        )
        self.templates.env.globals["min"] = min
        self.templates.env.globals["admin_title"] = title
        self.templates.env.globals["admin_logo_url"] = logo_url
        self.templates.env.globals["model_admins"] = self.model_admins
        self.templates.env.globals["is_iterable"] = is_iterable

    @property
    def model_admins(self) -> List["ModelAdmin"]:
        """Get list of ModelAdmins lazily.

        Returns:
            List of ModelAdmin classes registered in Admin.
        """

        return self._model_admins

    def _find_model_admin(self, identity: str) -> "ModelAdmin":
        for model_admin in self.model_admins:
            if model_admin.identity == identity:
                return model_admin

        raise HTTPException(status_code=404)

    def register_model(self, model: Type["ModelAdmin"]) -> None:
        """Register ModelAdmin to the Admin.

        Args:
            model: ModelAdmin class to register in Admin.

        ???+ usage
            ```python
            from sqladmin import Admin, ModelAdmin

            class UserAdmin(ModelAdmin, model=User):
                pass

            admin.register_model(UserAdmin)
            ```
        """

        # Set database engine from Admin instance
        model.engine = self.engine
        model.url_path_for = self.app.url_path_for

        if isinstance(model.engine, Engine):
            model.sessionmaker = sessionmaker(bind=model.engine, class_=Session)
            model.async_engine = False
        else:
            model.sessionmaker = sessionmaker(bind=model.engine, class_=AsyncSession)
            model.async_engine = True

        self._model_admins.append((model()))


class BaseAdminView(BaseAdmin):
    async def _list(self, request: Request) -> None:
        model_admin = self._find_model_admin(request.path_params["identity"])
        if not model_admin.is_accessible(request):
            raise HTTPException(status_code=403)

    async def _create(self, request: Request) -> None:
        model_admin = self._find_model_admin(request.path_params["identity"])
        if not model_admin.can_create or not model_admin.is_accessible(request):
            raise HTTPException(status_code=403)

    async def _details(self, request: Request) -> None:
        model_admin = self._find_model_admin(request.path_params["identity"])
        if not model_admin.can_view_details or not model_admin.is_accessible(request):
            raise HTTPException(status_code=403)

    async def _delete(self, request: Request) -> None:
        model_admin = self._find_model_admin(request.path_params["identity"])
        if not model_admin.can_delete or not model_admin.is_accessible(request):
            raise HTTPException(status_code=403)

    async def _edit(self, request: Request) -> None:
        model_admin = self._find_model_admin(request.path_params["identity"])
        if not model_admin.can_edit or not model_admin.is_accessible(request):
            raise HTTPException(status_code=403)

    async def _export(self, request: Request) -> None:
        model_admin = self._find_model_admin(request.path_params["identity"])
        if not model_admin.can_export or not model_admin.is_accessible(request):
            raise HTTPException(status_code=403)
        if request.path_params["export_type"] not in model_admin.export_types:
            raise HTTPException(status_code=404)


class Admin(BaseAdminView):
    """Main entrypoint to admin interface.

    ???+ usage
        ```python
        from fastapi import FastAPI
        from sqladmin import Admin, ModelAdmin

        from mymodels import User # SQLAlchemy model


        app = FastAPI()
        admin = Admin(app, engine)


        class UserAdmin(ModelAdmin, model=User):
            column_list = [User.id, User.name]


        admin.register_model(UserAdmin)
        ```
    """

    def __init__(
        self,
        app: Starlette,
        engine: Union[Engine, AsyncEngine],
        base_url: str = "/admin",
        title: str = "Admin",
        logo_url: str = None,
        middlewares: Sequence[Middleware] = None,
        debug: bool = False,
    ) -> None:
        """
        Args:
            app: Starlette or FastAPI application.
            engine: SQLAlchemy engine instance.
            base_url: Base URL for Admin interface.
            title: Admin title.
            logo_url: URL of logo to be displayed instead of title.
        """

        assert isinstance(engine, (Engine, AsyncEngine))
        super().__init__(
            app=app, engine=engine, base_url=base_url, title=title, logo_url=logo_url
        )

        statics = StaticFiles(packages=["sqladmin"])

        def http_exception(request: Request, exc: Exception) -> Response:
            assert isinstance(exc, HTTPException)
            context = {
                "request": request,
                "status_code": exc.status_code,
                "message": exc.detail,
            }
            return self.templates.TemplateResponse(
                "error.html", context, status_code=exc.status_code
            )

        admin = Starlette(
            routes=[
                Mount("/statics", app=statics, name="statics"),
                Route("/", endpoint=self.index, name="index"),
                Route("/{identity}/list", endpoint=self.list, name="list"),
                Route(
                    "/{identity}/details/{pk}", endpoint=self.details, name="details"
                ),
                Route(
                    "/{identity}/delete/{pk}",
                    endpoint=self.delete,
                    name="delete",
                    methods=["DELETE"],
                ),
                Route(
                    "/{identity}/create",
                    endpoint=self.create,
                    name="create",
                    methods=["GET", "POST"],
                ),
                Route(
                    "/{identity}/edit/{pk}",
                    endpoint=self.edit,
                    name="edit",
                    methods=["GET", "POST"],
                ),
                Route(
                    "/{identity}/export/{export_type}",
                    endpoint=self.export,
                    name="export",
                    methods=["GET"],
                ),
            ],
            exception_handlers={HTTPException: http_exception},
            middleware=middlewares,
            debug=debug,
        )
        self.app.mount(base_url, app=admin, name="admin")

    async def index(self, request: Request) -> Response:
        """Index route which can be overridden to create dashboards."""

        return self.templates.TemplateResponse("index.html", {"request": request})

    async def list(self, request: Request) -> Response:
        """List route to display paginated Model instances."""

        await self._list(request)

        model_admin = self._find_model_admin(request.path_params["identity"])

        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("pageSize", 0))
        search = request.query_params.get("search", None)
        sort_by = request.query_params.get("sortBy", None)
        sort = request.query_params.get("sort", None)

        pagination = await model_admin.list(page, page_size, search, sort_by, sort)
        pagination.add_pagination_urls(request.url)

        context = {
            "request": request,
            "model_admin": model_admin,
            "pagination": pagination,
        }

        return self.templates.TemplateResponse(model_admin.list_template, context)

    async def details(self, request: Request) -> Response:
        """Details route."""

        await self._details(request)

        model_admin = self._find_model_admin(request.path_params["identity"])

        model = await model_admin.get_model_by_pk(request.path_params["pk"])
        if not model:
            raise HTTPException(status_code=404)

        context = {
            "request": request,
            "model_admin": model_admin,
            "model": model,
            "title": model_admin.name,
        }

        return self.templates.TemplateResponse(model_admin.details_template, context)

    async def delete(self, request: Request) -> Response:
        """Delete route."""

        await self._delete(request)

        identity = request.path_params["identity"]
        model_admin = self._find_model_admin(identity)

        model = await model_admin.get_model_by_pk(request.path_params["pk"])
        if not model:
            raise HTTPException(status_code=404)

        await model_admin.delete_model(model)

        return Response(content=request.url_for("admin:list", identity=identity))

    async def create(self, request: Request) -> Response:
        """Create model endpoint."""

        await self._create(request)

        identity = request.path_params["identity"]
        model_admin = self._find_model_admin(identity)

        Form = await model_admin.scaffold_form()
        form = Form(await request.form())

        context = {
            "request": request,
            "model_admin": model_admin,
            "form": form,
        }

        if request.method == "GET":
            return self.templates.TemplateResponse(model_admin.create_template, context)

        if not form.validate():
            return self.templates.TemplateResponse(
                model_admin.create_template,
                context,
                status_code=400,
            )

        model = model_admin.model(**form.data)
        await model_admin.insert_model(model)

        return RedirectResponse(
            request.url_for("admin:list", identity=identity),
            status_code=302,
        )

    async def edit(self, request: Request) -> Response:
        """Edit model endpoint."""

        await self._edit(request)

        identity = request.path_params["identity"]
        model_admin = self._find_model_admin(identity)

        model = await model_admin.get_model_by_pk(request.path_params["pk"])
        if not model:
            raise HTTPException(status_code=404)

        Form = await model_admin.scaffold_form()
        context = {
            "request": request,
            "model_admin": model_admin,
        }

        if request.method == "GET":
            context["form"] = Form(obj=model)
            return self.templates.TemplateResponse(model_admin.edit_template, context)

        form = Form(await request.form())
        if not form.validate():
            context["form"] = form
            return self.templates.TemplateResponse(
                model_admin.edit_template,
                context,
                status_code=400,
            )

        await model_admin.update_model(pk=request.path_params["pk"], data=form.data)

        return RedirectResponse(
            request.url_for("admin:list", identity=identity),
            status_code=302,
        )

    async def export(self, request: Request) -> Response:
        """Export model endpoint."""

        await self._export(request)

        identity = request.path_params["identity"]
        export_type = request.path_params["export_type"]

        model_admin = self._find_model_admin(identity)
        rows = await model_admin.get_model_objects(limit=model_admin.export_max_rows)
        return model_admin.export_data(rows, export_type=export_type)
