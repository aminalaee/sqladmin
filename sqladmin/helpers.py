import csv
import os
import re
import unicodedata
from abc import ABC, abstractmethod
from typing import Any, Callable, Generator, List, TypeVar, Union

from sqlalchemy import Column, inspect
from sqlalchemy.orm import RelationshipProperty

from sqladmin._types import MODEL_ATTR_TYPE

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


def get_relationships(model: Any) -> List[MODEL_ATTR_TYPE]:
    return list(inspect(model).relationships)


def get_attributes(model: Any) -> List[MODEL_ATTR_TYPE]:
    return list(inspect(model).attrs)


def get_direction(attr: MODEL_ATTR_TYPE) -> str:
    assert isinstance(attr, RelationshipProperty)
    name = attr.direction.name
    if name == "ONETOMANY" and not attr.uselist:
        return "ONETOONE"
    return name


def get_column_python_type(column: Column) -> type:
    try:
        return column.type.python_type
    except NotImplementedError:
        return str


def is_relationship(attr: MODEL_ATTR_TYPE) -> bool:
    return isinstance(attr, RelationshipProperty)
