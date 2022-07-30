from typing import Union

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import ColumnProperty, RelationshipProperty, Session

MODEL_ATTR_TYPE = Union[ColumnProperty, RelationshipProperty]
ENGINE_TYPE = Union[Session, AsyncSession]
