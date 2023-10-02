import inspect
import io
import logging
from types import MethodType
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    List,
    Optional,
    Sequence,
    Tuple,
    Type,
    Union,
    cast,
    no_type_check,
)
from urllib.parse import urljoin

from jinja2 import ChoiceLoader, FileSystemLoader, PackageLoader
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.session import Session, sessionmaker
from starlette.applications import Starlette
from starlette.datastructures import URL, FormData, UploadFile
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse, Response
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from sqladmin._menu import CategoryMenu, Menu, ViewMenu
from sqladmin._types import ENGINE_TYPE
from sqladmin.ajax import QueryAjaxModelLoader
from sqladmin.authentication import AuthenticationBackend, login_required
from sqladmin.helpers import (
    get_object_identifier,
    is_async_session_maker,
    slugify_action_name,
)
from sqladmin.models import BaseView, ModelView

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import async_sessionmaker

__all__ = [
    "Admin",
    "expose",
    "action",
]

logger = logging.getLogger(__name__)


class BaseAdmin:
    """Base class for implementing Admin interface.

    Danger:
        This class should almost never be used directly.
    """

    def __init__(
        self,
        app: Starlette,
        engine: Optional[ENGINE_TYPE] = None,
        session_maker: Optional[sessionmaker] = None,
        base_url: str = "/admin",
        title: str = "Admin",
        logo_url: Optional[str] = None,
        templates_dir: str = "templates",
        middlewares: Optional[Sequence[Middleware]] = None,
        authentication_backend: Optional[AuthenticationBackend] = None,
    ) -> None:
        self.app = app
        self.engine = engine
        self.base_url = base_url
        self.templates_dir = templates_dir
        self.title = title
        self.logo_url = logo_url

        if session_maker:
            self.session_maker = session_maker
        elif isinstance(engine, Engine):
            self.session_maker = sessionmaker(bind=self.engine, class_=Session)
        else:
            self.session_maker = sessionmaker(bind=self.engine, class_=AsyncSession)

        self.session_maker.configure(autoflush=False, autocommit=False)
        self.is_async = is_async_session_maker(self.session_maker)

        middlewares = middlewares or []
        self.authentication_backend = authentication_backend
        if authentication_backend:
            middlewares = list(middlewares)
            middlewares.extend(authentication_backend.middlewares)

        self.admin = Starlette(middleware=middlewares)
        self.templates = self.init_templating_engine()
        self._views: List[Union[BaseView, ModelView]] = []
        self._menu = Menu()

    def init_templating_engine(self) -> Jinja2Templates:
        templates = Jinja2Templates("templates")
        loaders = [
            FileSystemLoader(self.templates_dir),
            PackageLoader("sqladmin", "templates"),
        ]

        templates.env.loader = ChoiceLoader(loaders)
        templates.env.globals["min"] = min
        templates.env.globals["zip"] = zip
        templates.env.globals["admin"] = self
        templates.env.globals["is_list"] = lambda x: isinstance(x, list)
        templates.env.globals["get_object_identifier"] = get_object_identifier

        return templates

    @property
    def views(self) -> List[Union[BaseView, ModelView]]:
        """Get list of ModelView and BaseView instances lazily.

        Returns:
            List of ModelView and BaseView instances added to Admin.
        """

        return self._views

    def _find_model_view(self, identity: str) -> ModelView:
        for view in self.views:
            if isinstance(view, ModelView) and view.identity == identity:
                return view

        raise HTTPException(status_code=404)

    def add_view(self, view: Union[Type[ModelView], Type[BaseView]]) -> None:
        """Add ModelView or BaseView classes to Admin.
        This is a shortcut that will handle both `add_model_view` and `add_base_view`.
        """

        view._admin_ref = self
        if view.is_model:
            self.add_model_view(view)  # type: ignore
        else:
            self.add_base_view(view)

    def _find_decorated_funcs(
        self,
        view: Type[Union[BaseView, ModelView]],
        view_instance: Union[BaseView, ModelView],
        handle_fn: Callable[
            [MethodType, Type[Union[BaseView, ModelView]], Union[BaseView, ModelView]],
            None,
        ],
    ) -> None:
        funcs = inspect.getmembers(view_instance, predicate=inspect.ismethod)

        for _, func in funcs[::-1]:
            handle_fn(func, view, view_instance)

    def _handle_action_decorated_func(
        self,
        func: MethodType,
        view: Type[Union[BaseView, ModelView]],
        view_instance: Union[BaseView, ModelView],
    ) -> None:
        if hasattr(func, "_action"):
            view_instance = cast(ModelView, view_instance)
            self.admin.add_route(
                route=func,
                path=f"/{view_instance.identity}/action/" + getattr(func, "_slug"),
                methods=["GET"],
                name=f"action-{view_instance.identity}-{getattr(func, '_slug')}",
                include_in_schema=getattr(func, "_include_in_schema"),
            )

            if getattr(func, "_add_in_list"):
                view_instance._custom_actions_in_list[getattr(func, "_slug")] = getattr(
                    func, "_label"
                )
            if getattr(func, "_add_in_detail"):
                view_instance._custom_actions_in_detail[
                    getattr(func, "_slug")
                ] = getattr(func, "_label")

            if getattr(func, "_confirmation_message"):
                view_instance._custom_actions_confirmation[
                    getattr(func, "_slug")
                ] = getattr(func, "_confirmation_message")

    def _handle_expose_decorated_func(
        self,
        func: MethodType,
        view: Type[Union[BaseView, ModelView]],
        view_instance: Union[BaseView, ModelView],
    ) -> None:
        if hasattr(func, "_exposed"):
            self.admin.add_route(
                route=func,
                path=getattr(func, "_path"),
                methods=getattr(func, "_methods"),
                name=getattr(func, "_identity"),
                include_in_schema=getattr(func, "_include_in_schema"),
            )

            view.identity = getattr(func, "_identity")

    def add_model_view(self, view: Type[ModelView]) -> None:
        """Add ModelView to the Admin.

        ???+ usage
            ```python
            from sqladmin import Admin, ModelView

            class UserAdmin(ModelView, model=User):
                pass

            admin.add_model_view(UserAdmin)
            ```
        """

        # Set database engine from Admin instance
        view.session_maker = self.session_maker
        view.is_async = self.is_async
        view.ajax_lookup_url = urljoin(
            self.base_url + "/", f"{view.identity}/ajax/lookup"
        )
        view.templates = self.templates
        view_instance = view()

        self._find_decorated_funcs(
            view, view_instance, self._handle_action_decorated_func
        )
        self._views.append(view_instance)
        self._build_menu(view_instance)

    def add_base_view(self, view: Type[BaseView]) -> None:
        """Add BaseView to the Admin.

        ???+ usage
            ```python
            from sqladmin import BaseView, expose

            class CustomAdmin(BaseView):
                name = "Custom Page"
                icon = "fa-solid fa-chart-line"

                @expose("/custom", methods=["GET"])
                def test_page(self, request: Request):
                    return self.templates.TemplateResponse(
                        "custom.html",
                        context={"request": request},
                    )

            admin.add_base_view(CustomAdmin)
            ```
        """

        view.templates = self.templates
        view_instance = view()

        self._find_decorated_funcs(
            view, view_instance, self._handle_expose_decorated_func
        )
        self._views.append(view_instance)
        self._build_menu(view_instance)

    def _build_menu(self, view: Union[ModelView, BaseView]) -> None:
        if view.category:
            menu = CategoryMenu(name=view.category)
            menu.add_child(ViewMenu(view=view, name=view.name, icon=view.icon))
            self._menu.add(menu)
        else:
            self._menu.add(ViewMenu(view=view, icon=view.icon, name=view.name))


