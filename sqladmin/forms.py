import inspect
import sys
from enum import Enum
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    Union,
    no_type_check,
)

import anyio
from sqlalchemy import Boolean, inspect as sqlalchemy_inspect, select
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import ColumnProperty, RelationshipProperty, Session
from sqlalchemy.sql.schema import Column
from wtforms import (
    BooleanField,
    DecimalField,
    Field,
    Form,
    IntegerField,
    StringField,
    TextAreaField,
    validators,
)
from wtforms.fields.core import UnboundField

from sqladmin._types import ENGINE_TYPE, MODEL_ATTR_TYPE
from sqladmin._validators import CurrencyValidator, TimezoneValidator
from sqladmin.ajax import QueryAjaxModelLoader
from sqladmin.exceptions import NoConverterFound
from sqladmin.fields import (
    AjaxSelectField,
    AjaxSelectMultipleField,
    DateField,
    DateTimeField,
    JSONField,
    QuerySelectField,
    QuerySelectMultipleField,
    SelectField,
    TimeField,
)
from sqladmin.helpers import get_direction, get_primary_key, is_relationship

if sys.version_info >= (3, 8):
    from typing import Protocol
else:
    from typing_extensions import Protocol


class Validator(Protocol):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        ...  # pragma: no cover

    def __call__(self, form: Form, field: Field) -> None:
        ...  # pragma: no cover


