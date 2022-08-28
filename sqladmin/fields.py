import datetime
import json
import operator
import time
from typing import Any, Callable, Generator, List, Optional, Tuple, Union

from sqlalchemy import inspect
from wtforms import Form, SelectFieldBase, ValidationError, fields, widgets

from sqladmin import widgets as sqladmin_widgets
from sqladmin.helpers import as_str

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


class TimeField(fields.Field):
    """
    A text field which stores a `datetime.time` object.
    Accepts time string in multiple formats: 20:10, 20:10:00, 10:00 am, 9:30pm, etc.
    """

    widget = sqladmin_widgets.TimePickerWidget()

    def __init__(
        self,
        label: str = None,
        validators: list = None,
        formats: List[str] = None,
        default_format: str = None,
        **kwargs: Any,
    ) -> None:
        """
        Constructor

        :param label:
            Label
        :param validators:
            Field validators
        :param formats:
            Supported time formats, as a enumerable.
        :param default_format:
            Default time format. Defaults to '%H:%M:%S'
        :param kwargs:
            Any additional parameters
        """
        super().__init__(label, validators, **kwargs)

        self.formats = formats or (
            "%H:%M:%S",
            "%H:%M",
            "%I:%M:%S%p",
            "%I:%M%p",
            "%I:%M:%S %p",
            "%I:%M %p",
        )

        self.default_format = default_format or "%H:%M:%S"
        self.data: Optional[datetime.time]

    def _value(self) -> str:
        if self.raw_data:
            return " ".join(self.raw_data)
        elif self.data is not None:
            return self.data.strftime(self.default_format)
        else:
            return ""

    def process_formdata(self, valuelist: List[str]) -> None:
        if valuelist:
            date_str = " ".join(valuelist)

            if date_str.strip():
                for format in self.formats:
                    try:
                        timetuple = time.strptime(date_str, format)
                        self.data = datetime.time(
                            timetuple.tm_hour, timetuple.tm_min, timetuple.tm_sec
                        )
                        return
                    except ValueError:
                        pass

                raise ValueError("Invalid time format")
            else:
                self.data = None


class SelectField(fields.SelectField):
    def __init__(
        self,
        label: str = None,
        validators: list = None,
        coerce: type = str,
        choices: Union[list, Callable] = None,
        allow_blank: bool = False,
        blank_text: str = None,
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


class Select2TagsField(fields.StringField):
    """
    `Select2 <https://github.com/select2/select2>`_ styled text field.
    """

    widget = sqladmin_widgets.Select2TagsWidget()

    def __init__(
        self,
        label: str = None,
        validators: list = None,
        save_as_list: bool = False,
        coerce: type = str,
        **kwargs: Any,
    ) -> None:
        """
        Initialization

        :param save_as_list:
            If `True` then populate ``obj`` using list else string
        """
        self.save_as_list = save_as_list
        self.coerce = coerce

        super().__init__(label, validators, **kwargs)

    def process_formdata(self, valuelist: List[str]) -> None:
        if valuelist:
            if self.save_as_list:
                self.data = [
                    self.coerce(v.strip()) for v in valuelist[0].split(",") if v.strip()
                ]
            else:
                self.data = self.coerce(valuelist[0])

    def _value(self) -> str:
        if isinstance(self.data, (list, tuple)):
            return ",".join(as_str(v) for v in self.data)
        elif self.data:
            return as_str(self.data)
        else:
            return ""


class JSONField(fields.TextAreaField):
    def _value(self) -> str:
        if self.raw_data:
            return self.raw_data[0]
        elif self.data:
            return as_str(json.dumps(self.data, ensure_ascii=False))
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
        data: list = None,
        label: str = None,
        validators: list = None,
        get_label: Union[Callable, str] = None,
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
        data: list = None,
        label: str = None,
        validators: list = None,
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
    """Ajax Model Select Field"""

    widget = sqladmin_widgets.AjaxSelect2Widget()

    separator = ","

    def __init__(
        self,
        loader,
        label=None,
        validators=None,
        allow_blank=False,
        blank_text="",
        object_list=None,
        **kwargs,
    ):
        super().__init__(label, validators, **kwargs)
        self.loader = loader

        self.allow_blank = allow_blank
        self.blank_text = blank_text

    @property
    def data(self) -> Any:
        if self._formdata:
            self.data = self._formdata

        return self._data

    @data.setter
    def data(self, data: Any) -> None:
        self._data = data
        self._formdata = None

    def _format_item(self, item):
        value = self.loader.format(self.data)
        return (value[0], value[1], True)

    def process_formdata(self, valuelist):
        if valuelist:
            if self.allow_blank and valuelist[0] == "__None":
                self.data = None
            else:
                self._data = None
                self._formdata = valuelist[0]

    def pre_validate(self, form):
        if not self.allow_blank and self.data is None:
            raise ValidationError("Not a valid choice")


class AjaxSelectMultipleField(AjaxSelectField):
    """Ajax-enabled model multi-select field."""

    widget = sqladmin_widgets.AjaxSelect2Widget(multiple=True)

    def __init__(self, loader, label=None, validators=None, default=None, **kwargs):
        default = default or []

        super().__init__(loader, label, validators, default=default, **kwargs)
        self._invalid_formdata = False

    @property
    def data(self):
        formdata = self._formdata
        if formdata:
            self.data(formdata)

        return self._data

    @data.setter
    def data(self, data) -> None:
        self._data = data
        self._formdata = None

    def process_formdata(self, valuelist) -> None:
        self._formdata = set()

        for field in valuelist:
            for n in field.split(self.separator):
                self._formdata.add(n)

    def pre_validate(self, form: Form) -> None:
        if self._invalid_formdata:
            raise ValidationError("Not a valid choice")
