from dataclasses import dataclass
from typing import Any, ClassVar, List, Optional, Sequence, Type, Union, no_type_check

import anyio
from sqlalchemy import Column, func, inspect
from sqlalchemy.engine.base import Engine
from sqlalchemy.engine.cursor import CursorResult
from sqlalchemy.exc import NoInspectionAvailable
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql.expression import select
from starlette.requests import Request

from sqladmin.exceptions import InvalidColumnError, InvalidModelError

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
    """
    Metaclass used to specify class variables in ModelAdmin.
    """

    @no_type_check
    def __new__(mcls, name, bases, attrs: dict, **kwargs: Any):
        cls: Type["ModelAdmin"] = super().__new__(mcls, name, bases, attrs)

        model = kwargs.get("model", None)
        db = kwargs.get("db")

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
        cls.identity = model.__name__.lower()
        cls.model = model
        cls.db = db
        cls.name = attrs.get("name", cls.model.__name__)
        cls.name_plural = attrs.get("name_plural", f"{cls.name}s")

        mcls.setup_list_page_settings(cls, attrs)
        mcls.setup_detail_page_settings(cls, attrs)

        return cls

    @classmethod
    def get_column_by_attr(
        cls, model: type, attr: Union[str, InstrumentedAttribute]
    ) -> Column:
        """
        Get SQLAlchemy Column from Model using InstrumentedAttribute or name of Column.
        """

        try:
            mapper = inspect(model)
            if isinstance(attr, str):
                return mapper.columns[attr]
            else:
                return mapper.columns[attr.name]
        except KeyError:
            raise InvalidColumnError(
                f"Model '{model.__name__}' has no attribute '{attr}'."
            )

    @classmethod
    def get_model_columns(cls, model: type) -> List[Column]:
        return list(inspect(model).columns)

    @classmethod
    def setup_list_page_settings(cls, admin: Type["ModelAdmin"], attrs: dict) -> None:
        if "column_list" in attrs and "column_exclude_list" in attrs:
            raise Exception(
                "Cannot use 'column_list' and 'column_exclude_list' together."
            )
        elif "column_list" in attrs:
            column_list = attrs["column_list"]
            assert column_list, "Field 'column_list' cannot be empty."

            admin.column_list = [
                cls.get_column_by_attr(admin.model, attr) for attr in column_list
            ]
        elif "column_exclude_list" in attrs:
            column_exclude_list = attrs["column_exclude_list"]
            assert column_exclude_list, "Field 'column_exclude_list' cannot be empty."

            columns_exclude = [
                cls.get_column_by_attr(admin.model, attr)
                for attr in column_exclude_list
            ]
            columns = cls.get_model_columns(admin.model)
            admin.column_list = list(set(columns) - set(columns_exclude))
        else:
            admin.column_list = [admin.pk_column]

    @classmethod
    def setup_detail_page_settings(cls, admin: Type["ModelAdmin"], attrs: dict) -> None:
        if "column_details_list" in attrs and "column_details_exclude_list" in attrs:
            raise Exception(
                "Cannot use 'column_details_list' and "
                "'column_details_exclude_list' together."
            )
        elif "column_details_list" in attrs:
            column_list = attrs["column_details_list"]
            assert column_list, "Field 'column_details_list' cannot be empty."

            admin.column_details_list = [
                cls.get_column_by_attr(admin.model, attr) for attr in column_list
            ]
        elif "column_details_exclude_list" in attrs:
            column_exclude_list = attrs["column_details_exclude_list"]
            assert (
                column_exclude_list
            ), "Field 'column_details_exclude_list' cannot be empty."

            columns_exclude = [
                cls.get_column_by_attr(admin.model, attr)
                for attr in column_exclude_list
            ]
            columns = cls.get_model_columns(admin.model)
            admin.column_details_list = list(set(columns) - set(columns_exclude))
        else:
            admin.column_details_list = cls.get_model_columns(admin.model)


class ModelAdmin(metaclass=ModelAdminMeta):
    """
    Base class for defining admnistrative behaviour for the model.

    Usage:
        from sqladmin import ModelAdmin

        class ExampleAdmin(ModelAdmin, model=SQLAlchemyModel):
            can_create = True

    """

    model: ClassVar[type]
    db: ClassVar[Session]

    # Internals
    pk_column: ClassVar[Column]
    identity: ClassVar[str]

    # Metadata
    name: ClassVar[str]
    name_plural: ClassVar[str]
    icon: ClassVar[str]

    # Permissions
    can_create: ClassVar[bool] = True
    can_edit: ClassVar[bool] = True
    can_delete: ClassVar[bool] = True
    can_view_details: ClassVar[bool] = True

    # List page
    column_list: Sequence[Union[str, Column]]
    column_exclude_list: Sequence[Union[str, Column]]
    page_size: int = 10
    page_size_options: Sequence[int] = [10, 25, 50, 100]

    # Details page
    column_details_list: Sequence[Union[str, Column]]
    column_details_exclude_list: Sequence[Union[str, Column]]

    @classmethod
    async def _run_query(cls, query: str) -> CursorResult:
        """
        If using a sync driver, query will be run in a worker thread,
        otherwise it will run using the async driver.
        """

        engine: Union[Engine, AsyncEngine] = cls.db.get_bind()
        if isinstance(engine, Engine):
            return await anyio.to_thread.run_sync(cls.db.execute, query)
        else:
            async with engine.begin() as conn:
                return await conn.execute()

    @classmethod
    async def count(cls) -> int:
        query = select(func.count(cls.pk_column))
        result = await cls._run_query(query)

        return result.scalar()

    @classmethod
    async def paginate(cls, request: Request) -> Pagination:
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", cls.page_size))
        page_size = min(page_size, 100)

        query = select(cls.column_list).limit(page_size).offset((page - 1) * page_size)
        items = await cls._run_query(query)

        count = await cls.count()

        # TODO: Use query params from url_for
        # https://github.com/encode/starlette/pull/1385
        base_url = request.url_for("admin:list", identity=cls.identity)

        if page == 1:
            previous_page_url = None
        else:
            previous_page_url = base_url + f"?page={page - 1}"

        if (page * page_size) > count:
            next_page_url = None
        else:
            next_page_url = base_url + f"?page={page + 1}"

        return Pagination(
            rows=items.all(),
            page=page,
            page_size=page_size,
            count=count,
            previous_page_url=previous_page_url,
            next_page_url=next_page_url,
        )

    @classmethod
    async def get_model_by_pk(cls, value: Any) -> Any:
        query = select(cls.model).where(cls.pk_column == value)
        result = await cls._run_query(query)

        try:
            return result.scalar_one()
        except NoResultFound:
            return None

    @classmethod
    def get_column_value(cls, obj: type, column: Column) -> Any:
        return getattr(obj, column.name, None)