class ConverterCallable(Protocol):
    def __call__(
        self,
        model: type,
        prop: MODEL_ATTR_TYPE,
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

    def _register_converters(self) -> None:
        converters = {}

        for name in dir(self):
            obj = getattr(self, name)
            if hasattr(obj, "_converter_for"):
                for classname in obj._converter_for:
                    converters[classname] = obj

        self._converters = converters

    async def _prepare_kwargs(
        self,
        prop: MODEL_ATTR_TYPE,
        engine: ENGINE_TYPE,
        field_args: Dict[str, Any],
        field_widget_args: Dict[str, Any],
        form_include_pk: bool,
        label: Optional[str] = None,
        loader: Optional[QueryAjaxModelLoader] = None,
    ) -> Optional[Dict[str, Any]]:
        kwargs: Union[dict, None]
        kwargs = field_args.copy()
        widget_args = field_widget_args.copy()
        widget_args.setdefault("class", "form-control")

        kwargs.setdefault("label", label)
        kwargs.setdefault("validators", [])
        kwargs.setdefault("filters", [])
        kwargs.setdefault("default", None)
        kwargs.setdefault("description", prop.doc)
        kwargs.setdefault("render_kw", widget_args)

        if isinstance(prop, ColumnProperty):
            kwargs = self._prepare_column(
                prop=prop, kwargs=kwargs, form_include_pk=form_include_pk
            )
        else:
            kwargs = await self._prepare_relationship(
                prop=prop, engine=engine, kwargs=kwargs, loader=loader
            )

        return kwargs

    def _prepare_column(
        self, prop: ColumnProperty, form_include_pk: bool, kwargs: dict
    ) -> Union[dict, None]:
        assert len(prop.columns) == 1, "Multiple-column properties not supported"
        column = prop.columns[0]

        if (column.primary_key or column.foreign_keys) and not form_include_pk:
            return None

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
        optional_types = (Boolean,)

        if column.nullable:
            kwargs["validators"].append(validators.Optional())

        if (
            not column.nullable
            and not isinstance(column.type, optional_types)
            and not column.default
            and not column.server_default
        ):
            kwargs["validators"].append(validators.InputRequired())

        return kwargs

    async def _prepare_relationship(
        self,
        prop: RelationshipProperty,
        kwargs: dict,
        engine: ENGINE_TYPE,
        loader: Optional[QueryAjaxModelLoader] = None,
    ) -> dict:
        nullable = True
        for pair in prop.local_remote_pairs:
            if not pair[0].nullable:
                nullable = False

        kwargs["allow_blank"] = nullable

        if not loader:
            kwargs.setdefault("data", await self._prepare_select_options(prop, engine))

        return kwargs

    async def _prepare_select_options(
        self,
        prop: RelationshipProperty,
        engine: ENGINE_TYPE,
    ) -> List[Tuple[str, Any]]:
        target_model = prop.mapper.class_
        pk = get_primary_key(target_model)
        stmt = select(target_model).limit(100)

        if isinstance(engine, Engine):
            with Session(engine) as session:
                objects = await anyio.to_thread.run_sync(session.execute, stmt)
                return [
                    (self._get_pk_value(obj, pk), str(obj))
                    for obj in objects.scalars().all()
                ]
        elif isinstance(engine, AsyncEngine):
            async with AsyncSession(engine) as session:
                objects = await session.execute(stmt)
                return [
                    (self._get_pk_value(obj, pk), str(obj))
                    for obj in objects.scalars().all()
                ]

        return []  # pragma: nocover

    def get_converter(self, prop: MODEL_ATTR_TYPE) -> ConverterCallable:
        if isinstance(prop, RelationshipProperty):
            direction = get_direction(prop)
            return self._converters[direction]

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
                if callable(col_type.impl):  # type: ignore
                    impl = col_type.impl  # type: ignore
                else:
                    impl = col_type.impl.__class__  # type: ignore

                if impl.__name__ in self._converters:
                    return self._converters[impl.__name__]

        raise NoConverterFound(  # pragma: nocover
            f"Could not find field converter for column {column.name} ({types[0]!r})."
        )

    async def convert(
        self,
        model: type,
        prop: MODEL_ATTR_TYPE,
        engine: ENGINE_TYPE,
        field_args: Dict[str, Any],
        field_widget_args: Dict[str, Any],
        form_include_pk: bool,
        label: Optional[str] = None,
        override: Optional[Type[Field]] = None,
        form_ajax_refs: Dict[str, QueryAjaxModelLoader] = {},
    ) -> Optional[UnboundField]:

        loader = form_ajax_refs.get(prop.key)
        kwargs = await self._prepare_kwargs(
            prop=prop,
            engine=engine,
            field_args=field_args,
            field_widget_args=field_widget_args,
            label=label,
            form_include_pk=form_include_pk,
            loader=loader,
        )

        if kwargs is None:
            return None

        if override is not None:
            assert issubclass(override, Field)
            return override(**kwargs)

        multiple = (
            is_relationship(prop)
            and prop.direction.name in ("ONETOMANY", "MANYTOMANY")
            and prop.uselist
        )

        if loader:
            if multiple:
                return AjaxSelectMultipleField(loader, **kwargs)
            else:
                return AjaxSelectField(loader, **kwargs)

        converter = self.get_converter(prop=prop)
        return converter(model=model, prop=prop, kwargs=kwargs)

    def _get_pk_value(self, o: Any, pk: Column) -> str:
        return str(getattr(o, pk.name))


class ModelConverter(ModelConverterBase):
    @staticmethod
    def _string_common(prop: ColumnProperty) -> List[Validator]:
        li = []
        column: Column = prop.columns[0]
        if isinstance(column.type.length, int) and column.type.length:
            li.append(validators.Length(max=column.type.length))
        return li

    @converts("String", "CHAR")  # includes Unicode
    def conv_string(
        self, model: type, prop: ColumnProperty, kwargs: Dict[str, Any]
    ) -> UnboundField:
        extra_validators = self._string_common(prop)
        kwargs.setdefault("validators", [])
        kwargs["validators"].extend(extra_validators)
        return StringField(**kwargs)

    @converts("Text", "LargeBinary", "Binary")  # includes UnicodeText
    def conv_text(
        self, model: type, prop: ColumnProperty, kwargs: Dict[str, Any]
    ) -> UnboundField:
        kwargs.setdefault("validators", [])
        extra_validators = self._string_common(prop)
        kwargs["validators"].extend(extra_validators)
        return TextAreaField(**kwargs)

    @converts("Boolean", "dialects.mssql.base.BIT")
    def conv_boolean(
        self, model: type, prop: ColumnProperty, kwargs: Dict[str, Any]
    ) -> UnboundField:
        if not prop.columns[0].nullable:
            kwargs.setdefault("render_kw", {})
            kwargs["render_kw"]["class"] = "form-check-input"
            return BooleanField(**kwargs)

        kwargs["allow_blank"] = True
        kwargs["choices"] = [(True, "True"), (False, "False")]
        kwargs["coerce"] = lambda v: str(v) == "True"
        return SelectField(**kwargs)

    @converts("Date")
    def conv_date(
        self, model: type, prop: ColumnProperty, kwargs: Dict[str, Any]
    ) -> UnboundField:
        return DateField(**kwargs)

    @converts("Time")
    def conv_time(
        self, model: type, prop: ColumnProperty, kwargs: Dict[str, Any]
    ) -> UnboundField:
        return TimeField(**kwargs)

    @converts("DateTime")
    def conv_datetime(
        self, model: type, prop: ColumnProperty, kwargs: Dict[str, Any]
    ) -> UnboundField:
        return DateTimeField(**kwargs)

    @converts("Enum")
    def conv_enum(
        self, model: type, prop: ColumnProperty, kwargs: Dict[str, Any]
    ) -> UnboundField:
        available_choices = [(e, e) for e in prop.columns[0].type.enums]
        accepted_values = [choice[0] for choice in available_choices]

        if prop.columns[0].nullable:
            kwargs["allow_blank"] = True
            accepted_values.append(None)
            filters = kwargs.get("filters", [])
            filters.append(lambda x: x or None)
            kwargs["filters"] = filters

        kwargs["choices"] = available_choices
        kwargs.setdefault("validators", [])
        kwargs["validators"].append(validators.AnyOf(accepted_values))
        kwargs["coerce"] = lambda v: v.name if isinstance(v, Enum) else str(v)
        return SelectField(**kwargs)

    @converts("Integer")  # includes BigInteger and SmallInteger
    def conv_integer(
        self, model: type, prop: ColumnProperty, kwargs: Dict[str, Any]
    ) -> UnboundField:
        return IntegerField(**kwargs)

    @converts("Numeric")  # includes DECIMAL, Float/FLOAT, REAL, and DOUBLE
    def conv_decimal(
        self, model: type, prop: ColumnProperty, kwargs: Dict[str, Any]
    ) -> UnboundField:
        # override default decimal places limit, use database defaults instead
        kwargs.setdefault("places", None)
        return DecimalField(**kwargs)

    @converts("JSON")
    def conv_json(
        self, model: type, prop: ColumnProperty, kwargs: Dict[str, Any]
    ) -> UnboundField:
        return JSONField(**kwargs)

    # @converts("dialects.mysql.types.YEAR", "dialects.mysql.base.YEAR")
    # def conv_MSYear(self, field_args: Dict, **kwargs: Any) -> Field:
    #     field_args["validators"].append(validators.NumberRange(min=1901, max=2155))
    #     return StringField(**field_args)

    @converts(
        "sqlalchemy.dialects.postgresql.base.INET",
        "sqlalchemy_utils.types.ip_address.IPAddressType",
    )
    def conv_ip_address(
        self, model: type, prop: ColumnProperty, kwargs: Dict[str, Any]
    ) -> UnboundField:
        kwargs.setdefault("label", "IP Address")
        kwargs.setdefault("validators", [])
        kwargs["validators"].append(validators.IPAddress(ipv4=True, ipv6=True))
        return StringField(**kwargs)

    @converts("sqlalchemy.dialects.postgresql.base.MACADDR")
    def conv_mac_address(
        self, model: type, prop: ColumnProperty, kwargs: Dict[str, Any]
    ) -> UnboundField:
        kwargs.setdefault("label", "MAC Address")
        kwargs.setdefault("validators", [])
        kwargs["validators"].append(validators.MacAddress())
        return StringField(**kwargs)

    @converts(
        "sqlalchemy.dialects.postgresql.base.UUID",
        "sqlalchemy_utils.types.uuid.UUIDType",
    )
    def conv_uuid(
        self, model: type, prop: ColumnProperty, kwargs: Dict[str, Any]
    ) -> UnboundField:
        kwargs.setdefault("label", "UUID")
        kwargs.setdefault("validators", [])
        kwargs["validators"].append(validators.UUID())
        return StringField(**kwargs)

    @converts("sqlalchemy_utils.types.email.EmailType")
    def conv_email(
        self, model: type, prop: ColumnProperty, kwargs: Dict[str, Any]
    ) -> UnboundField:
        kwargs.setdefault("label", "Email")
        kwargs.setdefault("validators", [])
        kwargs["validators"].append(validators.Email())
        return StringField(**kwargs)

    @converts("sqlalchemy_utils.types.url.URLType")
    def conv_url(
        self, model: type, prop: ColumnProperty, kwargs: Dict[str, Any]
    ) -> UnboundField:
        kwargs.setdefault("validators", [])
        kwargs["validators"].append(validators.URL())
        return StringField(**kwargs)

    @converts("sqlalchemy_utils.types.currency.CurrencyType")
    def conv_currency(
        self, model: type, prop: ColumnProperty, kwargs: Dict[str, Any]
    ) -> UnboundField:
        kwargs.setdefault("validators", [])
        kwargs["validators"].append(CurrencyValidator())
        return StringField(**kwargs)

    @converts("sqlalchemy_utils.types.timezone.TimezoneType")
    def conv_timezone(
        self, model: type, prop: ColumnProperty, kwargs: Dict[str, Any]
    ) -> UnboundField:
        kwargs.setdefault("validators", [])
        kwargs["validators"].append(
            TimezoneValidator(coerce_function=prop.columns[0].type._coerce)
        )
        return StringField(**kwargs)

    @converts("ONETOONE")
    def conv_one_to_one(
        self, model: type, prop: RelationshipProperty, kwargs: Dict[str, Any]
    ) -> UnboundField:
        kwargs["allow_blank"] = True
        return QuerySelectField(**kwargs)

    @converts("MANYTOONE")
    def conv_many_to_one(
        self, model: type, prop: RelationshipProperty, kwargs: Dict[str, Any]
    ) -> UnboundField:
        return QuerySelectField(**kwargs)

    @converts("MANYTOMANY", "ONETOMANY")
    def conv_many_to_many(
        self, model: type, prop: RelationshipProperty, kwargs: Dict[str, Any]
    ) -> UnboundField:
        return QuerySelectMultipleField(**kwargs)


async def get_model_form(
    model: type,
    engine: ENGINE_TYPE,
    only: Sequence[str] = None,
    exclude: Sequence[str] = None,
    column_labels: Dict[str, str] = None,
    form_args: Dict[str, Dict[str, Any]] = None,
    form_widget_args: Dict[str, Dict[str, Any]] = None,
    form_class: Type[Form] = Form,
    form_overrides: Dict[str, Type[Field]] = None,
    form_ajax_refs: Dict[str, QueryAjaxModelLoader] = None,
    form_include_pk: bool = False,
) -> Type[Form]:
    type_name = model.__name__ + "Form"
    converter = ModelConverter()
    mapper = sqlalchemy_inspect(model)
    form_args = form_args or {}
    form_widget_args = form_widget_args or {}
    column_labels = column_labels or {}
    form_overrides = form_overrides or {}
    form_ajax_refs = form_ajax_refs or {}

    attributes = []
    names = only or mapper.attrs.keys()
    for name in names:
        if exclude and name in exclude:
            continue
        attributes.append((name, mapper.attrs[name]))

    field_dict = {}
    for name, attr in attributes:
        field_args = form_args.get(name, {})
        field_widget_args = form_widget_args.get(name, {})
        label = column_labels.get(name, None)
        override = form_overrides.get(name, None)
        field = await converter.convert(
            model=model,
            prop=attr,
            engine=engine,
            field_args=field_args,
            field_widget_args=field_widget_args,
            label=label,
            override=override,
            form_include_pk=form_include_pk,
            form_ajax_refs=form_ajax_refs,
        )
        if field is not None:
            field_dict[name] = field

    return type(type_name, (form_class,), field_dict)
