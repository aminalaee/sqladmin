import re
from typing import Any, Callable, List, Optional, Tuple

from sqlalchemy import Integer
from sqlalchemy.sql.expression import Select, select
from starlette.requests import Request

from sqladmin._types import MODEL_ATTR


def get_parameter_name(column: MODEL_ATTR) -> str:
    if isinstance(column, str):
        return column
    else:
        return column.key


def prettify_attribute_name(name: str) -> str:
    return re.sub(r"_([A-Za-z])", r" \1", name).title()


def get_title(column: MODEL_ATTR) -> str:
    name = get_parameter_name(column)
    return prettify_attribute_name(name)


def get_column_obj(column: MODEL_ATTR, model: Any = None) -> Any:
    if isinstance(column, str):
        if model is None:
            raise ValueError("model is required for string column filters")
        return getattr(model, column)
    return column


def get_foreign_column_name(column_obj: Any) -> str:
    fk = next(iter(column_obj.foreign_keys))
    return fk.column.name


def get_model_from_column(column: Any) -> Any:
    return column.parent.class_


class BooleanFilter:
    def __init__(
        self,
        column: MODEL_ATTR,
        title: Optional[str] = None,
        parameter_name: Optional[str] = None,
    ):
        self.column = column
        self.title = title or get_title(column)
        self.parameter_name = parameter_name or get_parameter_name(column)

    async def lookups(
        self, request: Request, model: Any, run_query: Callable[[Select], Any]
    ) -> List[Tuple[str, str]]:
        return [
            ("all", "All"),
            ("true", "Yes"),
            ("false", "No"),
        ]

    async def get_filtered_query(self, query: Select, value: Any, model: Any) -> Select:
        column_obj = get_column_obj(self.column, model)
        if value == "true":
            return query.filter(column_obj.is_(True))
        elif value == "false":
            return query.filter(column_obj.is_(False))
        else:
            return query


class AllUniqueStringValuesFilter:
    def __init__(
        self,
        column: MODEL_ATTR,
        title: Optional[str] = None,
        parameter_name: Optional[str] = None,
    ):
        self.column = column
        self.title = title or get_title(column)
        self.parameter_name = parameter_name or get_parameter_name(column)

    async def lookups(
        self, request: Request, model: Any, run_query: Callable[[Select], Any]
    ) -> List[Tuple[str, str]]:
        column_obj = get_column_obj(self.column, model)

        return [("", "All")] + [
            (value[0], value[0])
            for value in await run_query(select(column_obj).distinct())
        ]

    async def get_filtered_query(self, query: Select, value: Any, model: Any) -> Select:
        if value == "":
            return query

        column_obj = get_column_obj(self.column, model)
        return query.filter(column_obj == value)


class StaticValuesFilter:
    def __init__(
        self,
        column: MODEL_ATTR,
        values: List[Tuple[str, str]],
        title: Optional[str] = None,
        parameter_name: Optional[str] = None,
    ):
        self.column = column
        self.title = title or get_title(column)
        self.parameter_name = parameter_name or get_parameter_name(column)
        self.values = values

    async def lookups(
        self, request: Request, model: Any, run_query: Callable[[Select], Any]
    ) -> List[Tuple[str, str]]:
        return [("", "All")] + self.values

    async def get_filtered_query(self, query: Select, value: Any, model: Any) -> Select:
        column_obj = get_column_obj(self.column, model)
        if value == "":
            return query
        return query.filter(column_obj == value)


class ForeignKeyFilter:
    def __init__(
        self,
        foreign_key: MODEL_ATTR,
        foreign_display_field: MODEL_ATTR,
        foreign_model: Any = None,
        title: Optional[str] = None,
        parameter_name: Optional[str] = None,
    ):
        self.foreign_key = foreign_key
        self.foreign_display_field = foreign_display_field
        self.foreign_model = foreign_model
        self.title = title or get_title(foreign_key)
        self.parameter_name = parameter_name or get_parameter_name(foreign_key)

    async def lookups(
        self, request: Request, model: Any, run_query: Callable[[Select], Any]
    ) -> List[Tuple[str, str]]:
        foreign_key_obj = get_column_obj(self.foreign_key, model)
        if self.foreign_model is None and isinstance(self.foreign_display_field, str):
            raise ValueError("foreign_model is required for string foreign key filters")
        if self.foreign_model is None:
            assert not isinstance(self.foreign_display_field, str)
            foreign_display_field_obj = self.foreign_display_field
        else:
            foreign_display_field_obj = get_column_obj(
                self.foreign_display_field, self.foreign_model
            )
        if not self.foreign_model:
            self.foreign_model = get_model_from_column(foreign_display_field_obj)
        foreign_model_key_name = get_foreign_column_name(foreign_key_obj)
        foreign_model_key_obj = getattr(self.foreign_model, foreign_model_key_name)

        return [("", "All")] + [
            (str(key), str(value))
            for key, value in await run_query(
                select(foreign_model_key_obj, foreign_display_field_obj).distinct()
            )
        ]

    async def get_filtered_query(self, query: Select, value: Any, model: Any) -> Select:
        foreign_key_obj = get_column_obj(self.foreign_key, model)
        column_type = foreign_key_obj.type
        if isinstance(column_type, Integer):
            value = int(value)

        return query.filter(foreign_key_obj == value)
