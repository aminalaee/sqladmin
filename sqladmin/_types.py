from typing import Union

from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.orm import ColumnProperty, RelationshipProperty

MODEL_PROPERTY = Union[ColumnProperty, RelationshipProperty]
ENGINE_TYPE = Union[Engine, AsyncEngine]
