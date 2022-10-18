import json
import operator
from typing import Any, Callable, Generator, List, Optional, Set, Tuple, Union

from sqlalchemy import inspect
from wtforms import Form, SelectFieldBase, ValidationError, fields, widgets

from sqladmin import widgets as sqladmin_widgets
from sqladmin.ajax import QueryAjaxModelLoader

__all__ = [
    "AjaxSelectField",
    "AjaxSelectMultipleField",
    "DateField",
    "DateTimeField",
    "JSONField",
    "QuerySelectField",
    "QuerySelectMultipleField",
    "SelectField",
    "Select2TagsField",
    "TimeField",
]


class DateField(fields.DateField):
    """
    Add custom DatePickerWidget for data-format and data-date-format fields
    """

    widget = sqladmin_widgets.DatePickerWidget()


class DateTimeField(fields.DateTimeField):
    """
    Allows modifying the datetime format of a DateTimeField using form_args.
    """

    widget = sqladmin_widgets.DateTimePickerWidget()


class TimeField(fields.TimeField):
    """
    A text field which stores a `datetime.time` object.
    """

    widget = sqladmin_widgets.TimePickerWidget()


class SelectField(fields.SelectField):
    def __init__(
        self,
        label: Optional[str] = None,
        validators: Optional[list] = None,
        coerce: type = str,
        choices: Optional[Union[list, Callable]] = None,
        allow_blank: bool = False,
        blank_text: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(label, validators, coerce, choices, **kwargs)
        self.allow_blank = allow_blank
        self.blank_text = blank_text or " "

    def iter_choices(self) -> Generator[Tuple[str, str, bool], None, None]:
        choices = self.choices or []

        if self.allow_blank:
            yield ("__None", self.blank_text, self.data is None)

        for choice in choices:
            if isinstance(choice, tuple):
                yield (choice[0], choice[1], self.coerce(choice[0]) == self.data)
            else:
                yield (
                    choice.value,
                    choice.name,
                    self.coerce(choice.value) == self.data,
                )

    def process_formdata(self, valuelist: List[str]) -> None:
        if valuelist:
            if valuelist[0] == "__None":
                self.data = None
            else:
                try:
                    self.data = self.coerce(valuelist[0])
                except ValueError:
                    raise ValueError(self.gettext("Invalid Choice: could not coerce"))

    def pre_validate(self, form: Form) -> None:
        if self.allow_blank and self.data is None:
            return

        super().pre_validate(form)


class JSONField(fields.TextAreaField):
    def _value(self) -> str:
        if self.raw_data:
            return self.raw_data[0]
        elif self.data:
            return str(json.dumps(self.data, ensure_ascii=False))
        else:
            return "{}"

    def process_formdata(self, valuelist: List[str]) -> None:
        if valuelist:
            value = valuelist[0]

            # allow saving blank field as None
            if not value:
                self.data = None
                return

            try:
                self.data = json.loads(valuelist[0])
            except ValueError:
                raise ValueError(self.gettext("Invalid JSON"))


class QuerySelectField(fields.SelectFieldBase):
    widget = widgets.Select()

    def __init__(
        self,
        data: Optional[list] = None,
        label: Optional[str] = None,
        validators: Optional[list] = None,
        get_label: Optional[Union[Callable, str]] = None,
        allow_blank: bool = False,
        blank_text: str = "",
        **kwargs: Any,
    ) -> None:
        super().__init__(label=label, validators=validators, **kwargs)

        self._select_data = data or []

        if get_label is None:
            self.get_label = lambda x: x
        elif isinstance(get_label, str):
            self.get_label = operator.attrgetter(get_label)
        else:
            self.get_label = get_label

        self.allow_blank = allow_blank
        self.blank_text = blank_text
        self._data: Optional[tuple]
        self._formdata: Optional[Union[str, List[str]]]

    @property
    def data(self) -> Optional[tuple]:
        if self._formdata is not None:
            for pk, _ in self._select_data:
                if pk == self._formdata:
                    self.data = pk
                    break
        return self._data

    @data.setter
    def data(self, data: tuple) -> None:
        self._data = data
        self._formdata = None

    def iter_choices(self) -> Generator[Tuple[str, str, bool], None, None]:
        if self.allow_blank:
            yield ("__None", self.blank_text, self.data is None)

        if self.data:
            primary_key = str(inspect(self.data).identity[0])
        else:
            primary_key = None

        for pk, label in self._select_data:
            yield (pk, self.get_label(label), str(pk) == primary_key)

    def process_formdata(self, valuelist: List[str]) -> None:
        if valuelist:
            if self.allow_blank and valuelist[0] == "__None":
                self.data = None
            else:
                self._data = None
                self._formdata = valuelist[0]

    def pre_validate(self, form: Form) -> None:
        data = self.data
        if data is not None:
            for pk, _ in self._select_data:
                if data == pk:
                    break
            else:  # pragma: no cover
                raise ValidationError(self.gettext("Not a valid choice"))
        elif self._formdata or not self.allow_blank:
            raise ValidationError(self.gettext("Not a valid choice"))


class QuerySelectMultipleField(QuerySelectField):
    """
    Very similar to QuerySelectField with the difference that this will
    display a multiple select. The data property will hold a list with ORM
    model instances and will be an empty list when no value is selected.

    If any of the items in the data list or submitted form data cannot be
    found in the query, this will result in a validation error.
    """

    widget = widgets.Select(multiple=True)

    def __init__(
        self,
        data: Optional[list] = None,
        label: Optional[str] = None,
        validators: Optional[list] = None,
        default: Any = None,
        **kwargs: Any,
    ) -> None:
        default = default or []
        super().__init__(label=label, validators=validators, default=default, **kwargs)

        self._select_data = data or []

        if kwargs.get("allow_blank", False):
            import warnings

            warnings.warn(
                "allow_blank=True does not do anything for QuerySelectMultipleField."
            )
        self._invalid_formdata = False
        self._formdata: Optional[List[str]] = None
        self._data: Optional[tuple] = None

    @property
    def data(self) -> Optional[tuple]:
        formdata = self._formdata
        if formdata is not None:
            data = []
            for pk, _ in self._select_data:
                if not formdata:
                    break
                elif pk in formdata:
                    formdata.remove(pk)
                    data.append(pk)
            if formdata:
                self._invalid_formdata = True
            self.data = data or self._data  # type: ignore
        return self._data

    @data.setter
    def data(self, data: tuple) -> None:
        self._data = data
        self._formdata = None

    def iter_choices(self) -> Generator[Tuple[str, Any, bool], None, None]:
        if self.data is not None:
            primary_keys = [str(inspect(m).identity[0]) for m in self.data]
            for pk, label in self._select_data:
                yield (pk, self.get_label(label), pk in primary_keys)

    def process_formdata(self, valuelist: List[str]) -> None:
        self._formdata = list(set(valuelist))

    def pre_validate(self, form: Form) -> None:
        if self._invalid_formdata:
            raise ValidationError(self.gettext("Not a valid choice"))
        elif self.data:
            pk_list = [x[0] for x in self._select_data]
            for v in self.data:
                if v not in pk_list:  # pragma: no cover
                    raise ValidationError(self.gettext("Not a valid choice"))


class AjaxSelectField(SelectFieldBase):
    widget = sqladmin_widgets.AjaxSelect2Widget()
    separator = ","

    def __init__(
        self,
        loader: QueryAjaxModelLoader,
        label: Optional[str] = None,
        validators: Optional[list] = None,
        allow_blank: bool = False,
        **kwargs: Any,
    ) -> None:
        kwargs.pop("data", None)  # Handled by JS side
        self.loader = loader
        self.allow_blank = allow_blank
        super().__init__(label, validators, **kwargs)

    @property
    def data(self) -> Any:
        if self._formdata:
            self.data = self._formdata

        return self._data

    @data.setter
    def data(self, data: Any) -> None:
        self._data = data
        self._formdata = None

    def process_formdata(self, valuelist: list) -> None:
        if valuelist:
            if self.allow_blank and valuelist[0] == "__None":
                self.data = None
            else:
                self._data = None
                self._formdata = valuelist[0]

    def pre_validate(self, form: Form) -> None:
        if not self.allow_blank and self.data is None:
            raise ValidationError("Not a valid choice")


class AjaxSelectMultipleField(SelectFieldBase):
    widget = sqladmin_widgets.AjaxSelect2Widget(multiple=True)
    separator = ","

    def __init__(
        self,
        loader: QueryAjaxModelLoader,
        label: Optional[str] = None,
        validators: Optional[list] = None,
        default: Optional[list] = None,
        allow_blank: bool = False,
        **kwargs: Any,
    ) -> None:
        kwargs.pop("data", None)  # Handled by JS side
        self.loader = loader
        self.allow_blank = allow_blank
        default = default or []
        self._formdata: Set[Any] = set()

        super().__init__(label, validators, default=default, **kwargs)

    @property
    def data(self) -> Any:
        if self._formdata:
            self.data = self._formdata

        return self._data

    @data.setter
    def data(self, data: Any) -> None:
        self._data = data
        self._formdata = set()

    def process_formdata(self, valuelist: list) -> None:
        self._formdata = set()

        for field in valuelist:
            for n in field.split(self.separator):
                self._formdata.add(n)
