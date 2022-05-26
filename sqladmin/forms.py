import inspect
from enum import Enum
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Sequence,
    Type,
    TypeVar,
    Union,
    no_type_check,
)

import anyio
from sqlalchemy import inspect as sqlalchemy_inspect, select
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import ColumnProperty, Mapper, RelationshipProperty, Session
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


class Validator(Protocol):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        ...  # pragma: no cover

    def __call__(self, form: Form, field: Field) -> None:
        ...  # pragma: no cover


class ConverterCallable(Protocol):
    def __call__(
        self,
        model: type,
        prop: Union[ColumnProperty, RelationshipProperty],
        kwargs: Dict[str, Any],
    ) -> UnboundField:
        ...  # pragma: no cover


T_CC = TypeVar("T_CC", bound=ConverterCallable)


@no_type_check
def converts(*args: str) -> Callable[[T_CC], T_CC]:
    def _inner(func: T_CC) -> T_CC:
        func._converter_for = frozenset(args)
        return func

    return _inner


class ModelConverterBase:
    _converters: Dict[str, ConverterCallable] = {}

    def __init__(self) -> None:
        super().__init__()
        self._register_converters()

    def _register_converters(self):
        converters = {}

        for name in dir(self):
            obj = getattr(self, name)
            if hasattr(obj, "_converter_for"):
                for classname in obj._converter_for:
                    converters[classname] = obj

        self._converters = converters

    def get_converter(
        self, model: type, prop: Union[ColumnProperty, RelationshipProperty]
    ) -> ConverterCallable:
        if not isinstance(prop, ColumnProperty):
            return self._converters[prop.direction.name]

        column = prop.columns[0]
        types = inspect.getmro(type(column.type))

        # Search by module + name
        for col_type in types:
            type_string = f"{col_type.__module__}.{col_type.__name__}"

            if type_string in self._converters:
                return self._converters[type_string]

        # Search by name
        for col_type in types:
            if col_type.__name__ in self._converters:
                return self._converters[col_type.__name__]

            # Support for custom types like SQLModel which inherit TypeDecorator
            if hasattr(col_type, "impl"):
                if col_type.impl.__name__ in self._converters:  # type: ignore
                    return self._converters[col_type.impl.__name__]  # type: ignore

        raise NoConverterFound(  # pragma: nocover
            f"Could not find field converter for column {column.name} ({types[0]!r})."
        )

    async def _prepare_kwargs(
        self,
        model: type,
        mapper: Mapper,
        prop: Union[ColumnProperty, RelationshipProperty],
        engine: Union[Engine, AsyncEngine],
        field_args: Dict[str, Any] = None,
        label: Optional[str] = None,
        override: Optional[Type[Field]] = None,
    ) -> Optional[Dict[str, Any]]:
        if field_args:
            kwargs = field_args.copy()
        else:
            kwargs = {}

        kwargs: Dict[str, Any]
        kwargs.setdefault("label", label)
        kwargs.setdefault("validators", [])
        kwargs.setdefault("filters", [])
        kwargs.setdefault("default", None)
        kwargs.setdefault("description", prop.doc)
        kwargs.setdefault("render_kw", {"class": "form-control"})

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

        return kwargs

    async def convert(
        self,
        model: type,
        mapper: Mapper,
        prop: Union[ColumnProperty, RelationshipProperty],
        engine: Union[Engine, AsyncEngine],
        field_args: Dict[str, Any] = None,
        label: Optional[str] = None,
        override: Optional[Type[Field]] = None,
    ) -> Optional[UnboundField]:

        kwargs = await self._prepare_kwargs(
            model=model,
            mapper=mapper,
            prop=prop,
            engine=engine,
            field_args=field_args,
            label=label,
            override=override,
        )

        if kwargs is None:
            return None

        if override is not None:
            assert issubclass(override, Field)
            return override(**kwargs)

        converter = self.get_converter(model=model, prop=prop)
        return converter(model=model, prop=prop, kwargs=kwargs)

    def get_pk(self, o: Any, pk_name: str) -> Any:
        return getattr(o, pk_name)


class ModelConverter(ModelConverterBase):
    @staticmethod
    def _string_common(prop: ColumnProperty) -> List[Validator]:
        li = []
        column: Column = prop.columns[0]
        if isinstance(column.type.length, int) and column.type.length:
            li.append(validators.Length(max=column.type.length))
        return li

    @converts("String", "CHAR")  # includes Unicode
    def conv_String(
        self, model: type, prop: ColumnProperty, kwargs: Dict[str, Any]
    ) -> UnboundField:
        extra_validators = self._string_common(prop)
        kwargs.setdefault("validators", [])
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
    # def conv_MSYear(self, field_args: Dict, **kwargs: Any) -> Field:
    #     field_args["validators"].append(validators.NumberRange(min=1901, max=2155))
    #     return StringField(**field_args)

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

    @converts("sqlalchemy_utils.types.email.EmailType")
    def conv_UtilsEmail(
        self, model: type, prop: ColumnProperty, kwargs: Dict[str, Any]
    ) -> UnboundField:
        kwargs.setdefault("label", "Email")
        kwargs.setdefault("validators", [])
        kwargs["validators"].append(validators.Email())
        return StringField(**kwargs)

    @converts(
        "sqlalchemy_utils.types.ip_address.IPAddressType",
    )
    def conv_UtilsIP(
        self, model: type, prop: ColumnProperty, kwargs: Dict[str, Any]
    ) -> UnboundField:
        kwargs.setdefault("label", "IPAddress")
        kwargs.setdefault("validators", [])
        kwargs["validators"].append(validators.IPAddress(ipv4=True, ipv6=True))
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
) -> Type[Form]:
    type_name = model.__name__ + "Form"
    converter = ModelConverter()
    mapper = sqlalchemy_inspect(model)
    form_args = form_args or {}
    column_labels = column_labels or {}
    form_overrides = form_overrides or {}

    attributes = []
    for name, attr in mapper.attrs.items():
        if only and name not in only:
            continue
        elif exclude and name in exclude:
            continue

        attributes.append((name, attr))

    field_dict = {}
    for name, attr in attributes:
        field_args = form_args.get(name, {})
        label = column_labels.get(name, None)
        override = form_overrides.get(name, None)
        field = await converter.convert(
            model, mapper, attr, engine, field_args, label, override
        )
        if field is not None:
            field_dict[name] = field

    return type(type_name, (form_class,), field_dict)
