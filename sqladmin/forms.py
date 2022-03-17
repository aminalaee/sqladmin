import inspect
from enum import Enum
from typing import Any, Callable, Dict, Sequence, Type, Union, no_type_check

import anyio
from sqlalchemy import inspect as sqlalchemy_inspect, select
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import ColumnProperty, Mapper, RelationshipProperty, Session
from sqlalchemy.sql.schema import Column
from wtforms import (
    BooleanField,
    DateField,
    DateTimeField,
    DecimalField,
    Field,
    Form,
    IntegerField,
    SelectField,
    StringField,
    TextAreaField,
    validators,
)
from wtforms.fields.core import UnboundField

from sqladmin.fields import JSONField, QuerySelectField, QuerySelectMultipleField


@no_type_check
def converts(*args: str) -> Callable:
    def _inner(func: Callable) -> Callable:
        func._converter_for = frozenset(args)
        return func

    return _inner


class ModelConverterBase:
    _convert_for = None

    def __init__(self) -> None:
        converters = {}

        for name in dir(self):
            obj = getattr(self, name)
            if hasattr(obj, "_converter_for"):
                for classname in obj._converter_for:
                    converters[classname] = obj

        self.converters = converters

    def get_converter(self, column: Column) -> Callable:
        types = inspect.getmro(type(column.type))

        # Search by module + name
        for col_type in types:
            type_string = f"{col_type.__module__}.{col_type.__name__}"

            if type_string in self.converters:
                return self.converters[type_string]

        # Search by name
        for col_type in types:
            if col_type.__name__ in self.converters:
                return self.converters[col_type.__name__]

            # Support for custom types like SQLModel which inherit TypeDecorator
            if hasattr(col_type, "impl"):
                if col_type.impl.__name__ in self.converters:  # type: ignore
                    return self.converters[col_type.impl.__name__]  # type: ignore

        raise Exception(  # pragma: nocover
            f"Could not find field converter for column {column.name} ({types[0]!r})."
        )

    async def convert(
        self,
        model: type,
        mapper: Mapper,
        prop: Union[ColumnProperty, RelationshipProperty],
        engine: Union[Engine, AsyncEngine],
    ) -> UnboundField:
        kwargs: Dict = {
            "validators": [],
            "filters": [],
            "default": None,
            "description": prop.doc,
            "render_kw": {"class": "form-control"},
        }

        converter = None
        column = None

        if isinstance(prop, ColumnProperty):
            assert len(prop.columns) == 1, "Multiple-column properties not supported"
            column = prop.columns[0]

            if column.primary_key or column.foreign_keys:
                return

            default = getattr(column, "default", None)

            if default is not None:
                # Only actually change default if it has an attribute named
                # 'arg' that's callable.
                callable_default = getattr(default, "arg", None)

                if callable_default is not None:
                    # ColumnDefault(val).arg can be also a plain value
                    default = (
                        callable_default(None)
                        if callable(callable_default)
                        else callable_default
                    )

            kwargs["default"] = default

            if column.nullable:
                kwargs["validators"].append(validators.Optional())
            else:
                kwargs["validators"].append(validators.InputRequired())

            converter = self.get_converter(column)
        else:
            nullable = True
            for pair in prop.local_remote_pairs:
                if not pair[0].nullable:
                    nullable = False

            kwargs["allow_blank"] = nullable

            target_model = prop.mapper.class_
            pk = sqlalchemy_inspect(target_model).primary_key[0].name
            stmt = select(target_model)

            if isinstance(engine, Engine):
                with Session(engine) as session:
                    objects = await anyio.to_thread.run_sync(session.execute, stmt)
                    object_list = [
                        (str(self.get_pk(obj, pk)), obj)
                        for obj in objects.scalars().all()
                    ]
                    kwargs["object_list"] = object_list
            else:
                async with AsyncSession(engine) as session:
                    objects = await session.execute(stmt)
                    object_list = [
                        (str(self.get_pk(obj, pk)), obj)
                        for obj in objects.scalars().all()
                    ]
                    kwargs["object_list"] = object_list

            converter = self.converters[prop.direction.name]

        assert converter is not None

        return converter(
            model=model, mapper=mapper, prop=prop, column=column, field_args=kwargs
        )

    def get_pk(self, o: Any, pk_name: str) -> Any:
        return getattr(o, pk_name)


