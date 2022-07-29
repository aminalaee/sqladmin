from typing import Union

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import ColumnProperty, RelationshipProperty, Session

_MODEL_ATTR_TYPE = Union[ColumnProperty, RelationshipProperty]
_ENGINE_TYPE = Union[Session, AsyncSession]
