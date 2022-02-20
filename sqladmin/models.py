from typing import (
    Any,
    ClassVar,
    Dict,
    List,
    Sequence,
    Tuple,
    Type,
    Union,
    no_type_check,
)

import anyio
from sqlalchemy import Column, func, inspect, select
from sqlalchemy.engine.base import Engine
from sqlalchemy.exc import NoInspectionAvailable
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import (
    ColumnProperty,
    RelationshipProperty,
    Session,
    selectinload,
    sessionmaker,
)
from sqlalchemy.orm.attributes import InstrumentedAttribute
from starlette.requests import Request
from wtforms import Form

from sqladmin.exceptions import InvalidColumnError, InvalidModelError
from sqladmin.forms import get_model_form
from sqladmin.helpers import prettify_class_name, slugify_class_name
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
            ["column_details_list", "column_details_exclude_list"], attrs
        )

        return cls

    @classmethod
    def _check_conflicting_options(mcls, keys: List[str], attrs: dict) -> None:
        if all(k in attrs for k in keys):
            raise AssertionError(f"Cannot use {' and '.join(keys)} together.")

    @classmethod
    def _get_sessionmaker(mcls, engine: Union[Engine, AsyncEngine]) -> None:
        if isinstance(engine, Engine):
            return sessionmaker(bind=engine, class_=Session)
        else:
            return sessionmaker(bind=engine, class_=AsyncSession)


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
    engine: ClassVar[Union[Engine, AsyncEngine]]
    sessionmaker: ClassVar[sessionmaker]

    # Internals
    pk_column: ClassVar[Column]
    identity: ClassVar[str]

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
            icon = "fas fa-user"
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
    """Default edit template"""

    async def count(self) -> int:
        query = select(func.count(self.pk_column))

        if isinstance(self.engine, Engine):
            with self.sessionmaker() as session:
                result = await anyio.to_thread.run_sync(session.execute, query)
                return result.scalar_one()
        else:
            async with self.sessionmaker() as session:
                result = await session.execute(query)
                return result.scalar_one()

    async def list(self, page: int, page_size: int) -> Pagination:
        page_size = min(page_size or self.page_size, max(self.page_size_options))

        count = await self.count()
        query = (
            select(self.model)
            .order_by(self.pk_column)
            .limit(page_size)
            .offset((page - 1) * page_size)
        )

        for _, attr in self.get_list_columns():
            if isinstance(attr, RelationshipProperty):
                query = query.options(selectinload(attr.key))

        pagination = Pagination(
            rows=[],
            page=page,
            page_size=page_size,
            count=count,
        )

        if isinstance(self.engine, Engine):
            with self.sessionmaker() as session:
                items = await anyio.to_thread.run_sync(session.execute, query)
                pagination.rows = items.scalars().all()
                return pagination
        else:
            async with self.sessionmaker() as session:
                items = await session.execute(query)
                pagination.rows = items.scalars().all()
                return pagination

    async def get_model_by_pk(self, value: Any) -> Any:
        query = select(self.model).where(self.pk_column == value)

        for _, attr in self.get_details_columns():
            if isinstance(attr, RelationshipProperty):
                query = query.options(selectinload(attr.key))

        if isinstance(self.engine, Engine):
            with self.sessionmaker() as session:
                result = await anyio.to_thread.run_sync(session.execute, query)
                return result.scalar_one_or_none()
        else:
            async with self.sessionmaker() as session:
                result = await session.execute(query)
                return result.scalar_one_or_none()

    def get_attr_value(
        self, obj: type, attr: Union[Column, ColumnProperty, RelationshipProperty]
    ) -> Any:
        if isinstance(attr, Column):
            return getattr(obj, attr.name)
        else:
            value = getattr(obj, attr.key)
            if isinstance(value, list):
                return ", ".join(map(str, value))
            return value

    def get_model_attr(
        self, attr: Union[str, InstrumentedAttribute]
    ) -> Union[ColumnProperty, RelationshipProperty]:
        assert isinstance(attr, (str, InstrumentedAttribute))

        if isinstance(attr, str):
            key = attr
        elif isinstance(attr.prop, ColumnProperty):
            key = attr.name
        elif isinstance(attr.prop, RelationshipProperty):
            key = attr.prop.key

        try:
            return inspect(self.model).attrs[key]
        except KeyError:
            raise InvalidColumnError(
                f"Model '{self.model.__name__}' has no attribute '{attr}'."
            )

    def get_model_attributes(self) -> List[Column]:
        return list(inspect(self.model).attrs)

    def get_list_columns(self) -> List[Tuple[str, Column]]:
        """Get list of columns to display in List page."""

        column_list = getattr(self, "column_list", None)
        column_exclude_list = getattr(self, "column_exclude_list", None)

        if column_list:
            attrs = [self.get_model_attr(attr) for attr in self.column_list]
        elif column_exclude_list:
            exclude_columns = [
                self.get_model_attr(attr) for attr in column_exclude_list
            ]
            all_attrs = self.get_model_attributes()
            attrs = list(set(all_attrs) - set(exclude_columns))
        else:
            attrs = [getattr(self.model, self.pk_column.name).prop]

        labels = self.get_column_labels()
        return [(labels.get(attr, attr.key), attr) for attr in attrs]

    def get_details_columns(self) -> List[Tuple[str, Column]]:
        """Get list of columns to display in Detail page."""

        column_details_list = getattr(self, "column_details_list", None)
        column_details_exclude_list = getattr(self, "column_details_exclude_list", None)

        if column_details_list:
            attrs = [self.get_model_attr(attr) for attr in column_details_list]
        elif column_details_exclude_list:
            exclude_columns = [
                self.get_model_attr(attr) for attr in column_details_exclude_list
            ]
            all_attrs = self.get_model_attributes()
            attrs = list(set(all_attrs) - set(exclude_columns))
        else:
            attrs = self.get_model_attributes()

        labels = self.get_column_labels()
        return [(labels.get(attr, attr.key), attr) for attr in attrs]

    def get_column_labels(self) -> Dict[Column, str]:
        return {
            self.get_model_attr(column_label): value
            for column_label, value in self.column_labels.items()
        }

    async def delete_model(self, obj: type) -> None:
        if isinstance(self.engine, Engine):
            with self.sessionmaker.begin() as session:
                await anyio.to_thread.run_sync(session.delete, obj)
        else:
            async with self.sessionmaker.begin() as session:
                await session.delete(obj)

    async def insert_model(self, obj: type) -> Any:
        if isinstance(self.engine, Engine):
            with self.sessionmaker.begin() as session:
                await anyio.to_thread.run_sync(session.add, obj)
        else:
            async with self.sessionmaker.begin() as session:
                session.add(obj)

    async def update_model(self, pk: Any, data: Dict[str, Any]) -> None:
        stmt = select(self.model).where(self.pk_column == pk)
        relationships = inspect(self.model).relationships

        for name in relationships.keys():
            stmt = stmt.options(selectinload(name))

        if isinstance(self.engine, Engine):
            with self.sessionmaker.begin() as session:
                result = session.execute(stmt).scalars().first()
                for name, value in data.items():
                    if (
                        name in relationships
                        and relationships[name].direction.name != "MANYTOONE"
                    ):
                        # Load relationship objects into session
                        session.add_all(value)
                    setattr(result, name, value)
        else:
            async with self.sessionmaker.begin() as session:
                result = await session.execute(stmt)
                result = result.scalars().first()
                for name, value in data.items():
                    if (
                        name in relationships
                        and relationships[name].direction.name != "MANYTOONE"
                    ):
                        # Load relationship objects into session
                        session.add_all(value)
                    setattr(result, name, value)

    async def scaffold_form(self) -> Type[Form]:
        return await get_model_form(model=self.model, engine=self.engine)
