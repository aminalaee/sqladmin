import time
from enum import Enum
from typing import (
    Any,
    Callable,
    ClassVar,
    Dict,
    Generator,
    List,
    Optional,
    Sequence,
    Tuple,
    Type,
    Union,
    no_type_check,
)
from urllib.parse import urlencode

import anyio
from sqlalchemy import Column, String, asc, cast, desc, func, inspect, or_
from sqlalchemy.exc import NoInspectionAvailable
from sqlalchemy.orm import (
    ColumnProperty,
    RelationshipProperty,
    joinedload,
    sessionmaker,
)
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.sql.elements import ClauseElement
from sqlalchemy.sql.expression import Select, select
from starlette.datastructures import URL
from starlette.requests import Request
from starlette.responses import StreamingResponse
from starlette.templating import Jinja2Templates
from wtforms import Field, Form

from sqladmin._queries import Query
from sqladmin._types import ENGINE_TYPE, MODEL_PROPERTY
from sqladmin.ajax import create_ajax_loader
from sqladmin.exceptions import InvalidModelError
from sqladmin.formatters import BASE_FORMATTERS
from sqladmin.forms import ModelConverter, ModelConverterBase, get_model_form
from sqladmin.helpers import (
    Writer,
    get_column_python_type,
    get_primary_key,
    map_attr_to_prop,
    prettify_class_name,
    secure_filename,
    slugify_class_name,
    stream_to_csv,
)
from sqladmin.pagination import Pagination

__all__ = [
    "BaseView",
    "ModelView",
    "ModelView",
]


class ModelViewMeta(type):
    """Metaclass used to specify class variables in ModelView.

    Danger:
        This class should almost never be used directly.
    """

    @no_type_check
    def __new__(mcls, name, bases, attrs: dict, **kwargs: Any):
        cls: Type["ModelView"] = super().__new__(mcls, name, bases, attrs)

        model = kwargs.get("model")

        if not model:
            return cls

        try:
            inspect(model)
        except NoInspectionAvailable:
            raise InvalidModelError(
                f"Class {model.__name__} is not a SQLAlchemy model."
            )

        cls.pk_column = get_primary_key(model)
        cls.identity = slugify_class_name(model.__name__)
        cls.model = model

        cls.name = attrs.get("name", prettify_class_name(cls.model.__name__))
        cls.name_plural = attrs.get("name_plural", f"{cls.name}s")
        cls.icon = attrs.get("icon")

        cls.list_query = attrs.get("list_query", select(model))
        cls.count_query = attrs.get("count_query", select(func.count(cls.pk_column)))

        mcls._check_conflicting_options(["column_list", "column_exclude_list"], attrs)
        mcls._check_conflicting_options(
            ["form_columns", "form_excluded_columns"], attrs
        )
        mcls._check_conflicting_options(
            ["column_details_list", "column_details_exclude_list"], attrs
        )
        mcls._check_conflicting_options(
            ["column_export_list", "column_export_exclude_list"], attrs
        )

        return cls

    @classmethod
    def _check_conflicting_options(mcls, keys: List[str], attrs: dict) -> None:
        if all(k in attrs for k in keys):
            raise AssertionError(f"Cannot use {' and '.join(keys)} together.")


class BaseModelView:
    def is_visible(self, request: Request) -> bool:
        """Override this method if you want dynamically
        hide or show administrative views from SQLAdmin menu structure
        By default, item is visible in menu.
        Both is_visible and is_accessible to be displayed in menu.
        """
        return True

    def is_accessible(self, request: Request) -> bool:
        """Override this method to add permission checks.
        SQLAdmin does not make any assumptions about the authentication system
        used in your application, so it is up to you to implement it.
        By default, it will allow access for everyone.
        """
        return True


