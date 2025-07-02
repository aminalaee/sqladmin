from typing import Any, Callable, List, Protocol, Tuple, Union, runtime_checkable

from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.orm import ColumnProperty, InstrumentedAttribute, RelationshipProperty
from sqlalchemy.sql.expression import Select
from starlette.requests import Request

MODEL_PROPERTY = Union[ColumnProperty, RelationshipProperty]
ENGINE_TYPE = Union[Engine, AsyncEngine]
MODEL_ATTR = Union[str, InstrumentedAttribute]


@runtime_checkable
class ColumnFilter(Protocol):
    title: str
    parameter_name: str

    async def lookups(
        self, request: Request, model: Any, run_query: Callable[[Select], Any]
    ) -> List[Tuple[str, str]]:
        ...

    async def get_filtered_query(self, query: Select, value: Any, model: Any) -> Select:
        ...
