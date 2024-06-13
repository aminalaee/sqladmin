from __future__ import annotations

from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.orm import ColumnProperty, InstrumentedAttribute, RelationshipProperty

MODEL_PROPERTY = ColumnProperty | RelationshipProperty
ENGINE_TYPE = Engine | AsyncEngine
MODEL_ATTR = str | InstrumentedAttribute
