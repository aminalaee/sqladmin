import inspect
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Sequence, Type, TypeVar, Union

import anyio
from sqlalchemy import inspect as sqlalchemy_inspect, select
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import (
    ColumnProperty,
    InstrumentedAttribute,
    MapperProperty,
    RelationshipProperty,
    Session,
)
from sqlalchemy.sql.schema import Column
from typing_extensions import Protocol
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

from sqladmin.exceptions import NoConverterFound
from sqladmin.fields import JSONField, QuerySelectField, QuerySelectMultipleField

T_MP = TypeVar("T_MP", ColumnProperty, RelationshipProperty)


class Validator(Protocol):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        ...

    def __call__(self, form: Form, field: Field) -> None:
        ...


class ConverterCallback(Protocol):
    def __call__(self, model: type, prop: T_MP, kwargs: Dict[str, Any]) -> UnboundField:
        ...


T_CC = TypeVar("T_CC", bound=ConverterCallback)


class AdminAttribute:
    def __init__(
        self,
        model: type,
        attribute: Union[str, InstrumentedAttribute],
        *,
        label: Optional[str] = None,
        field_type_override: Type[Field] = None,
        extra_field_kwargs: Dict[str, Any] = None,
        extra_validators: List[Callable[[Form, Field], None]] = None,
    ):
        self.model = model

        if isinstance(attribute, str):
            self.attribute = getattr(model, attribute)
        else:
            self.attribute = attribute  # pragma: no cover
        assert isinstance(self.attribute, InstrumentedAttribute)
        assert self.attribute.class_ is model

        self.label = label

        self.extra_field_kwargs = extra_field_kwargs or {}
        self.field_type_override = field_type_override
        self.extra_validators = extra_validators or []

    def skip(self) -> bool:
        if self.is_relationship:
            return False
        else:
            return bool(self.sqla_column.primary_key or self.sqla_column.foreign_keys)

    @property
    def is_relationship(self) -> bool:
        return isinstance(self.attribute.prop, RelationshipProperty)

    @property
    def sqla_property(self) -> MapperProperty:
        return self.attribute.prop

    @property
    def sqla_column(self) -> Column:
        assert isinstance(
            self.sqla_property, ColumnProperty
        ), "Relationship properties don't have a column attr"
        assert (
            len(self.sqla_property.columns) == 1
        ), "Multiple-column properties not supported"
        column = self.sqla_property.columns[0]
        return column

    def _get_default_value(self) -> Any:
        if self.is_relationship:
            return None

        default = getattr(self.sqla_column, "default", None)

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

        return default

    @property
    def wtf_base_validators(self) -> List[Validator]:
        if self.is_relationship:
            return []
        li = []
        if self.sqla_column.nullable:
            li.append(validators.Optional())
        else:
            li.append(validators.InputRequired())
        return li

    @property
    def _wtf_default_field_kwargs(self) -> Dict[str, Any]:
        kwargs = {
            "label": self.label,
            "validators": [*self.wtf_base_validators, *self.extra_validators],
            "description": self.sqla_property.doc,
            "render_kw": {"class": "form-control"},
            "default": self._get_default_value(),
        }
        if self.is_relationship:
            allow_blank = True
            for pair in self.sqla_property.local_remote_pairs:
                if not pair[0].nullable:
                    allow_blank = False
            kwargs["allow_blank"] = allow_blank
        return kwargs

    async def get_object_list(self, engine: Union[Engine, AsyncEngine]) -> List[Any]:
        target_model = self.sqla_property.mapper.class_
        pk = sqlalchemy_inspect(target_model).primary_key[0].name
        stmt = select(target_model)

        if isinstance(engine, Engine):
            with Session(engine) as session:
                objects = await anyio.to_thread.run_sync(session.execute, stmt)
                object_list = [
                    (str(getattr(obj, pk)), obj) for obj in objects.scalars().all()
                ]
        else:
            async with AsyncSession(engine) as session:
                objects = await session.execute(stmt)
                object_list = [
                    (str(getattr(obj, pk)), obj) for obj in objects.scalars().all()
                ]
        return object_list

    @property
    def field_kwargs(self) -> Dict[str, Any]:
        d = {
            **self._wtf_default_field_kwargs,
            **self.extra_field_kwargs,
        }
        return d