class BaseAdminView(BaseAdmin):
    """
    Manage right to access to an action from a model
    """

    async def _list(self, request: Request) -> None:
        model_view = self._find_model_view(request.path_params["identity"])
        if not model_view.is_accessible(request):
            raise HTTPException(status_code=403)

    async def _create(self, request: Request) -> None:
        model_view = self._find_model_view(request.path_params["identity"])
        if not model_view.can_create or not model_view.is_accessible(request):
            raise HTTPException(status_code=403)

    async def _details(self, request: Request) -> None:
        model_view = self._find_model_view(request.path_params["identity"])
        if not model_view.can_view_details or not model_view.is_accessible(request):
            raise HTTPException(status_code=403)

    async def _delete(self, request: Request) -> None:
        model_view = self._find_model_view(request.path_params["identity"])
        if not model_view.can_delete or not model_view.is_accessible(request):
            raise HTTPException(status_code=403)

    async def _edit(self, request: Request) -> None:
        model_view = self._find_model_view(request.path_params["identity"])
        if not model_view.can_edit or not model_view.is_accessible(request):
            raise HTTPException(status_code=403)

    async def _export(self, request: Request) -> None:
        model_view = self._find_model_view(request.path_params["identity"])
        if not model_view.can_export or not model_view.is_accessible(request):
            raise HTTPException(status_code=403)
        if request.path_params["export_type"] not in model_view.export_types:
            raise HTTPException(status_code=404)


