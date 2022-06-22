from collections.abc import Iterable
from typing import Any


def is_iterable(obj: Any) -> bool:
    return isinstance(obj, Iterable) and not isinstance(obj, (str, bytes))