class BaseView(BaseModelView):
    """Base class for defining admnistrative views for the model.

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

    # Internals
    is_model: ClassVar[bool] = False
    templates: ClassVar[Jinja2Templates]

    name: ClassVar[str] = ""
    """Name of the view to be displayed."""

    identity: ClassVar[str] = ""
    """Same as name but it will be used for URL of the endpoints."""

    methods: ClassVar[List[str]] = ["GET"]
    """List of method names for the endpoint.
    By default it's set to `["GET"]` only.
    """

    include_in_schema: ClassVar[bool] = True
    """Control whether this endpoint
    should be included in the schema.
    """

    icon: ClassVar[str]
    """Display icon for ModelAdmin in the sidebar.
    Currently only supports FontAwesome icons.
    """


class ModelView(BaseView, metaclass=ModelViewMeta):
    """Base class for defining admnistrative behaviour for the model.

    ???+ usage
        ```python
        from sqladmin import ModelView

        from mymodels import User # SQLAlchemy model

        class UserAdmin(ModelView, model=User):
            can_create = True
        ```
    """

    model: ClassVar[type]

    # Internals
    pk_column: ClassVar[Column]
    sessionmaker: ClassVar[sessionmaker]
    engine: ClassVar[ENGINE_TYPE]
    async_engine: ClassVar[bool]
    is_model: ClassVar[bool] = True
    ajax_lookup_url: ClassVar[str] = ""

    name_plural: ClassVar[str] = ""
    """Plural name of ModelView.
    Default value is Model class name + `s`.
    """

    # Permissions
    can_create: ClassVar[bool] = True
    """Permission for creating new Models. Default value is set to `True`."""

    can_edit: ClassVar[bool] = True
    """Permission for editing Models. Default value is set to `True`."""

    can_delete: ClassVar[bool] = True
    """Permission for deleting Models. Default value is set to `True`."""

    can_view_details: ClassVar[bool] = True
    """Permission for viewing full details of Models.
    Default value is set to `True`.
    """

    can_export: ClassVar[bool] = True
    """Permission for exporting lists of Models.
    Default value is set to `True`.
    """

    # List page
    column_list: ClassVar[Sequence[Union[str, InstrumentedAttribute]]] = []
    """List of columns to display in `List` page.
    Columns can either be string names or SQLAlchemy columns.

    ???+ note
        By default only Model primary key is displayed.

    ???+ example
        ```python
        class UserAdmin(ModelView, model=User):
            column_list = [User.id, User.name]
        ```
    """

    column_exclude_list: ClassVar[Sequence[Union[str, InstrumentedAttribute]]] = []
    """List of columns to exclude in `List` page.
    Columns can either be string names or SQLAlchemy columns.

    ???+ example
        ```python
        class UserAdmin(ModelView, model=User):
            column_exclude_list = [User.id, User.name]
        ```
    """

    column_formatters: ClassVar[
        Dict[Union[str, InstrumentedAttribute], Callable[[type, Column], Any]]
    ] = {}
    """Dictionary of list view column formatters.
    Columns can either be string names or SQLAlchemy columns.

    ???+ example
        ```python
        class UserAdmin(ModelView, model=User):
            column_formatters = {User.name: lambda m, a: m.name[:10]}
        ```

    The format function has the prototype:
    ???+ formatter
        ```python
        def formatter(model, attribute):
            # `model` is model instance
            # `attribute` is a Union[ColumnProperty, RelationshipProperty]
            pass
        ```
    """

    page_size: ClassVar[int] = 10
    """Default number of items to display in `List` page pagination.
    Default value is set to `10`.

    ???+ example
        ```python
        class UserAdmin(ModelView, model=User):
            page_size = 25
        ```
    """

    page_size_options: ClassVar[Sequence[int]] = [10, 25, 50, 100]
    """Pagination choices displayed in `List` page.
    Default value is set to `[10, 25, 50, 100]`.

    ???+ example
        ```python
        class UserAdmin(ModelView, model=User):
            page_size_options = [50, 100]
        ```
    """

    column_searchable_list: ClassVar[Sequence[Union[str, InstrumentedAttribute]]] = []
    """A collection of the searchable columns.
    It is assumed that only text-only fields are searchable,
    but it is up to the model implementation to decide.

    ???+ example
        ```python
        class UserAdmin(ModelView, model=User):
            column_searchable_list = [User.name]
        ```
    """

    column_sortable_list: ClassVar[Sequence[Union[str, InstrumentedAttribute]]] = []
    """Collection of the sortable columns for the list view.

    ???+ example
        ```python
        class UserAdmin(ModelView, model=User):
            column_sortable_list = [User.name]
        ```
    """

    column_default_sort: ClassVar[Union[str, Tuple[str, bool], list]] = []
    """Default sort column if no sorting is applied.

    ???+ example
        ```python
        class UserAdmin(ModelView, model=User):
            column_default_sort = "email"
        ```

    You can use tuple to control ascending descending order. In following example, items
    will be sorted in descending order:

    ???+ example
        ```python
        class UserAdmin(ModelView, model=User):
            column_default_sort = ("email", True)
        ```

    If you want to sort by more than one column, you can pass a list of tuples

    ???+ example
        ```python
        class UserAdmin(ModelView, model=User):
            column_default_sort = [("email", True), ("name", False)]
        ```
    """

    # Details page
    column_details_list: ClassVar[Sequence[Union[str, InstrumentedAttribute]]] = []
    """List of columns to display in `Detail` page.
    Columns can either be string names or SQLAlchemy columns.

    ???+ note
        By default all columns of Model are displayed.

    ???+ example
        ```python
        class UserAdmin(ModelView, model=User):
            column_details_list = [User.id, User.name, User.mail]
        ```
    """

    column_details_exclude_list: ClassVar[
        Sequence[Union[str, InstrumentedAttribute]]
    ] = []
    """List of columns to exclude from displaying in `Detail` page.
    Columns can either be string names or SQLAlchemy columns.

    ???+ example
        ```python
        class UserAdmin(ModelView, model=User):
            column_details_exclude_list = [User.mail]
        ```
    """

    column_formatters_detail: ClassVar[
        Dict[Union[str, InstrumentedAttribute], Callable[[type, Column], Any]]
    ] = {}
    """Dictionary of details view column formatters.
    Columns can either be string names or SQLAlchemy columns.

    ???+ example
        ```python
        class UserAdmin(ModelView, model=User):
            column_formatters_detail = {User.name: lambda m, a: m.name[:10]}
        ```

    The format function has the prototype:
    ???+ formatter
        ```python
        def formatter(model, attribute):
            # `model` is model instance
            # `attribute` is a Union[ColumnProperty, RelationshipProperty]
            pass
        ```
    """

    save_as: ClassVar[bool] = False
    """Set `save_as` to enable a “save as new” feature on admin change forms.

    Normally, objects have three save options:
    ``Save`, `Save and continue editing` and `Save and add another`.

    If save_as is True, `Save and add another` will be replaced 
    by a `Save as new` button 
    that creates a new object (with a new ID) 
    rather than updating the existing object.

    By default, `save_as` is set to `False`.
    """

    save_as_continue: ClassVar[bool] = True
    """When `save_as=True`, the default redirect after saving the new object 
    is to the edit view for that object.
    If you set `save_as_continue=False`, the redirect will be to the list view.

    By default, `save_as_continue` is set to `True`.
    """

    # Templates
    list_template: ClassVar[str] = "list.html"
    """List view template. Default is `list.html`."""

    create_template: ClassVar[str] = "create.html"
    """Create view template. Default is `create.html`."""

    details_template: ClassVar[str] = "details.html"
    """Details view template. Default is `details.html`."""

    edit_template: ClassVar[str] = "edit.html"
    """Edit view template. Default is `edit.html`."""

    # Export
    column_export_list: ClassVar[List[Union[str, InstrumentedAttribute]]] = []
    """List of columns to include when exporting.
    Columns can either be string names or SQLAlchemy columns.

    ???+ example
        ```python
        class UserAdmin(ModelView, model=User):
            column_export_list = [User.id, User.name]
        ```
    """

    column_export_exclude_list: ClassVar[List[Union[str, InstrumentedAttribute]]] = []
    """List of columns to exclude when exporting.
    Columns can either be string names or SQLAlchemy columns.

    ???+ example
        ```python
        class UserAdmin(ModelView, model=User):
            column_export_exclude_list = [User.id, User.name]
        ```
    """

    export_types: ClassVar[List[str]] = ["csv"]
    """A list of available export filetypes.
    Currently only `csv` is supported.
    """

    export_max_rows: ClassVar[int] = 0
    """Maximum number of rows allowed for export.
    Unlimited by default.
    """

    # Form
    form: ClassVar[Optional[Type[Form]]] = None
    """Form class.
    Override if you want to use custom form for your model.
    Will completely disable form scaffolding functionality.

    ???+ example
        ```python
        class MyForm(Form):
            name = StringField('Name')

        class MyModelView(ModelView, model=User):
            form = MyForm
        ```
    """

    form_base_class: ClassVar[Type[Form]] = Form
    """Base form class.
    Will be used by form scaffolding function when creating model form.
    Useful if you want to have custom constructor or override some fields.

    ???+ example
        ```python
        class MyBaseForm(Form):
            def do_something(self):
                pass

        class MyModelView(ModelView, model=User):
            form_base_class = MyBaseForm
        ```
    """

    form_args: ClassVar[Dict[str, Dict[str, Any]]] = {}
    """Dictionary of form field arguments.
    Refer to WTForms documentation for list of possible options.

    ???+ example
        ```python
        from wtforms.validators import DataRequired

        class MyModelView(ModelView, model=User):
            form_args = dict(
                name=dict(label="User Name", validators=[DataRequired()])
            )
        ```
    """

    form_widget_args: ClassVar[Dict[str, Dict[str, Any]]] = {}
    """Dictionary of form widget rendering arguments.
    Use this to customize how widget is rendered without using custom template.

    ???+ example
        ```python
        class UserAdmin(ModelView, model=User):
            form_widget_args = {
                "email": {
                    "readonly": True,
                },
            }
        ```
    """

    form_columns: ClassVar[Sequence[Union[str, InstrumentedAttribute]]] = []
    """List of columns to include in the form.
    Columns can either be string names or SQLAlchemy columns.

    ???+ note
        By default all columns of Model are included in the form.

    ???+ example
        ```python
        class UserAdmin(ModelView, model=User):
            form_columns = [User.name, User.mail]
        ```
    """

    form_excluded_columns: ClassVar[Sequence[Union[str, InstrumentedAttribute]]] = []
    """List of columns to exclude from the form.
    Columns can either be string names or SQLAlchemy columns.

    ???+ example
        ```python
        class UserAdmin(ModelView, model=User):
            form_excluded_columns = [User.id]
        ```
    """

    form_overrides: ClassVar[Dict[str, Type[Field]]] = {}
    """Dictionary of form column overrides.

    ???+ example
        ```python
        class UserAdmin(ModelView, model=User):
            form_overrides = dict(name=wtf.FileField)
        ```
    """

    form_include_pk: ClassVar[bool] = False
    """Control if form should include primary key columns or not.

    ???+ example
        ```python
        class UserAdmin(ModelView, model=User):
            form_include_pk = True
        ```
    """

    form_ajax_refs: ClassVar[Dict[str, dict]] = {}
    """Use Ajax for foreign key model loading.
    Should contain dictionary, where key is field name and
    value is a dictionary which configures Ajax lookups.

    ???+example
        ```python
        class UserAdmin(ModelAdmin, model=User):
            form_ajax_refs = {
                'address': {
                    'fields': ('street', 'zip_code'),
                    'order_by': ('id',),
                }
            }
        ```
    """

    form_converter: ClassVar[Type[ModelConverterBase]] = ModelConverter
    """Custom form converter class.
    Useful if you want to add custom form conversion in addition to the defaults.

    ???+ example
        ```python
        class PhoneNumberConverter(ModelConverter):
            pass

        class UserAdmin(ModelAdmin, model=User):
            form_converter = PhoneNumberConverter
        ```
    """

    # General options
    column_labels: ClassVar[Dict[Union[str, InstrumentedAttribute], str]] = {}
    """A mapping of column labels, used to map column names to new names.
    Dictionary keys can be string names or SQLAlchemy columns with string values.

    ???+ example
        ```python
        class UserAdmin(ModelView, model=User):
            column_labels = {User.mail: "Email"}
        ```
    """

    column_type_formatters: ClassVar[Dict[Type, Callable]] = BASE_FORMATTERS
    """Dictionary of value type formatters to be used in the list view.

    By default, two types are formatted:

        - None will be displayed as an empty string
        - bool will be displayed as a checkmark if it is True otherwise as an X.

    If you don’t like the default behavior and don’t want any type formatters applied,
    just override this property with an empty dictionary:

    ???+ example
        ```python
        class UserAdmin(ModelView, model=User):
            column_type_formatters = dict()
        ```
    """

    list_query: ClassVar[Select] = select()
    """
    The SQLAlchemy select expression used for the list page which can be customized.
    By default it will select all objects without any filters.

    ???+ example
        ```python
        from sqlalchemy import select

        class UserAdmin(ModelView, model=User):
            list_query = select(User).filter(User.active == True)
        ```
    """

    count_query: ClassVar[Select] = select()
    """
    The SQLAlchemy select expression used for the count query which can be customized.
    By default it will select all objects without any filters.

    ???+ example
        ```python
        from sqlalchemy import select

        class UserAdmin(ModelView, model=User):
            count_query = select(func.count(User.id))
        ```
    """

    def __init__(self) -> None:
        self._mapper = inspect(self.model)
        self._relation_props = list(self._mapper.relationships)
        self._relation_attrs = [
            getattr(self.model, prop.key) for prop in self._relation_props
        ]
        self._column_props = list(self._mapper.columns)
        self._props = self._mapper.attrs

        self._column_labels = self.get_column_labels()
        self._column_labels_value_by_key = {
            v: k for k, v in self._column_labels.items()
        }

        self._list_props = self.get_list_columns()
        self._list_relation_attrs = [
            getattr(self.model, prop.key)
            for (_, prop) in self._list_props
            if isinstance(prop, RelationshipProperty)
        ]

        self._details_props = self.get_details_columns()
        self._details_relation_attrs = [
            getattr(self.model, prop.key)
            for (_, prop) in self._details_props
            if isinstance(prop, RelationshipProperty)
        ]

        column_formatters = getattr(self, "column_formatters", {})
        self._list_formatters = {
            map_attr_to_prop(attr, self): formatter
            for (attr, formatter) in column_formatters.items()
        }

        column_formatters_detail = getattr(self, "column_formatters_detail", {})
        self._detail_formatters = {
            map_attr_to_prop(attr, self): formatter
            for (attr, formatter) in column_formatters_detail.items()
        }

        self._form_props = self.get_form_columns()
        self._form_relation_attrs = [
            getattr(self.model, prop.key)
            for (_, prop) in self._form_props
            if isinstance(prop, RelationshipProperty)
        ]

        self._export_props = self.get_export_columns()

        self._search_fields = [
            getattr(self.model, attr) if isinstance(attr, str) else attr
            for attr in self.column_searchable_list
        ]

        self._sort_fields = [
            map_attr_to_prop(attr, self).key for attr in self.column_sortable_list
        ]

        self._form_ajax_refs = {}
        for name, options in self.form_ajax_refs.items():
            self._form_ajax_refs[name] = create_ajax_loader(
                model_admin=self, name=name, options=options
            )

        self._custom_actions_in_list: Dict[str, str] = {}
        self._custom_actions_in_detail: Dict[str, str] = {}
        self._custom_actions_confirmation: Dict[str, str] = {}

    def _run_query_sync(self, stmt: ClauseElement) -> Any:
        with self.sessionmaker(expire_on_commit=False) as session:
            result = session.execute(stmt)
            return result.scalars().unique().all()

    async def _run_query(self, stmt: ClauseElement) -> Any:
        if self.async_engine:
            async with self.sessionmaker(expire_on_commit=False) as session:
                result = await session.execute(stmt)
                return result.scalars().unique().all()
        else:
            return await anyio.to_thread.run_sync(self._run_query_sync, stmt)

    def _url_for_details(self, request: Request, obj: Any) -> Union[str, URL]:
        pk = self._get_pk(obj)
        return request.url_for(
            "admin:details",
            identity=slugify_class_name(obj.__class__.__name__),
            pk=pk,
        )

    def _url_for_edit(self, request: Request, obj: Any) -> Union[str, URL]:
        pk = self._get_pk(obj)
        return request.url_for(
            "admin:edit",
            identity=slugify_class_name(obj.__class__.__name__),
            pk=pk,
        )

    def _url_for_delete(self, request: Request, obj: Any) -> str:
        pk = self._get_pk(obj)
        query_params = urlencode({"pks": pk})
        url = request.url_for(
            "admin:delete", identity=slugify_class_name(obj.__class__.__name__)
        )
        return str(url) + "?" + query_params

    def _url_for_details_with_prop(
        self, request: Request, obj: Any, prop: RelationshipProperty
    ) -> Union[str, URL]:
        target = getattr(obj, prop.key)
        if target is None:
            return ""

        pk = getattr(target, prop.mapper.primary_key[0].name)
        return request.url_for(
            "admin:details",
            identity=slugify_class_name(target.__class__.__name__),
            pk=pk,
        )

    def _url_for_action(self, request: Request, action_name: str) -> str:
        return str(
            request.url_for(
                f"admin:{self.identity}-{action_name}",
                identity=self.identity,
            )
        )

    def _get_pk(self, obj: Any) -> Any:
        return getattr(obj, get_primary_key(obj).name)

    def _get_default_sort(self) -> List[Tuple[str, bool]]:
        if self.column_default_sort:
            if isinstance(self.column_default_sort, list):
                return self.column_default_sort
            if isinstance(self.column_default_sort, tuple):
                return [self.column_default_sort]
            else:
                return [(self.column_default_sort, False)]

        return [(self.pk_column.name, False)]

    def _default_formatter(self, value: Any) -> Any:
        if type(value) in self.column_type_formatters:
            formatter = self.column_type_formatters[type(value)]
            return formatter(value)

        return value

    async def count(self) -> int:
        rows = await self._run_query(self.count_query)
        return rows[0]

    async def list(
        self,
        page: int,
        page_size: int,
        search: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort: str = "asc",
    ) -> Pagination:
        page_size = min(page_size or self.page_size, max(self.page_size_options))

        count = await self.count()
        stmt = self.list_query.limit(page_size).offset((page - 1) * page_size)

        for relation in self._list_relation_attrs:
            stmt = stmt.options(joinedload(relation))

        if sort_by:
            sort_fields = [(sort_by, sort == "desc")]
        else:
            sort_fields = self._get_default_sort()

        for sort_field, is_desc in sort_fields:
            if is_desc:
                stmt = stmt.order_by(desc(sort_field))
            else:
                stmt = stmt.order_by(asc(sort_field))

        if search:
            stmt = self.search_query(stmt=stmt, term=search)

        rows = await self._run_query(stmt)
        pagination = Pagination(
            rows=rows,
            page=page,
            page_size=page_size,
            count=count,
        )

        return pagination

    async def get_model_objects(self, limit: Union[int, None] = 0) -> List[Any]:
        # For unlimited rows this should pass None
        limit = None if limit == 0 else limit
        stmt = self.list_query.limit(limit=limit)

        for relation in self._list_relation_attrs:
            stmt = stmt.options(joinedload(relation))

        rows = await self._run_query(stmt)
        return rows

    async def _get_object_by_pk(self, stmt: Select) -> Any:
        rows = await self._run_query(stmt)
        return rows[0] if rows else None

    async def get_object_for_details(self, value: Any) -> Any:
        pk_value = get_column_python_type(self.pk_column)(value)
        stmt = select(self.model).where(self.pk_column == pk_value)

        for relation in self._details_relation_attrs:
            stmt = stmt.options(joinedload(relation))

        return await self._get_object_by_pk(stmt)

    async def get_object_for_edit(self, value: Any) -> Any:
        pk_value = get_column_python_type(self.pk_column)(value)
        stmt = select(self.model).where(self.pk_column == pk_value)

        for relation in self._form_relation_attrs:
            stmt = stmt.options(joinedload(relation))

        return await self._get_object_by_pk(stmt)

    async def get_object_for_delete(self, value: Any) -> Any:
        pk_value = get_column_python_type(self.pk_column)(value)
        stmt = select(self.model).where(self.pk_column == pk_value)
        return await self._get_object_by_pk(stmt)

    def get_prop_value(
        self, obj: type, prop: Union[Column, ColumnProperty, RelationshipProperty]
    ) -> Any:
        result = None

        if isinstance(prop, Column):
            result = getattr(obj, prop.name)
        else:
            result = getattr(obj, prop.key)
            result = result.value if isinstance(result, Enum) else result

        return result

    def get_list_value(self, obj: type, prop: MODEL_PROPERTY) -> Tuple[Any, Any]:
        """Get tuple of (value, formatted_value) for the list view."""
        value = self.get_prop_value(obj, prop)
        formatted_value = self._default_formatter(value)

        formatter = self._list_formatters.get(prop)
        if formatter:
            formatted_value = formatter(obj, prop)
        return value, formatted_value

    def get_detail_value(self, obj: type, prop: MODEL_PROPERTY) -> Tuple[Any, Any]:
        """Get tuple of (value, formatted_value) for the detail view."""
        value = self.get_prop_value(obj, prop)
        formatted_value = self._default_formatter(value)

        formatter = self._detail_formatters.get(prop)
        if formatter:
            formatted_value = formatter(obj, prop)
        return value, formatted_value

    def _build_column_list(
        self,
        defaults: List[MODEL_PROPERTY],
        include: Optional[Sequence[Union[str, InstrumentedAttribute]]] = None,
        exclude: Optional[Sequence[Union[str, InstrumentedAttribute]]] = None,
    ) -> List[Tuple[str, MODEL_PROPERTY]]:
        """This function generalizes constructing a list of columns
        for any sequence of inclusions or exclusions.
        """
        if include:
            props = [map_attr_to_prop(prop, self) for prop in include]
        elif exclude:
            exclude_props = {map_attr_to_prop(prop, self) for prop in exclude}
            props = [prop for prop in self._props if prop not in exclude_props]
        else:
            props = defaults

        return [(self._column_labels.get(prop, prop.key), prop) for prop in props]

    def get_list_columns(self) -> List[Tuple[str, MODEL_PROPERTY]]:
        """Get list of properties to display in List page."""

        column_list = getattr(self, "column_list", None)
        column_exclude_list = getattr(self, "column_exclude_list", None)

        return self._build_column_list(
            include=column_list,
            exclude=column_exclude_list,
            defaults=[self._props[self.pk_column.key]],
        )

    def get_details_columns(self) -> List[Tuple[str, MODEL_PROPERTY]]:
        """Get list of properties to display in Detail page."""

        column_details_list = getattr(self, "column_details_list", None)
        column_details_exclude_list = getattr(self, "column_details_exclude_list", None)

        return self._build_column_list(
            include=column_details_list,
            exclude=column_details_exclude_list,
            defaults=self._props,
        )

    def get_form_columns(self) -> List[Tuple[str, MODEL_PROPERTY]]:
        """Get list of properties to display in the form."""

        form_columns = getattr(self, "form_columns", None)
        form_excluded_columns = getattr(self, "form_excluded_columns", None)

        return self._build_column_list(
            include=form_columns,
            exclude=form_excluded_columns,
            defaults=self._props,
        )

    def get_export_columns(self) -> List[Tuple[str, MODEL_PROPERTY]]:
        """Get list of properties to export."""

        columns = getattr(self, "column_export_list", None)
        excluded_columns = getattr(self, "column_export_exclude_list", None)

        return self._build_column_list(
            include=columns,
            exclude=excluded_columns,
            defaults=[item[1] for item in self._list_props],
        )

    async def on_model_change(self, data: dict, model: Any, is_created: bool) -> None:
        """Perform some actions before a model is created or updated.
        By default does nothing.
        """

    async def after_model_change(
        self, data: dict, model: Any, is_created: bool
    ) -> None:
        """Perform some actions after a model was created
        or updated and committed to the database.
        By default does nothing.
        """

    def get_column_labels(
        self,
    ) -> Dict[MODEL_PROPERTY, str]:
        return {
            map_attr_to_prop(column_label, self): value
            for column_label, value in self.column_labels.items()
        }

    async def delete_model(self, obj: Any) -> None:
        await Query(self).delete(obj)

    async def insert_model(self, data: dict) -> Any:
        return await Query(self).insert(data)

    async def update_model(self, pk: Any, data: Dict[str, Any]) -> Any:
        return await Query(self).update(pk, data)

    async def on_model_delete(self, model: Any) -> None:
        """Perform some actions before a model is deleted.
        By default does nothing.
        """

    async def after_model_delete(self, model: Any) -> None:
        """Perform some actions after a model is deleted.
        By default do nothing.
        """

    async def scaffold_form(self) -> Type[Form]:
        if self.form is not None:
            return self.form
        return await get_model_form(
            model=self.model,
            engine=self.engine,
            only=[i[1].key or i[1].name for i in self._form_props],
            column_labels={k.key: v for k, v in self._column_labels.items()},
            form_args=self.form_args,
            form_widget_args=self.form_widget_args,
            form_class=self.form_base_class,
            form_overrides=self.form_overrides,
            form_ajax_refs=self._form_ajax_refs,
            form_include_pk=self.form_include_pk,
            form_converter=self.form_converter,
        )

    def search_placeholder(self) -> str:
        """Return search placeholder text.

        ???+ example
            ```python
            class UserAdmin(ModelView, model=User):
                column_labels = dict(name="Name", email="Email")
                column_searchable_list = [User.name, User.email]

            # placeholder is: "Name, Email"
            ```
        """

        search_fields = [
            map_attr_to_prop(attr, self) for attr in self.column_searchable_list
        ]
        field_names = [
            self._column_labels.get(field, field.key) for field in search_fields
        ]
        return ", ".join(field_names)

    def search_query(self, stmt: Select, term: str) -> Select:
        """Specify the search query given the SQLAlchemy statement
        and term to search for.
        It can be used for doing more complex queries like JSON objects. For example:

        ```py
        return stmt.filter(MyModel.name == term)
        ```
        """
        expressions = [
            cast(prop, String).ilike(f"%{term}%") for prop in self._search_fields
        ]
        return stmt.filter(or_(*expressions))

    def get_export_name(self, export_type: str) -> str:
        """The file name when exporting."""

        return f"{self.name}_{time.strftime('%Y-%m-%d_%H-%M-%S')}.{export_type}"

    def export_data(
        self,
        data: List[Any],
        export_type: str = "csv",
    ) -> StreamingResponse:
        if export_type == "csv":
            return self._export_csv(data)
        else:
            raise NotImplementedError("Only export_type='csv' is implemented.")

    def _export_csv(
        self,
        data: List[Any],
    ) -> StreamingResponse:
        def generate(writer: Writer) -> Generator[Any, None, None]:
            # Append the column titles at the beginning
            titles = [c[0] for c in self._export_props]
            yield writer.writerow(titles)

            for row in data:
                vals = [str(self.get_prop_value(row, c[1])) for c in self._export_props]
                yield writer.writerow(vals)

        # `get_export_name` can be subclassed.
        # So we want to keep the filename secure outside that method.
        filename = secure_filename(self.get_export_name(export_type="csv"))

        return StreamingResponse(
            content=stream_to_csv(generate),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment;filename={filename}"},
        )


class ModelAdmin(ModelView):
    def __init__(self) -> None:  # pragma: no cover
        import warnings

        warnings.warn(
            "The class `ModelAdmin` is deprectated, please use `ModelView instead.`",
            DeprecationWarning,
        )
        super().__init__()