class ModelConverterBase:

    _callbacks: Dict[str, ConverterCallback] = {}

    def __init__(self):
        super().__init__()
        self._register_callbacks()

    def _register_callbacks(self):
        converters: Dict[str, ConverterCallback] = {}
        for name in dir(self):
            obj = getattr(self, name)
            if hasattr(obj, "_converter_for"):
                for classname in obj._converter_for:
                    converters[classname] = obj
        self._callbacks = converters

    def get_callback(
        self, model: type, prop: T_MP, kwargs: Dict[str, Any]
    ) -> ConverterCallback:
        if isinstance(prop, RelationshipProperty):
            return self._callbacks[prop.direction.name]

        column = prop.columns[0]
        types = inspect.getmro(type(column.type))

        # Search by module + name
        for col_type in types:
            type_string = f"{col_type.__module__}.{col_type.__name__}"

            if type_string in self._callbacks:
                return self._callbacks[type_string]

        # Search by name
        for col_type in types:
            if col_type.__name__ in self._callbacks:
                return self._callbacks[col_type.__name__]

            # Support for custom types like SQLModel which inherit TypeDecorator
            if hasattr(col_type, "impl"):
                if col_type.impl.__name__ in self._callbacks:  # type: ignore
                    return self._callbacks[col_type.impl.__name__]  # type: ignore

        raise NoConverterFound(  # pragma: nocover
            f"Could not find field converter for column {column.name} ({types[0]!r})."
        )

    def convert(self, model: type, prop: T_MP, kwargs: Dict[str, Any]) -> UnboundField:
        callback = self.get_callback(model=model, prop=prop, kwargs=kwargs)
        return callback(model=model, prop=prop, kwargs=kwargs)


def converts(*args: str) -> Callable[[T_CC], T_CC]:
    def _inner(func: T_CC) -> T_CC:
        func._converter_for = frozenset(args)
        return func

    return _inner


