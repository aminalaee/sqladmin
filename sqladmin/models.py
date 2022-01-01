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
from sqlalchemy import Column, func, inspect
from sqlalchemy.engine.base import Engine
from sqlalchemy.engine.cursor import CursorResult
from sqlalchemy.exc import NoInspectionAvailable
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql.expression import delete, select
from starlette.requests import Request

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
    """
    Metaclass used to specify class variables in ModelAdmin.
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
        # else:
        #     return sessionmaker(bind=engine, class_=AsyncSession)


class ModelAdmin(metaclass=ModelAdminMeta):
    """
    Base class for defining admnistrative behaviour for the model.

    Usage:
        from sqladmin import ModelAdmin

        class ExampleAdmin(ModelAdmin, model=SQLAlchemyModel):
            can_create = True

    """

    model: ClassVar[type]
    engine: ClassVar[Union[Engine, AsyncEngine]]
    sessionmaker: ClassVar[sessionmaker]

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

    column_labels: Dict[Union[str, Column], str] = dict()

    @classmethod
    async def _run_query(cls, query: str) -> CursorResult:
        """
        If using a sync driver, query will be run in a worker thread,
        otherwise it will run using the async driver.
        """

        assert isinstance(cls.engine, (Engine, AsyncEngine))

        if isinstance(cls.engine, Engine):
            session: Session = cls.sessionmaker()
            return await anyio.to_thread.run_sync(session.execute, query)
        # else:
        #     async with cls.sessionmaker() as session:
        #         async with session.begin():
        #             return await session.execute(query)

    @classmethod
    async def count(cls) -> int:
        query = select(func.count(cls.pk_column))
        result = await cls._run_query(query)

        return result.scalar()

    @classmethod
    async def paginate(cls, request: Request) -> Pagination:
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", cls.page_size))
        page_size = min(page_size, max(cls.page_size_options))

        query = select(cls.model).limit(page_size).offset((page - 1) * page_size)
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
            rows=items.scalars().all(),
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
    async def delete_model(cls, pk: Any) -> None:
        query = delete(cls.model).where(cls.pk_column == pk)
        await cls._run_query(query)
