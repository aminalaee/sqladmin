import csv
import os
import re
import unicodedata
from abc import ABC, abstractmethod
from datetime import timedelta
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Generator,
    List,
    Optional,
    TypeVar,
    Union,
)

from sqlalchemy import Column, inspect
from sqlalchemy.orm import RelationshipProperty
from sqlalchemy.orm.attributes import InstrumentedAttribute

from sqladmin._types import MODEL_PROPERTY
from sqladmin.exceptions import InvalidColumnError

if TYPE_CHECKING:
    from sqladmin.models import ModelView

T = TypeVar("T")


_filename_ascii_strip_re = re.compile(r"[^A-Za-z0-9_.-]")
_windows_device_files = (
    "CON",
    "AUX",
    "COM1",
    "COM2",
    "COM3",
    "COM4",
    "LPT1",
    "LPT2",
    "LPT3",
    "PRN",
    "NUL",
)

standard_duration_re = re.compile(
    r"^"
    r"(?:(?P<days>-?\d+) (days?, )?)?"
    r"(?P<sign>-?)"
    r"((?:(?P<hours>\d+):)(?=\d+:\d+))?"
    r"(?:(?P<minutes>\d+):)?"
    r"(?P<seconds>\d+)"
    r"(?:[\.,](?P<microseconds>\d{1,6})\d{0,6})?"
    r"$"
)

# Support the sections of ISO 8601 date representation that are accepted by timedelta
iso8601_duration_re = re.compile(
    r"^(?P<sign>[-+]?)"
    r"P"
    r"(?:(?P<days>\d+([\.,]\d+)?)D)?"
    r"(?:T"
    r"(?:(?P<hours>\d+([\.,]\d+)?)H)?"
    r"(?:(?P<minutes>\d+([\.,]\d+)?)M)?"
    r"(?:(?P<seconds>\d+([\.,]\d+)?)S)?"
    r")?"
    r"$"
)

# Support PostgreSQL's day-time interval format, e.g. "3 days 04:05:06". The
# year-month and mixed intervals cannot be converted to a timedelta and thus
# aren't accepted.
postgres_interval_re = re.compile(
    r"^"
    r"(?:(?P<days>-?\d+) (days? ?))?"
    r"(?:(?P<sign>[-+])?"
    r"(?P<hours>\d+):"
    r"(?P<minutes>\d\d):"
    r"(?P<seconds>\d\d)"
    r"(?:\.(?P<microseconds>\d{1,6}))?"
    r")?$"
)


def prettify_class_name(name: str) -> str:
    return re.sub(r"(?<=.)([A-Z])", r" \1", name)


def slugify_class_name(name: str) -> str:
    dashed = re.sub("(.)([A-Z][a-z]+)", r"\1-\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1-\2", dashed).lower()


def secure_filename(filename: str) -> str:
    """Ported from Werkzeug.

    Pass it a filename and it will return a secure version of it. This
    filename can then safely be stored on a regular file system and passed
    to :func:`os.path.join`. The filename returned is an ASCII only string
    for maximum portability.
    On windows systems the function also makes sure that the file is not
    named after one of the special device files.
    """
    filename = unicodedata.normalize("NFKD", filename)
    filename = filename.encode("ascii", "ignore").decode("ascii")

    for sep in os.path.sep, os.path.altsep:
        if sep:
            filename = filename.replace(sep, " ")
    filename = str(_filename_ascii_strip_re.sub("", "_".join(filename.split()))).strip(
        "._"
    )

    # on nt a couple of special files are present in each folder.  We
    # have to ensure that the target file is not such a filename.  In
    # this case we prepend an underline
    if (
        os.name == "nt"
        and filename
        and filename.split(".")[0].upper() in _windows_device_files
    ):
        filename = f"_{filename}"  # pragma: no cover

    return filename


class Writer(ABC):
    """https://docs.python.org/3/library/csv.html#writer-objects"""

    @abstractmethod
    def writerow(self, row: List[str]) -> None:
        pass  # pragma: no cover

    @abstractmethod
    def writerows(self, rows: List[List[str]]) -> None:
        pass  # pragma: no cover

    @property
    @abstractmethod
    def dialect(self) -> csv.Dialect:
        pass  # pragma: no cover


class _PseudoBuffer:
    """An object that implements just the write method of the file-like
    interface.
    """

    def write(self, value: T) -> T:
        return value


def stream_to_csv(
    callback: Callable[[Writer], Generator[T, None, None]]
) -> Generator[T, None, None]:
    """Function that takes a callable (that yields from a CSV Writer), and
    provides it a writer that streams the output directly instead of
    storing it in a buffer. The direct output stream is intended to go
    inside a `starlette.responses.StreamingResponse`.

    Loosely adapted from here:

    https://docs.djangoproject.com/en/1.8/howto/outputting-csv/
    """
    writer = csv.writer(_PseudoBuffer())
    return callback(writer)  # type: ignore


def get_primary_key(model: type) -> Column:
    pks = inspect(model).mapper.primary_key
    assert len(pks) == 1, "Multiple Primary Keys not supported."
    return pks[0]


def get_direction(prop: MODEL_PROPERTY) -> str:
    assert isinstance(prop, RelationshipProperty)
    name = prop.direction.name
    if name == "ONETOMANY" and not prop.uselist:
        return "ONETOONE"
    return name


def get_column_python_type(column: Column) -> type:
    try:
        if hasattr(column.type, "impl"):
            return column.type.impl.python_type
        return column.type.python_type
    except NotImplementedError:
        return str


def is_relationship(prop: MODEL_PROPERTY) -> bool:
    return isinstance(prop, RelationshipProperty)


def parse_interval(value: str) -> Optional[timedelta]:
    match = (
        standard_duration_re.match(value)
        or iso8601_duration_re.match(value)
        or postgres_interval_re.match(value)
    )

    if not match:
        return None

    kw: Dict[str, Any] = match.groupdict()
    sign = -1 if kw.pop("sign", "+") == "-" else 1
    if kw.get("microseconds"):
        kw["microseconds"] = kw["microseconds"].ljust(6, "0")
    kw = {k: float(v.replace(",", ".")) for k, v in kw.items() if v is not None}
    days = timedelta(kw.pop("days", 0.0) or 0.0)
    if match.re == iso8601_duration_re:
        days *= sign
    return days + sign * timedelta(**kw)


def map_attr_to_prop(
    attr: Union[str, InstrumentedAttribute], model_admin: "ModelView"
) -> MODEL_PROPERTY:
    if isinstance(attr, InstrumentedAttribute):
        attr = attr.prop.key

    try:
        return model_admin._props[attr]
    except KeyError:
        raise InvalidColumnError(
            f"Model '{model_admin.model.__name__}' has no attribute '{attr}'."
        )


def is_falsy_value(value: Any) -> bool:
    if value is None:
        return True
    elif not value and isinstance(value, str):
        return True
    else:
        return False