class ModelConverter(ModelConverterBase):
    @staticmethod
    def _string_common(prop: ColumnProperty) -> List[Validator]:
        li = []
        column = prop.columns[0]
        if isinstance(column.type.length, int) and column.type.length:
            li.append(validators.Length(max=column.type.length))
        return li

    @converts("String")  # includes Unicode
    def conv_String(
        self, model: type, prop: ColumnProperty, kwargs: Dict[str, Any]
    ) -> UnboundField:
        kwargs.setdefault("validators", [])
        extra_validators = self._string_common(prop)
        kwargs["validators"].extend(extra_validators)
        return StringField(**kwargs)

    @converts("Text", "LargeBinary", "Binary")  # includes UnicodeText
    def conv_Text(
        self, model: type, prop: ColumnProperty, kwargs: Dict[str, Any]
    ) -> UnboundField:
        kwargs.setdefault("validators", [])
        extra_validators = self._string_common(prop)
        kwargs["validators"].extend(extra_validators)
        return TextAreaField(**kwargs)

    @converts("Boolean", "dialects.mssql.base.BIT")
    def conv_Boolean(
        self, model: type, prop: ColumnProperty, kwargs: Dict[str, Any]
    ) -> UnboundField:
        kwargs.setdefault("render_kw", {})
        kwargs["render_kw"]["class"] = "form-check-input"
        return BooleanField(**kwargs)

    @converts("Date")
    def conv_Date(
        self, model: type, prop: ColumnProperty, kwargs: Dict[str, Any]
    ) -> UnboundField:
        return DateField(**kwargs)

    @converts("DateTime")
    def conv_DateTime(
        self, model: type, prop: ColumnProperty, kwargs: Dict[str, Any]
    ) -> UnboundField:
        return DateTimeField(**kwargs)

    @converts("Enum")
    def conv_Enum(
        self, model: type, prop: ColumnProperty, kwargs: Dict[str, Any]
    ) -> UnboundField:
        available_choices = [(e, e) for e in prop.columns[0].type.enums]
        accepted_values = [choice[0] for choice in available_choices]

        kwargs["choices"] = available_choices
        kwargs.setdefault("validators", [])
        kwargs["validators"].append(validators.AnyOf(accepted_values))
        kwargs["coerce"] = lambda v: v.name if isinstance(v, Enum) else str(v)
        return SelectField(**kwargs)

    @converts("Integer")  # includes BigInteger and SmallInteger
    def handle_integer_types(
        self, model: type, prop: ColumnProperty, kwargs: Dict[str, Any]
    ) -> UnboundField:
        return IntegerField(**kwargs)

    @converts("Numeric")  # includes DECIMAL, Float/FLOAT, REAL, and DOUBLE
    def handle_decimal_types(
        self, model: type, prop: ColumnProperty, kwargs: Dict[str, Any]
    ) -> UnboundField:
        # override default decimal places limit, use database defaults instead
        kwargs.setdefault("places", None)
        return DecimalField(**kwargs)

    # @converts("dialects.mysql.types.YEAR", "dialects.mysql.base.YEAR")
    # def conv_MSYear(
    #         self, model: type, prop: ColumnProperty, kwargs: Dict[str, Any]
    # ) -> UnboundField:
    #     kwargs.setdefault("validators", [])
    #     kwargs["validators"].append(validators.NumberRange(min=1901, max=2155))
    #     return StringField(**kwargs)

    @converts("sqlalchemy.dialects.postgresql.base.INET")
    def conv_PGInet(
        self, model: type, prop: ColumnProperty, kwargs: Dict[str, Any]
    ) -> UnboundField:
        kwargs.setdefault("label", "IP Address")
        kwargs.setdefault("validators", [])
        kwargs["validators"].append(validators.IPAddress())
        return StringField(**kwargs)

    @converts("sqlalchemy.dialects.postgresql.base.MACADDR")
    def conv_PGMacaddr(
        self, model: type, prop: ColumnProperty, kwargs: Dict[str, Any]
    ) -> UnboundField:
        kwargs.setdefault("label", "MAC Address")
        kwargs.setdefault("validators", [])
        kwargs["validators"].append(validators.MacAddress())
        return StringField(**kwargs)

    @converts("sqlalchemy.dialects.postgresql.base.UUID")
    def conv_PgUuid(
        self, model: type, prop: ColumnProperty, kwargs: Dict[str, Any]
    ) -> UnboundField:
        kwargs.setdefault("label", "UUID")
        kwargs.setdefault("validators", [])
        kwargs["validators"].append(validators.UUID())
        return StringField(**kwargs)

    @converts("JSON")
    def convert_JSON(
        self, model: type, prop: ColumnProperty, kwargs: Dict[str, Any]
    ) -> UnboundField:
        return JSONField(**kwargs)

    @converts("MANYTOONE")
    def conv_ManyToOne(
        self, model: type, prop: RelationshipProperty, kwargs: Dict[str, Any]
    ) -> UnboundField:
        return QuerySelectField(**kwargs)

    @converts("MANYTOMANY", "ONETOMANY")
    def conv_ManyToMany(
        self, model: type, prop: RelationshipProperty, kwargs: Dict[str, Any]
    ) -> UnboundField:
        return QuerySelectMultipleField(**kwargs)


async def get_model_form(
    model: type,
    engine: Union[Engine, AsyncEngine],
    only: Sequence[str] = None,
    exclude: Sequence[str] = None,
    column_labels: Dict[str, str] = None,
    form_args: Dict[str, Dict[str, Any]] = None,
    form_class: Type[Form] = Form,
    form_overrides: Dict[str, Dict[str, Type[Field]]] = None,
    converter_class: Type[ModelConverterBase] = ModelConverter,
) -> Type[Form]:
    type_name = model.__name__ + "Form"
    converter = converter_class()
    mapper = sqlalchemy_inspect(model)
    form_args = form_args or {}
    column_labels = column_labels or {}
    form_overrides = form_overrides or {}

    admin_attrs = []

    for name, prop in mapper.attrs.items():
        if only and name not in only:
            continue
        elif exclude and name in exclude:
            continue

        attr = AdminAttribute(
            model=model,
            attribute=name,
            label=column_labels.get(name),
            field_type_override=form_overrides.get(name),
            extra_field_kwargs=form_args.get(name),
        )

        if attr.skip():
            continue

        admin_attrs.append(attr)

    field_dict: Dict[str, UnboundField] = {}

    for attr in admin_attrs:
        kwargs = attr.field_kwargs

        if attr.is_relationship:
            kwargs["object_list"] = await attr.get_object_list(engine=engine)

        if attr.field_type_override is not None:
            field = attr.field_type_override(**kwargs)

        else:
            field = converter.convert(
                model=attr.model, prop=attr.sqla_property, kwargs=kwargs
            )

        if field is not None:
            field_dict[attr.sqla_property.key] = field

    return type(type_name, (form_class,), field_dict)
