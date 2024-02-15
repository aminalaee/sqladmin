from typing import Any, Dict

from sqlalchemy import Column, Select


class BaseFilter:
    def __init__(
        self, column: Column, name: str, options: Dict[str, Any], data_type: type
    ):
        self.column = column
        self.name = name
        self.options = options
        self.data_type = data_type

    def apply(self, query: Select, value: Any):
        raise NotImplementedError

    @property
    def operation(self):
        raise NotImplementedError()


class FilterEqual(BaseFilter):
    @property
    def operation(self):
        return "equals"

    def apply(self, query: Select, value: Any):
        return query.filter(self.column == value)


class FilterNotEqual(BaseFilter):
    @property
    def operation(self):
        return "not equal"

    def apply(self, query: Select, value: Any):
        return query.filter(self.column != value)


class FilterConverter:
    strings = (FilterEqual, FilterNotEqual)

    def __init__(self) -> None:
        self.converters = {}
        for name in dir(self):
            attr = getattr(self, name)
            if hasattr(attr, "_converter_for"):
                for p in attr._converter_for:
                    self.converters[p] = attr

    def convert(self, type_name: str, column: Column, name: str, **kwargs: Any):
        filter_name = type_name.lower()

        if filter_name in self.converters:
            return self.converters[filter_name](column, name, **kwargs)

        return None

    @convert(
        "string",
        "char",
        "unicode",
        "varchar",
        "tinytext",
        "text",
        "mediumtext",
        "longtext",
        "unicodetext",
        "nchar",
        "nvarchar",
        "ntext",
        "citext",
        "emailtype",
        "URLType",
        "IPAddressType",
    )
    def conv_string(self, column, name, **kwargs):
        return [f(column, name, **kwargs) for f in self.strings]
