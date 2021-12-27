from dataclasses import dataclass
from typing import Any, ClassVar, List, Optional, Type, Union, no_type_check

import anyio
from sqlalchemy import Column, func, inspect
from sqlalchemy.engine.base import Engine
from sqlalchemy.engine.cursor import CursorResult
from sqlalchemy.exc import NoInspectionAvailable
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import InstrumentedAttribute
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
    per_page: int
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

        cls.list_display = [
            mcls.get_column_by_attr(model, attr)
            for attr in attrs.get("list_display", [cls.pk_column])
        ]

        return cls

    @classmethod
    def get_column_by_attr(
        cls, model: type, attr: Union[str, InstrumentedAttribute, Column]
    ) -> Column:
        """
        Get SQLAlchemy Column from Model using Column or name of Column.
        """

        if not isinstance(attr, str):
            return attr

        try:
            return getattr(model, attr)
        except AttributeError:
            raise InvalidColumnError(
                f"Model '{model.__name__}' has no attribute '{attr}'."
            )


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
    list_display: List[Union[str, Column]]
    per_page_default: int = 10
    per_page_options: List[int] = [10, 25, 50, 100]

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
        per_page = int(request.query_params.get("per_page", cls.per_page_default))
        per_page = min(per_page, 100)

        query = select(cls.list_display).limit(per_page).offset((page - 1) * per_page)
        items = await cls._run_query(query)

        count = await cls.count()

        # TODO: Use query params from url_for
        # https://github.com/encode/starlette/pull/1385
        base_url = request.url_for("admin:list", identity=cls.identity)

        if page == 1:
            previous_page_url = None
        else:
            previous_page_url = base_url + f"?page={page - 1}"

        if (page * per_page) > count:
            next_page_url = None
        else:
            next_page_url = base_url + f"?page={page + 1}"

        return Pagination(
            rows=items.all(),
            page=page,
            per_page=per_page,
            count=count,
            previous_page_url=previous_page_url,
            next_page_url=next_page_url,
        )
