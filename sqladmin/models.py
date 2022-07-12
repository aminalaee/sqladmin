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

import anyio
from sqlalchemy import Column, asc, desc, func, inspect, or_, select
from sqlalchemy.engine.base import Engine
from sqlalchemy.exc import NoInspectionAvailable
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.orm import (
    ColumnProperty,
    RelationshipProperty,
    joinedload,
    sessionmaker,
)
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.sql.elements import ClauseElement
from starlette.requests import Request
from starlette.responses import StreamingResponse
from wtforms import Field, Form

from sqladmin.exceptions import InvalidColumnError, InvalidModelError
from sqladmin.formatters import BASE_FORMATTERS
from sqladmin.forms import get_model_form
from sqladmin.helpers import (
    Writer,
    as_str,
    prettify_class_name,
    secure_filename,
    slugify_class_name,
    stream_to_csv,
)
from sqladmin.pagination import Pagination

__all__ = [
    "ModelAdmin",
]


class ModelAdminMeta(type):
    """Metaclass used to specify class variables in ModelAdmin.

    Danger:
        This class should almost never be used directly.
    """

    @no_type_check
    def __new__(mcls, name, bases, attrs: dict, **kwargs: Any):
        cls: Type["ModelAdmin"] = super().__new__(mcls, name, bases, attrs)

        model = kwargs.get("model")

        if not model:
            return cls

        try:
            mapper = inspect(model)
        except NoInspectionAvailable:
            raise InvalidModelError(
                f"Class {model.__name__} is not a SQLAlchemy model."
            )

        assert len(mapper.primary_key) == 1, "Multiple PK columns not supported."

        cls.pk_column = mapper.primary_key[0]
        cls.identity = slugify_class_name(model.__name__)
        cls.model = model

        cls.name = attrs.get("name", prettify_class_name(cls.model.__name__))
        cls.name_plural = attrs.get("name_plural", f"{cls.name}s")
        cls.icon = attrs.get("icon")

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


class BaseModelAdmin:
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