class ModelConverter(ModelConverterBase):
    @classmethod
    def _string_common(cls, column: Column, field_args: Dict, **kwargs: Any) -> None:
        if isinstance(column.type.length, int) and column.type.length:
            field_args["validators"].append(validators.Length(max=column.type.length))

    @converts("String")  # includes Unicode
    def conv_String(self, field_args: Dict, **kwargs: Any) -> Field:
        self._string_common(field_args=field_args, **kwargs)
        return StringField(**field_args)

    @converts("Text", "LargeBinary", "Binary")  # includes UnicodeText
    def conv_Text(self, field_args: Dict, **kwargs: Any) -> Field:
        self._string_common(field_args=field_args, **kwargs)
        return TextAreaField(**field_args)

    @converts("Boolean", "dialects.mssql.base.BIT")
    def conv_Boolean(self, field_args: Dict, **kwargs: Any) -> Field:
        field_args["render_kw"]["class"] = "form-check-input"
        return BooleanField(**field_args)

    @converts("Date")
    def conv_Date(self, field_args: Dict, **kwargs: Any) -> Field:
        return DateField(**field_args)

    @converts("DateTime")
    def conv_DateTime(self, field_args: Dict, **kwargs: Any) -> Field:
        return DateTimeField(**field_args)

    @converts("Enum")
    def conv_Enum(self, column: Column, field_args: Dict, **kwargs: Any) -> Field:
        available_choices = [(e, e) for e in column.type.enums]
        accepted_values = [choice[0] for choice in available_choices]

        field_args["choices"] = available_choices
        field_args["validators"].append(validators.AnyOf(accepted_values))
        field_args["coerce"] = lambda v: v.name if isinstance(v, Enum) else str(v)
        return SelectField(**field_args)

    @converts("Integer")  # includes BigInteger and SmallInteger
    def handle_integer_types(
        self, column: Column, field_args: Dict, **kwargs: Any
    ) -> Field:
        return IntegerField(**field_args)

    @converts("Numeric")  # includes DECIMAL, Float/FLOAT, REAL, and DOUBLE
    def handle_decimal_types(
        self, column: Column, field_args: Dict, **kwargs: Any
    ) -> Field:
        # override default decimal places limit, use database defaults instead
        field_args.setdefault("places", None)
        return DecimalField(**field_args)

    # @converts("dialects.mysql.types.YEAR", "dialects.mysql.base.YEAR")
    # def conv_MSYear(self, field_args: Dict, **kwargs: Any) -> Field:
    #     field_args["validators"].append(validators.NumberRange(min=1901, max=2155))
    #     return StringField(**field_args)

    @converts("sqlalchemy.dialects.postgresql.base.INET")
    def conv_PGInet(self, field_args: Dict, **kwargs: Any) -> Field:
        field_args.setdefault("label", "IP Address")
        field_args["validators"].append(validators.IPAddress())
        return StringField(**field_args)

    @converts("sqlalchemy.dialects.postgresql.base.MACADDR")
    def conv_PGMacaddr(self, field_args: Dict, **kwargs: Any) -> Field:
        field_args.setdefault("label", "MAC Address")
        field_args["validators"].append(validators.MacAddress())
        return StringField(**field_args)

    @converts("sqlalchemy.dialects.postgresql.base.UUID")
    def conv_PgUuid(self, field_args: Dict, **kwargs: Any) -> Field:
        field_args.setdefault("label", "UUID")
        field_args["validators"].append(validators.UUID())
        return StringField(**field_args)

    @converts("JSON")
    def convert_JSON(self, field_args: dict, **extra: Any) -> Field:
        return JSONField(**field_args)

    @converts("MANYTOONE")
    def conv_ManyToOne(self, field_args: Dict, **kwargs: Any) -> Field:
        return QuerySelectField(**field_args)

    @converts("MANYTOMANY", "ONETOMANY")
    def conv_ManyToMany(self, field_args: Dict, **kwargs: Any) -> Field:
        return QuerySelectMultipleField(**field_args)


async def get_model_form(
    model: type,
    engine: Union[Engine, AsyncEngine],
    only: Sequence[str] = None,
    exclude: Sequence[str] = None,
) -> Type[Form]:
    type_name = model.__name__ + "Form"
    converter = ModelConverter()
    mapper = sqlalchemy_inspect(model)

    attributes = []
    for name, attr in mapper.attrs.items():
        if only and name not in only:
            continue
        elif exclude and name in exclude:
            continue

        attributes.append((name, attr))

    field_dict = {}
    for name, attr in attributes:
        field = await converter.convert(model, mapper, attr, engine)
        if field is not None:
            field_dict[name] = field

    return type(type_name, (Form,), field_dict)
