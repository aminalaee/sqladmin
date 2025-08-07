from typing import (
    Any,
    Callable,
    List,
    Protocol,
    Tuple,
    Union,
    runtime_checkable,
)

from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.orm import ColumnProperty, InstrumentedAttribute, RelationshipProperty
from sqlalchemy.sql.expression import Select
from starlette.requests import Request

MODEL_PROPERTY = Union[ColumnProperty, RelationshipProperty]
ENGINE_TYPE = Union[Engine, AsyncEngine]
MODEL_ATTR = Union[str, InstrumentedAttribute]


@runtime_checkable
class SimpleColumnFilter(Protocol):
    """Protocol for filters with simple value-based filtering"""

    title: str
    parameter_name: str

    async def lookups(
        self, request: Request, model: Any, run_query: Callable[[Select], Any]
    ) -> List[Tuple[str, str]]:
        ...

    async def get_filtered_query(self, query: Select, value: Any, model: Any) -> Select:
        ...


@runtime_checkable
class OperationColumnFilter(Protocol):
    """Protocol for filters with operation-based filtering"""

    title: str
    parameter_name: str
    has_operator: bool

    async def lookups(
        self, request: Request, model: Any, run_query: Callable[[Select], Any]
    ) -> List[Tuple[str, str]]:
        ...

    async def get_filtered_query(
        self, query: Select, operation: str, value: Any, model: Any
    ) -> Select:
        ...


ColumnFilter = Union[SimpleColumnFilter, OperationColumnFilter]
