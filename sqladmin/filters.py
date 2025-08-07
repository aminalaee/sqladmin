import re
from typing import Any, Callable, List, Optional, Tuple

from sqlalchemy import (
    BigInteger,
    Float,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.sql.expression import Select, select
from sqlalchemy.sql.sqltypes import _Binary
from starlette.requests import Request

from sqladmin._types import MODEL_ATTR

# Try to import UUID type for SQLAlchemy 2.0+
try:
    import uuid

    from sqlalchemy import Uuid

    HAS_UUID_SUPPORT = True
except ImportError:
    # Fallback for SQLAlchemy < 2.0
    HAS_UUID_SUPPORT = False
    Uuid = None


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
    has_operator = False

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
    has_operator = False

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
    has_operator = False

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
    has_operator = False

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


class ColumnFilter:
    """Universal filter that provides appropriate filter types based on column type"""

    has_operator = True

    def __init__(
        self,
        column: MODEL_ATTR,
        title: Optional[str] = None,
        parameter_name: Optional[str] = None,
    ):
        self.column = column
        self.title = title or get_title(column)
        self.parameter_name = parameter_name or get_parameter_name(column)

    def get_operation_options(self, column_obj: Any) -> List[Tuple[str, str]]:
        """Return operation options based on column type"""
        if self._is_string_type(column_obj):
            return [
                ("contains", "Contains"),
                ("equals", "Equals"),
                ("starts_with", "Starts with"),
                ("ends_with", "Ends with"),
            ]
        elif self._is_numeric_type(column_obj):
            return [
                ("equals", "Equals"),
                ("greater_than", "Greater than"),
                ("less_than", "Less than"),
            ]
        elif self._is_uuid_type(column_obj):
            return [
                ("equals", "Equals"),
                ("contains", "Contains"),
                ("starts_with", "Starts with"),
            ]
        else:
            return [
                ("equals", "Equals"),
            ]

    def get_operation_options_for_model(self, model: Any) -> List[Tuple[str, str]]:
        """Return operation options based on column type for given model"""
        column_obj = get_column_obj(self.column, model)
        return self.get_operation_options(column_obj)

    def _is_string_type(self, column_obj: Any) -> bool:
        return isinstance(column_obj.type, (String, Text, _Binary))

    def _is_numeric_type(self, column_obj: Any) -> bool:
        return isinstance(
            column_obj.type, (Integer, Numeric, Float, BigInteger, SmallInteger)
        )

    def _is_uuid_type(self, column_obj: Any) -> bool:
        # Check if UUID support is available and column is UUID type
        return HAS_UUID_SUPPORT and isinstance(column_obj.type, Uuid)

    def _convert_value_for_column(
        self, value: str, column_obj: Any, operation: str = "equals"
    ) -> Any:
        if not value:
            return None

        column_type = column_obj.type

        try:
            if isinstance(column_type, (String, Text, _Binary)):
                return str(value)

            if isinstance(column_type, (Integer, BigInteger, SmallInteger)):
                return int(value)

            if isinstance(column_type, (Numeric, Float)):
                return float(value)

            # UUID support for SQLAlchemy 2.0+
            if HAS_UUID_SUPPORT and isinstance(column_type, Uuid):
                # For contains/starts_with operations, keep as string for LIKE queries
                if operation in ("contains", "starts_with"):
                    return str(value.strip())
                # For equals operation, validate and convert to UUID
                return uuid.UUID(value.strip())

        except (ValueError, TypeError):
            return None

        return str(value)

    async def lookups(
        self, request: Request, model: Any, run_query: Callable[[Select], Any]
    ) -> List[Tuple[str, str]]:
        # This method is not used for has_operator=True filters
        # The UI uses get_operation_options_for_model instead
        return []

    async def get_filtered_query(
        self, query: Select, operation: str, value: Any, model: Any
    ) -> Select:
        """Handle filtering with separate operation and value parameters"""
        if not value or value == "" or not operation:
            return query

        column_obj = get_column_obj(self.column, model)
        converted_value = self._convert_value_for_column(
            str(value).strip(), column_obj, operation
        )

        if converted_value is None:
            return query

        if operation == "contains":
            if self._is_uuid_type(column_obj):
                # For UUID, cast to text for LIKE operations
                search_value = f"%{str(value).strip()}%"
                return query.filter(column_obj.cast(String).ilike(search_value))
            else:
                return query.filter(column_obj.ilike(f"%{str(value).strip()}%"))
        elif operation == "equals":
            return query.filter(column_obj == converted_value)
        elif operation == "starts_with":
            if self._is_uuid_type(column_obj):
                # For UUID, cast to text for LIKE operations
                search_value = f"{str(value).strip()}%"
                return query.filter(column_obj.cast(String).ilike(search_value))
            else:
                return query.filter(column_obj.startswith(str(value).strip()))
        elif operation == "ends_with":
            return query.filter(column_obj.endswith(str(value).strip()))
        elif operation == "greater_than":
            return query.filter(column_obj > converted_value)
        elif operation == "less_than":
            return query.filter(column_obj < converted_value)

        return query


class StringFilter:
    """Filter specifically designed for string columns with text-based operations"""

    has_operator = True

    def __init__(
        self,
        column: MODEL_ATTR,
        title: Optional[str] = None,
        parameter_name: Optional[str] = None,
    ):
        self.column = column
        self.title = title or f"{get_title(column)} (String)"
        self.parameter_name = parameter_name or get_parameter_name(column)

    def get_operation_options(self) -> List[Tuple[str, str]]:
        """Return available operations for this filter"""
        return [
            ("contains", "Contains"),
            ("equals", "Equals"),
            ("starts", "Starts with"),
            ("ends", "Ends with"),
        ]

    def get_operation_options_for_model(self, model: Any) -> List[Tuple[str, str]]:
        """Return operation options for string filters"""
        return self.get_operation_options()

    async def lookups(
        self, request: Request, model: Any, run_query: Callable[[Select], Any]
    ) -> List[Tuple[str, str]]:
        # This method is not used for has_operator=True filters
        return []

    async def get_filtered_query(
        self, query: Select, operation: str, value: Any, model: Any
    ) -> Select:
        """Handle filtering with separate operation and value parameters"""
        if not value or value == "" or not operation:
            return query

        column_obj = get_column_obj(self.column, model)
        filter_text = str(value).strip()

        if operation == "contains":
            return query.filter(column_obj.contains(filter_text))
        elif operation == "equals":
            return query.filter(column_obj == filter_text)
        elif operation == "starts":
            return query.filter(column_obj.startswith(filter_text))
        elif operation == "ends":
            return query.filter(column_obj.endswith(filter_text))

        return query


class NumericFilter:
    """Filter specifically designed for numeric columns with mathematical operations"""

    has_operator = True

    def __init__(
        self,
        column: MODEL_ATTR,
        title: Optional[str] = None,
        parameter_name: Optional[str] = None,
    ):
        self.column = column
        self.title = title or f"{get_title(column)} (Numeric)"
        self.parameter_name = parameter_name or get_parameter_name(column)

    def get_operation_options(self) -> List[Tuple[str, str]]:
        """Return available operations for this filter"""
        return [
            ("equals", "Equals"),
            ("gt", "Greater than"),
            ("gte", "Greater than or equal"),
            ("lt", "Less than"),
            ("lte", "Less than or equal"),
        ]

    def get_operation_options_for_model(self, model: Any) -> List[Tuple[str, str]]:
        """Return operation options for numeric filters"""
        return self.get_operation_options()

    def _convert_to_numeric(self, value: str, column_obj: Any) -> Any:
        if not value:
            return None

        column_type = column_obj.type

        try:
            if isinstance(column_type, (Integer, BigInteger, SmallInteger)):
                return int(value)

            if isinstance(column_type, (Numeric, Float)):
                return float(value)

        except (ValueError, TypeError):
            return None

        return None

    async def lookups(
        self, request: Request, model: Any, run_query: Callable[[Select], Any]
    ) -> List[Tuple[str, str]]:
        # This method is not used for has_operator=True filters
        return []

    async def get_filtered_query(
        self, query: Select, operation: str, value: Any, model: Any
    ) -> Select:
        """Handle filtering with separate operation and value parameters"""
        if not value or value == "" or not operation:
            return query

        column_obj = get_column_obj(self.column, model)
        converted_value = self._convert_to_numeric(str(value).strip(), column_obj)

        if converted_value is None:
            return query

        if operation == "equals":
            return query.filter(column_obj == converted_value)
        elif operation == "gt":
            return query.filter(column_obj > converted_value)
        elif operation == "gte":
            return query.filter(column_obj >= converted_value)
        elif operation == "lt":
            return query.filter(column_obj < converted_value)
        elif operation == "lte":
            return query.filter(column_obj <= converted_value)

        return query
