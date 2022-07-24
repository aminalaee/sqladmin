from typing import Union

from sqlalchemy.orm import ColumnProperty, RelationshipProperty

_MODEL_ATTR_TYPE = Union[ColumnProperty, RelationshipProperty]