class Admin(BaseAdminView):
    """Main entrypoint to admin interface.

    ???+ usage
        ```python
        from fastapi import FastAPI
        from sqladmin import Admin, ModelView

        from mymodels import User # SQLAlchemy model


        app = FastAPI()
        admin = Admin(app, engine)


        class UserAdmin(ModelView, model=User):
            column_list = [User.id, User.name]


        admin.add_view(UserAdmin)
        ```
    """

    def __init__(
        self,
        app: Starlette,
        engine: Optional[ENGINE_TYPE] = None,
        session_maker: Optional[Union[sessionmaker, "async_sessionmaker"]] = None,
        base_url: str = "/admin",
        title: str = "Admin",
        logo_url: Optional[str] = None,
        middlewares: Optional[Sequence[Middleware]] = None,
        debug: bool = False,
        templates_dir: str = "templates",
        authentication_backend: Optional[AuthenticationBackend] = None,
    ) -> None:
        """
        Args:
            app: Starlette or FastAPI application.
            engine: SQLAlchemy engine instance.
            session_maker: SQLAlchemy sessionmaker instance.
            base_url: Base URL for Admin interface.
            title: Admin title.
            logo_url: URL of logo to be displayed instead of title.
        """

        super().__init__(
            app=app,
            engine=engine,
            session_maker=session_maker,
            base_url=base_url,
            title=title,
            logo_url=logo_url,
            templates_dir=templates_dir,
            middlewares=middlewares,
            authentication_backend=authentication_backend,
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

        routes = [
            Mount("/statics", app=statics, name="statics"),
            Route("/", endpoint=self.index, name="index"),
            Route("/{identity}/list", endpoint=self.list, name="list"),
            Route("/{identity}/details/{pk}", endpoint=self.details, name="details"),
            Route(
                "/{identity}/delete",
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
                "/{identity}/export/{export_type}", endpoint=self.export, name="export"
            ),
            Route(
                "/{identity}/ajax/lookup", endpoint=self.ajax_lookup, name="ajax_lookup"
            ),
            Route("/login", endpoint=self.login, name="login", methods=["GET", "POST"]),
            Route("/logout", endpoint=self.logout, name="logout", methods=["GET"]),
        ]

        self.admin.router.routes = routes
        self.admin.exception_handlers = {HTTPException: http_exception}
        self.admin.debug = debug
        self.app.mount(base_url, app=self.admin, name="admin")

    @login_required
    async def index(self, request: Request) -> Response:
        """Index route which can be overridden to create dashboards."""

        return self.templates.TemplateResponse("index.html", {"request": request})

    @login_required
    async def list(self, request: Request) -> Response:
        """List route to display paginated Model instances."""

        await self._list(request)

        model_view = self._find_model_view(request.path_params["identity"])
        pagination = await model_view.list(request)
        pagination.add_pagination_urls(request.url)

        context = {
            "request": request,
            "model_view": model_view,
            "pagination": pagination,
        }

        return self.templates.TemplateResponse(model_view.list_template, context)

    @login_required
    async def details(self, request: Request) -> Response:
        """Details route."""

        await self._details(request)

        model_view = self._find_model_view(request.path_params["identity"])

        model = await model_view.get_object_for_details(request.path_params["pk"])
        if not model:
            raise HTTPException(status_code=404)

        context = {
            "request": request,
            "model_view": model_view,
            "model": model,
            "title": model_view.name,
        }

        return self.templates.TemplateResponse(model_view.details_template, context)

    @login_required
    async def delete(self, request: Request) -> Response:
        """Delete route."""

        await self._delete(request)

        identity = request.path_params["identity"]
        model_view = self._find_model_view(identity)

        params = request.query_params.get("pks", "")
        pks = params.split(",") if params else []
        for pk in pks:
            model = await model_view.get_object_for_delete(pk)
            if not model:
                raise HTTPException(status_code=404)

            await model_view.delete_model(request, pk)

        return Response(content=str(request.url_for("admin:list", identity=identity)))

    @login_required
    async def create(self, request: Request) -> Response:
        """Create model endpoint."""

        await self._create(request)

        identity = request.path_params["identity"]
        model_view = self._find_model_view(identity)

        Form = await model_view.scaffold_form()
        form_data = await self._handle_form_data(request)
        form = Form(form_data)

        context = {
            "request": request,
            "model_view": model_view,
            "form": form,
        }

        if request.method == "GET":
            return self.templates.TemplateResponse(model_view.create_template, context)

        if not form.validate():
            return self.templates.TemplateResponse(
                model_view.create_template, context, status_code=400
            )

        try:
            obj = await model_view.insert_model(request, form.data)
        except Exception as e:
            logger.exception(e)
            context["error"] = str(e)
            return self.templates.TemplateResponse(
                model_view.create_template, context, status_code=400
            )

        url = self.get_save_redirect_url(
            request=request,
            form=form_data,
            obj=obj,
            model_view=model_view,
        )
        return RedirectResponse(url=url, status_code=302)

    @login_required
    async def edit(self, request: Request) -> Response:
        """Edit model endpoint."""

        await self._edit(request)

        identity = request.path_params["identity"]
        model_view = self._find_model_view(identity)

        model = await model_view.get_object_for_edit(request.path_params["pk"])
        if not model:
            raise HTTPException(status_code=404)

        Form = await model_view.scaffold_form()
        context = {
            "request": request,
            "obj": model,
            "model_view": model_view,
            "form": Form(obj=model),
        }

        if request.method == "GET":
            return self.templates.TemplateResponse(model_view.edit_template, context)

        form_data = await self._handle_form_data(request, model)
        form = Form(form_data)
        if not form.validate():
            context["form"] = form
            return self.templates.TemplateResponse(
                model_view.edit_template, context, status_code=400
            )

        try:
            if model_view.save_as and form_data.get("save") == "Save as new":
                obj = await model_view.insert_model(request, form.data)
            else:
                obj = await model_view.update_model(
                    request, pk=request.path_params["pk"], data=form.data
                )
        except Exception as e:
            logger.exception(e)
            context["error"] = str(e)
            return self.templates.TemplateResponse(
                model_view.edit_template, context, status_code=400
            )

        url = self.get_save_redirect_url(
            request=request,
            form=form_data,
            obj=obj,
            model_view=model_view,
        )
        return RedirectResponse(url=url, status_code=302)

    @login_required
    async def export(self, request: Request) -> Response:
        """Export model endpoint."""

        await self._export(request)

        identity = request.path_params["identity"]
        export_type = request.path_params["export_type"]

        model_view = self._find_model_view(identity)
        rows = await model_view.get_model_objects(
            request=request, limit=model_view.export_max_rows
        )
        return model_view.export_data(rows, export_type=export_type)

    async def login(self, request: Request) -> Response:
        assert self.authentication_backend is not None

        context = {"request": request, "error": ""}

        if request.method == "GET":
            return self.templates.TemplateResponse("login.html", context)

        ok = await self.authentication_backend.login(request)
        if not ok:
            context["error"] = "Invalid credentials."
            return self.templates.TemplateResponse(
                "login.html", context, status_code=400
            )

        return RedirectResponse(request.url_for("admin:index"), status_code=302)

    async def logout(self, request: Request) -> Response:
        assert self.authentication_backend is not None

        await self.authentication_backend.logout(request)
        return RedirectResponse(request.url_for("admin:index"), status_code=302)

    async def ajax_lookup(self, request: Request) -> Response:
        """Ajax lookup route."""

        identity = request.path_params["identity"]
        model_view = self._find_model_view(identity)

        name = request.query_params.get("name")
        term = request.query_params.get("term")

        if not name or not term:
            raise HTTPException(status_code=400)

        try:
            loader: QueryAjaxModelLoader = model_view._form_ajax_refs[name]
        except KeyError:
            raise HTTPException(status_code=400)

        data = [loader.format(m) for m in await loader.get_list(term)]
        return JSONResponse({"results": data})

    def get_save_redirect_url(
        self, request: Request, form: FormData, model_view: ModelView, obj: Any
    ) -> Union[str, URL]:
        """
        Get the redirect URL after a save action
        which is triggered from create/edit page.
        """

        identity = request.path_params["identity"]
        identifier = get_object_identifier(obj)

        if form.get("save") == "Save":
            return request.url_for("admin:list", identity=identity)
        elif form.get("save") == "Save and continue editing" or (
            form.get("save") == "Save as new" and model_view.save_as_continue
        ):
            return request.url_for("admin:edit", identity=identity, pk=identifier)
        return request.url_for("admin:create", identity=identity)

    async def _handle_form_data(self, request: Request, obj: Any = None) -> FormData:
        """
        Handle form data and modify in case of UplaodFile.
        This is needed since in edit page
        there's no way to show current file of object.
        """

        form = await request.form()
        form_data: List[Tuple[str, Union[str, UploadFile]]] = []
        for key, value in form.multi_items():
            if not isinstance(value, UploadFile):
                form_data.append((key, value))
                continue

            should_clear = form.get(key + "_checkbox")
            empty_upload = len(await value.read(1)) != 1
            await value.seek(0)
            if should_clear:
                form_data.append((key, UploadFile(io.BytesIO(b""))))
            elif empty_upload and obj and getattr(obj, key):
                f = getattr(obj, key)  # In case of update, imitate UploadFile
                form_data.append((key, UploadFile(filename=f.name, file=f.open())))
            else:
                form_data.append((key, value))
        return FormData(form_data)


def expose(
    path: str,
    *,
    methods: List[str] = ["GET"],
    identity: Optional[str] = None,
    include_in_schema: bool = True,
) -> Callable[..., Any]:
    """Expose View with information."""

    @no_type_check
    def wrap(func):
        func._exposed = True
        func._path = path
        func._methods = methods
        func._identity = identity or func.__name__
        func._include_in_schema = include_in_schema
        return login_required(func)

    return wrap


def action(
    name: str,
    label: Optional[str] = None,
    confirmation_message: Optional[str] = None,
    *,
    include_in_schema: bool = True,
    add_in_detail: bool = True,
    add_in_list: bool = True,
) -> Callable[..., Any]:
    """Decorate a [`ModelView`][sqladmin.models.ModelView] function
    with this to:

    * expose it as a custom "action" route
    * add a button to the admin panel to invoke the action

    When invoked from the admin panel, the following query parameter(s) are passed:

    * `pks`: the comma-separated list of selected object PKs - can be empty

    Args:
        name: Unique name for the action - should be alphanumeric, dash and underscore
        label: Human-readable text describing action
        confirmation_message: Message to show before confirming action
        include_in_schema: Indicating if the endpoint be included in the schema
        add_in_detail: Indicating if action should be dispalyed on model detail page
        add_in_list: Indicating if action should be dispalyed on model list page
    """

    @no_type_check
    def wrap(func):
        func._action = True
        func._slug = slugify_action_name(name)
        func._label = label if label is not None else name
        func._confirmation_message = confirmation_message
        func._include_in_schema = include_in_schema
        func._add_in_detail = add_in_detail
        func._add_in_list = add_in_list
        return login_required(func)

    return wrap