class ModelAdmin(BaseModelAdmin, metaclass=ModelAdminMeta):
    """Base class for defining admnistrative behaviour for the model.

    ???+ usage
        ```python
        from sqladmin import ModelAdmin

        from mymodels import User # SQLAlchemy model

        class UserAdmin(ModelAdmin, model=User):
            can_create = True
        ```
    """

    model: ClassVar[type]

    # Internals
    pk_column: ClassVar[Column]
    identity: ClassVar[str]
    sessionmaker: ClassVar[sessionmaker]
    engine: ClassVar[Union[Engine, AsyncEngine]]
    async_engine: ClassVar[bool]
    url_path_for: ClassVar[Callable]

    # Metadata
    name: ClassVar[str] = ""
    """Name of ModelAdmin to display.
    Default value is set to Model class name.
    """

    name_plural: ClassVar[str] = ""
    """Plural name of ModelAdmin.
    Default value is Model class name + `s`.
    """

    icon: ClassVar[str] = ""
    """Display icon for ModelAdmin in the sidebar.
    Currently only supports FontAwesome icons.

    ???+ example
        ```python
        class UserAdmin(ModelAdmin, model=User):
            icon = "fa-solid fa-user"
        ```
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
        class UserAdmin(ModelAdmin, model=User):
            column_list = [User.id, User.name]
        ```
    """

    column_exclude_list: ClassVar[Sequence[Union[str, InstrumentedAttribute]]] = []
    """List of columns to exclude in `List` page.
    Columns can either be string names or SQLAlchemy columns.

    ???+ example
        ```python
        class UserAdmin(ModelAdmin, model=User):
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
        class UserAdmin(ModelAdmin, model=User):
            column_formatters = {User.name: lambda m, a: m.name[:10]}
        ```

    The format function has the prototype:
    ???+ formatter
        ```python
        def formatter(model, attribute):
            # `model` is model instance
            # `attribute` is a Union[Column, ColumnProperty, RelationshipProperty]
            pass
        ```
    """

    page_size: ClassVar[int] = 10
    """Default number of items to display in `List` page pagination.
    Default value is set to `10`.

    ???+ example
        ```python
        class UserAdmin(ModelAdmin, model=User):
            page_size = 25
        ```
    """

    page_size_options: ClassVar[Sequence[int]] = [10, 25, 50, 100]
    """Pagination choices displayed in `List` page.
    Default value is set to `[10, 25, 50, 100]`.

    ???+ example
        ```python
        class UserAdmin(ModelAdmin, model=User):
            page_size_options = [50, 100]
        ```
    """

    column_searchable_list: ClassVar[Sequence[Union[str, InstrumentedAttribute]]] = []
    """A collection of the searchable columns.
    It is assumed that only text-only fields are searchable,
    but it is up to the model implementation to decide.

    ???+ example
        ```python
        class UserAdmin(ModelAdmin, model=User):
            column_searchable_list = [User.name]
        ```
    """

    column_sortable_list: ClassVar[Sequence[Union[str, InstrumentedAttribute]]] = []
    """Collection of the sortable columns for the list view.

    ???+ example
        ```python
        class UserAdmin(ModelAdmin, model=User):
            column_sortable_list = [User.name]
        ```
    """

    column_default_sort: ClassVar[Union[str, tuple, list]] = []
    """Default sort column if no sorting is applied.

    ???+ example
        ```python
        class UserAdmin(ModelAdmin, model=User):
            column_default_sort = "email"
        ```

    You can use tuple to control ascending descending order. In following example, items
    will be sorted in descending order:

    ???+ example
        ```python
        class UserAdmin(ModelAdmin, model=User):
            column_default_sort = ("email", True)
        ```

    If you want to sort by more than one column, you can pass a list of tuples

    ???+ example
        ```python
        class UserAdmin(ModelAdmin, model=User):
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
        class UserAdmin(ModelAdmin, model=User):
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
        class UserAdmin(ModelAdmin, model=User):
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
        class UserAdmin(ModelAdmin, model=User):
            column_formatters_detail = {User.name: lambda m, a: m.name[:10]}
        ```

    The format function has the prototype:
    ???+ formatter
        ```python
        def formatter(model, attribute):
            # `model` is model instance
            # `attribute` is a Union[Column, ColumnProperty, RelationshipProperty]
            pass
        ```
    """

    column_labels: ClassVar[Dict[Union[str, InstrumentedAttribute], str]] = {}
    """A mapping of column labels, used to map column names to new names.
    Dictionary keys can be string names or SQLAlchemy columns with string values.

    ???+ example
        ```python
        class UserAdmin(ModelAdmin, model=User):
            column_labels = {User.mail: "Email"}
        ```
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
        class UserAdmin(ModelAdmin, model=User):
            column_export_list = [User.id, User.name]
        ```
    """

    column_export_exclude_list: ClassVar[List[Union[str, InstrumentedAttribute]]] = []
    """List of columns to exclude when exporting.
    Columns can either be string names or SQLAlchemy columns.

    ???+ example
        ```python
        class UserAdmin(ModelAdmin, model=User):
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

        class MyModelAdmin(ModelAdmin, model=User):
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

        class MyModelAdmin(ModelAdmin, model=User):
            form_base_class = MyBaseForm
        ```
    """

    form_args: ClassVar[Dict[str, Dict[str, Any]]] = {}
    """Dictionary of form field arguments.
    Refer to WTForms documentation for list of possible options.

    ???+ example
        ```python
        from wtforms.validators import DataRequired

        class MyModelAdmin(ModelAdmin, model=User):
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
        class UserAdmin(ModelAdmin, model=User):
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
        class UserAdmin(ModelAdmin, model=User):
            form_columns = [User.name, User.mail]
        ```
    """

    form_excluded_columns: ClassVar[Sequence[Union[str, InstrumentedAttribute]]] = []
    """List of columns to exclude from the form.
    Columns can either be string names or SQLAlchemy columns.

    ???+ example
        ```python
        class UserAdmin(ModelAdmin, model=User):
            form_excluded_columns = [User.id]
        ```
    """

    form_overrides: ClassVar[Dict[str, Type[Field]]] = {}
    """Dictionary of form column overrides.

    ???+ example
        ```python
        class UserAdmin(ModelAdmin, model=User):
            form_overrides = dict(name=wtf.FileField)
        ```
    """

    form_include_pk: ClassVar[bool] = False
    """Control if form should include primary key columns or not.

    ???+ example
        ```python
        class UserAdmin(ModelAdmin, model=User):
            form_include_pk = True
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
        class UserAdmin(ModelAdmin, model=User):
            column_type_formatters = dict()
        ```
    """

    def __init__(self) -> None:
        self._column_labels = self.get_column_labels()
        self._column_labels_value_by_key = {
            v: k for k, v in self._column_labels.items()
        }

        self._relations = list(inspect(self.model).relationships)

        self._list_attrs = self.get_list_columns()
        self._list_columns = [
            (name, attr)
            for (name, attr) in self._list_attrs
            if isinstance(attr, ColumnProperty)
        ]

        self._details_attrs = self.get_details_columns()
        self._details_columns = [
            (name, attr)
            for (name, attr) in self._details_attrs
            if isinstance(attr, ColumnProperty)
        ]

        column_formatters = getattr(self, "column_formatters", {})
        self._list_formatters = {
            self.get_model_attr(attr): formatter
            for (attr, formatter) in column_formatters.items()
        }

        column_formatters_detail = getattr(self, "column_formatters_detail", {})
        self._detail_formatters = {
            self.get_model_attr(attr): formatter
            for (attr, formatter) in column_formatters_detail.items()
        }

        self._form_attrs = self.get_form_columns()

        self._export_attrs = self.get_export_columns()

        self._search_fields = [
            getattr(self.model, self.get_model_attr(attr).key)
            for attr in self.column_searchable_list
        ]

        self._sort_fields = [
            getattr(self.model, self.get_model_attr(attr).key)
            for attr in self.column_sortable_list
        ]

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

    def _add_object_sync(self, obj: Any) -> None:
        with self.sessionmaker.begin() as session:
            session.add(obj)

    def _delete_object_sync(self, obj: Any) -> None:
        with self.sessionmaker.begin() as session:
            session.delete(obj)

    def _update_modeL_sync(self, pk: Any, data: Dict[str, Any]) -> None:
        stmt = select(self.model).where(
            self.pk_column == self._get_column_python_type(self.pk_column)(pk)
        )
        relationships = inspect(self.model).relationships

        with self.sessionmaker.begin() as session:
            result = session.execute(stmt).scalars().first()
            for name, value in data.items():
                if name in relationships and isinstance(value, list):
                    # Load relationship objects into session
                    session.add_all(value)
                setattr(result, name, value)

    def _get_column_python_type(self, column: Column) -> type:
        try:
            return column.type.python_type
        except NotImplementedError:
            return str

    def _url_for_details(self, obj: Any) -> str:
        pk = getattr(obj, inspect(obj).mapper.primary_key[0].name)
        return self.url_path_for(
            "admin:details",
            identity=slugify_class_name(obj.__class__.__name__),
            pk=pk,
        )

    def _url_for_edit(self, obj: Any) -> str:
        pk = getattr(obj, inspect(obj).mapper.primary_key[0].name)
        return self.url_path_for(
            "admin:edit",
            identity=slugify_class_name(obj.__class__.__name__),
            pk=pk,
        )

    def _url_for_delete(self, obj: Any) -> str:
        pk = getattr(obj, inspect(obj).mapper.primary_key[0].name)
        return self.url_path_for(
            "admin:delete",
            identity=slugify_class_name(obj.__class__.__name__),
            pk=pk,
        )

    def _url_for_details_with_attr(self, obj: Any, attr: RelationshipProperty) -> str:
        target = getattr(obj, attr.key)
        if target is None:
            return ""

        pk = getattr(target, attr.mapper.primary_key[0].name)
        return self.url_path_for(
            "admin:details",
            identity=slugify_class_name(target.__class__.__name__),
            pk=pk,
        )

    def _get_default_sort(self) -> List[tuple]:
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
        stmt = select(func.count(self.pk_column))
        rows = await self._run_query(stmt)
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
        stmt = select(self.model).limit(page_size).offset((page - 1) * page_size)

        for relation in self._relations:
            stmt = stmt.options(joinedload(relation.key))

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
            expressions = [attr.ilike(f"%{search}%") for attr in self._search_fields]
            stmt = stmt.filter(or_(*expressions))

        rows = await self._run_query(stmt)
        pagination = Pagination(
            rows=rows,
            page=page,
            page_size=page_size,
            count=count,
        )

        return pagination

    async def get_model_objects(self, limit: int = 0) -> List[Any]:
        # For unlimited rows this should pass None
        limit = None if limit == 0 else limit
        stmt = select(self.model).limit(limit=limit)

        for relation in self._relations:
            stmt = stmt.options(joinedload(relation.key))

        rows = await self._run_query(stmt)
        return rows

    async def get_model_by_pk(self, value: Any) -> Any:
        stmt = select(self.model).where(
            self.pk_column == self._get_column_python_type(self.pk_column)(value)
        )

        for relation in self._relations:
            stmt = stmt.options(joinedload(relation.key))

        rows = await self._run_query(stmt)
        if rows:
            return rows[0]
        return None

    def get_attr_value(
        self, obj: type, attr: Union[Column, ColumnProperty, RelationshipProperty]
    ) -> Any:
        result = None

        if isinstance(attr, Column):
            result = getattr(obj, attr.name)

        if isinstance(attr, (ColumnProperty, RelationshipProperty)):
            result = getattr(obj, attr.key)
            result = result.value if isinstance(result, Enum) else result

        return result

    def get_list_value(
        self, obj: type, attr: Union[Column, ColumnProperty, RelationshipProperty]
    ) -> Tuple[Any, Any]:
        """Get tuple of (value, formatted_value) for the list view."""
        value = self.get_attr_value(obj, attr)
        formatted_value = self._default_formatter(value)

        formatter = self._list_formatters.get(attr)
        if formatter:
            formatted_value = formatter(obj, attr)
        return value, formatted_value

    def get_detail_value(
        self, obj: type, attr: Union[Column, ColumnProperty, RelationshipProperty]
    ) -> Tuple[Any, Any]:
        """Get tuple of (value, formatted_value) for the detail view."""
        value = self.get_attr_value(obj, attr)
        formatted_value = self._default_formatter(value)

        formatter = self._detail_formatters.get(attr)
        if formatter:
            formatted_value = formatter(obj, attr)
        return value, formatted_value

    def get_model_attr(
        self, attr: Union[str, InstrumentedAttribute]
    ) -> Union[ColumnProperty, RelationshipProperty]:
        assert isinstance(attr, (str, InstrumentedAttribute))

        if isinstance(attr, str):
            key = attr
        elif isinstance(attr.prop, ColumnProperty):
            key = attr.key
        elif isinstance(attr.prop, RelationshipProperty):
            key = attr.prop.key

        if key in inspect(self.model).attrs:
            return inspect(self.model).attrs[key]

        # Get value by column label
        if key in self._column_labels_value_by_key:
            return self._column_labels_value_by_key[key]

        raise InvalidColumnError(
            f"Model '{self.model.__name__}' has no attribute '{key}'."
        )

    def get_model_attributes(self) -> List[Column]:
        return list(inspect(self.model).attrs)

    def _build_column_list(
        self,
        include: Optional[Sequence[Union[str, InstrumentedAttribute]]] = None,
        exclude: Optional[Sequence[Union[str, InstrumentedAttribute]]] = None,
        default: Callable[[], List[Column]] = None,
    ) -> List[Tuple[str, Column]]:
        """This function generalizes constructing a list of columns
        for any sequence of inclusions or exclusions.
        """
        if include:
            attrs = [self.get_model_attr(attr) for attr in include]
        elif exclude:
            exclude_columns = [self.get_model_attr(attr) for attr in exclude]
            all_attrs = self.get_model_attributes()
            attrs = list(set(all_attrs) - set(exclude_columns))
        else:
            attrs = default()

        return [(self._column_labels.get(attr, attr.key), attr) for attr in attrs]

    def get_list_columns(self) -> List[Tuple[str, Column]]:
        """Get list of columns to display in List page."""

        column_list = getattr(self, "column_list", None)
        column_exclude_list = getattr(self, "column_exclude_list", None)

        return self._build_column_list(
            include=column_list,
            exclude=column_exclude_list,
            default=lambda: [getattr(self.model, self.pk_column.name).prop],
        )

    def get_details_columns(self) -> List[Tuple[str, Column]]:
        """Get list of columns to display in Detail page."""

        column_details_list = getattr(self, "column_details_list", None)
        column_details_exclude_list = getattr(self, "column_details_exclude_list", None)

        return self._build_column_list(
            include=column_details_list,
            exclude=column_details_exclude_list,
            default=self.get_model_attributes,
        )

    def get_form_columns(self) -> List[Tuple[str, Column]]:
        """Get list of columns to display in the form."""

        form_columns = getattr(self, "form_columns", None)
        form_excluded_columns = getattr(self, "form_excluded_columns", None)

        return self._build_column_list(
            include=form_columns,
            exclude=form_excluded_columns,
            default=self.get_model_attributes,
        )

    def get_export_columns(self) -> List[Tuple[str, Column]]:
        """Get list of columns to export."""

        columns = getattr(self, "column_export_list", None)
        excluded_columns = getattr(self, "column_export_exclude_list", None)
        if not columns and not excluded_columns:
            return self.get_list_columns()

        return self._build_column_list(
            include=columns,
            exclude=excluded_columns,
            default=lambda: self._list_columns,
        )

    def get_column_labels(self) -> Dict[Column, str]:
        return {
            self.get_model_attr(column_label): value
            for column_label, value in self.column_labels.items()
        }

    async def delete_model(self, obj: Any) -> None:
        if self.async_engine:
            async with self.sessionmaker.begin() as session:
                await session.delete(obj)
        else:
            await anyio.to_thread.run_sync(self._delete_object_sync, obj)

    async def insert_model(self, obj: type) -> Any:
        if self.async_engine:
            async with self.sessionmaker.begin() as session:
                session.add(obj)
        else:
            await anyio.to_thread.run_sync(self._add_object_sync, obj)

    async def update_model(self, pk: Any, data: Dict[str, Any]) -> None:
        if self.async_engine:
            stmt = select(self.model).where(
                self.pk_column == self._get_column_python_type(self.pk_column)(pk)
            )

            for relation in self._relations:
                stmt = stmt.options(joinedload(relation.key))

            async with self.sessionmaker.begin() as session:
                result = await session.execute(stmt)
                result = result.scalars().first()
                for name, value in data.items():
                    if isinstance(value, list) and name in [
                        relation.key for relation in self._relations
                    ]:
                        # Load relationship objects into session
                        session.add_all(value)
                    setattr(result, name, value)
        else:
            await anyio.to_thread.run_sync(self._update_modeL_sync, pk, data)

    async def scaffold_form(self) -> Type[Form]:
        if self.form is not None:
            return self.form
        return await get_model_form(
            model=self.model,
            engine=self.engine,
            only=[i[1].key for i in self._form_attrs],
            column_labels={k.key: v for k, v in self._column_labels.items()},
            form_args=self.form_args,
            form_widget_args=self.form_widget_args,
            form_class=self.form_base_class,
            form_overrides=self.form_overrides,
            form_include_pk=self.form_include_pk,
        )

    def search_placeholder(self) -> str:
        """Return search placeholder text.

        ???+ example
            ```python
            class UserAdmin(ModelAdmin, model=User):
                column_labels = dict(name="Name", email="Email")
                column_searchable_list = [User.name, User.email]

            # placeholder is: "Name, Email"
            ```
        """

        search_fields = [
            self.get_model_attr(attr) for attr in self.column_searchable_list
        ]
        field_names = [
            self._column_labels.get(field, field.key) for field in search_fields
        ]
        return ", ".join(field_names)

    def get_export_name(self, export_type: str) -> str:
        """The file name when exporting."""
        filename = f"{self.name}_{time.strftime('%Y-%m-%d_%H-%M-%S')}.{export_type}"
        return filename

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
        def generate(writer: Writer) -> Generator[List[str], None, None]:
            # Append the column titles at the beginning
            titles = [c[0] for c in self._export_attrs]
            yield writer.writerow(titles)

            for row in data:
                vals = [
                    as_str(self.get_attr_value(row, c[1])) for c in self._export_attrs
                ]
                yield writer.writerow(vals)

        # `get_export_name` can be subclassed.
        # So we want to keep the filename secure outside that method.
        filename = secure_filename(self.get_export_name(export_type="csv"))

        return StreamingResponse(
            content=stream_to_csv(generate),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment;filename={filename}"},
        )
