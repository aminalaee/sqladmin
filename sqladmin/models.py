from dataclasses import dataclass
from typing import (
    Any,
    ClassVar,
    Dict,
    List,
    Optional,
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
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.orm.exc import NoResultFound

from sqladmin.exceptions import InvalidColumnError, InvalidModelError
from sqladmin.helpers import prettify_class_name, slugify_class_name

__all__ = [
    "ModelAdmin",
]


@dataclass
class Pagination:
    rows: List[Any]
    page: int
    page_size: int
    count: int
    next_page_url: Optional[str] = None
    previous_page_url: Optional[str] = None


class ModelAdminMeta(type):
    """Metaclass used to specify class variables in ModelAdmin.

    Danger:
        This class should almost never be used directly.
    """

    @no_type_check
    def __new__(mcls, name, bases, attrs: dict, **kwargs: Any):
        cls: Type["ModelAdmin"] = super().__new__(mcls, name, bases, attrs)

        model = kwargs.get("model", None)

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
        cls.icon = attrs.get("icon", None)

        mcls._check_conflicting_options(["column_list", "column_exclude_list"], attrs)
        mcls._check_conflicting_options(
            ["column_details_list", "column_details_exclude_list"], attrs
        )

        return cls

    @classmethod
    def _check_conflicting_options(cls, keys: List[str], attrs: dict) -> None:
        if all(k in attrs for k in keys):
            raise AssertionError(f"Cannot use {' and '.join(keys)} together.")

    @classmethod
    def _get_sessionmaker(mcls, engine: Union[Engine, AsyncEngine]) -> None:
        if isinstance(engine, Engine):
            return sessionmaker(bind=engine, class_=Session)
        else:
            return sessionmaker(bind=engine, class_=AsyncSession)


class ModelAdmin(metaclass=ModelAdminMeta):
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
    """A dict of column labels, used to map column names to new names.
    Dictionary keys can be string names or SQLAlchemy columns with string values.

    ???+ example
        ```python
        class UserAdmin(ModelAdmin, model=User):
            column_labels = {User.mail: "Email"}
        ```
    """

    @classmethod
    async def count(cls) -> int:
        query = select(func.count(cls.pk_column))

        if isinstance(cls.engine, Engine):
            with cls.sessionmaker() as session:
                result = await anyio.to_thread.run_sync(session.execute, query)
                return result.scalar_one()
        else:
            async with cls.sessionmaker() as session:
                result = await session.execute(query)
                return result.scalar_one()

    @classmethod
    async def list(cls, page: int, page_size: int) -> Pagination:
        page_size = min(page_size or cls.page_size, max(cls.page_size_options))

        count = await cls.count()
        query = select(cls.model).limit(page_size).offset((page - 1) * page_size)

        pagination = Pagination(
            rows=[],
            page=page,
            page_size=page_size,
            count=count,
        )

        if isinstance(cls.engine, Engine):
            with cls.sessionmaker() as session:
                items = await anyio.to_thread.run_sync(session.execute, query)
                pagination.rows = items.scalars().all()
                return pagination
        else:
            async with cls.sessionmaker() as session:
                items = await session.execute(query)
                pagination.rows = items.scalars().all()
                return pagination

    @classmethod
    async def get_model_by_pk(cls, value: Any) -> Any:
        query = select(cls.model).where(cls.pk_column == value)

        if isinstance(cls.engine, Engine):
            with cls.sessionmaker() as session:
                result = await anyio.to_thread.run_sync(session.execute, query)
                try:
                    return result.scalar_one()
                except NoResultFound:
                    return None
        else:
            async with cls.sessionmaker() as session:
                result = await session.execute(query)
                try:
                    return result.scalar_one()
                except NoResultFound:
                    return None

    @classmethod
    def get_column_value(cls, obj: type, column: Column) -> Any:
        return getattr(obj, column.name, None)

    @classmethod
    def get_column_by_attr(cls, attr: Union[str, InstrumentedAttribute]) -> Column:
        try:
            mapper = inspect(cls.model)
            if isinstance(attr, str):
                return mapper.columns[attr]
            else:
                return mapper.columns[attr.name]
        except KeyError:
            raise InvalidColumnError(
                f"Model '{cls.model.__name__}' has no attribute '{attr}'."
            )

    @classmethod
    def get_model_columns(cls) -> List[Column]:
        return list(inspect(cls.model).columns)

    @classmethod
    def get_list_columns(cls) -> List[Tuple[str, Column]]:
        """Get list of columns to display in Detail page."""

        column_list = getattr(cls, "column_list", None)
        column_exclude_list = getattr(cls, "column_exclude_list", None)

        if column_list:
            columns = [cls.get_column_by_attr(attr) for attr in cls.column_list]
        elif column_exclude_list:
            exclude_columns = [
                cls.get_column_by_attr(attr) for attr in column_exclude_list
            ]
            all_columns = cls.get_model_columns()
            columns = list(set(all_columns) - set(exclude_columns))
        else:
            columns = [cls.pk_column]

        return [(cls.get_column_labels().get(c, c.name), c) for c in columns]

    @classmethod
    def get_details_columns(cls) -> List[Tuple[str, Column]]:
        """Get list of columns to display in Detail page."""

        column_details_list = getattr(cls, "column_details_list", None)
        column_details_exclude_list = getattr(cls, "column_details_exclude_list", None)

        if column_details_list:
            columns = [cls.get_column_by_attr(attr) for attr in column_details_list]
        elif column_details_exclude_list:
            exclude_columns = [
                cls.get_column_by_attr(attr) for attr in column_details_exclude_list
            ]
            all_columns = cls.get_model_columns()
            columns = list(set(all_columns) - set(exclude_columns))
        else:
            columns = cls.get_model_columns()

        return [(cls.get_column_labels().get(c, c.name), c) for c in columns]

    @classmethod
    def get_column_labels(cls) -> Dict[Column, str]:
        column_labels = {}
        for column_label, value in cls.column_labels.items():
            column_labels[cls.get_column_by_attr(column_label)] = value

        return column_labels

    @classmethod
    async def delete_model(cls, obj: str) -> None:
        if isinstance(cls.engine, Engine):
            with cls.sessionmaker.begin() as session:
                await anyio.to_thread.run_sync(session.delete, obj)
        else:
            async with cls.sessionmaker.begin() as session:
                await session.delete(obj)
