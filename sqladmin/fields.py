import datetime
import json
import operator
import time
from typing import Any, Callable, Generator, List, Optional, Tuple, Union

from wtforms import Form, ValidationError, fields, widgets

from sqladmin import widgets as sqladmin_widgets
from sqladmin.helpers import as_str

__all__ = [
    "DateField",
    "DateTimeField",
    "JSONField",
    "QuerySelectField",
    "QuerySelectMultipleField",
    "Select2Field",
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

    def __init__(
        self,
        label: str = None,
        validators: list = None,
        format: str = None,
        **kwargs: Any,
    ) -> None:
        """
        Constructor
        :param label:
            Label
        :param validators:
            Field validators
        :param format:
            Format for text to date conversion. Defaults to '%Y-%m-%d %H:%M:%S'
        :param kwargs:
            Any additional parameters
        """
        super().__init__(label, validators, **kwargs)

        self.format = format or "%Y-%m-%d %H:%M:%S"


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


class Select2Field(fields.SelectField):
    """
    `Select2 <https://github.com/select2/select2>`_ styled select widget.
    """

    widget = sqladmin_widgets.Select2Widget()

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
        # elif self.data:
        #     # prevent utf8 characters from being converted to ascii
        #     return as_str(json.dumps(self.data, ensure_ascii=False))
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
    """
    Will display a select drop-down field to choose between ORM results in a
    sqlalchemy `Query`.  The `data` property actually will store/keep an ORM
    model instance, not the ID. Submitting a choice which is not in the query
    will result in a validation error.

    This field only works for queries on models whose primary key column(s)
    have a consistent string representation. This means it mostly only works
    for those composed of string, unicode, and integer types. For the most
    part, the primary keys will be auto-detected from the model, alternately
    pass a one-argument callable to `get_pk` which can return a unique
    comparable key.

    Specify `get_label` to customize the label associated with each option. If
    a string, this is the name of an attribute on the model object to use as
    the label text. If a one-argument callable, this callable will be passed
    model instance and expected to return the label text. Otherwise, the model
    object's `__str__` will be used.

    If `allow_blank` is set to `True`, then a blank choice will be added to the
    top of the list. Selecting this choice will result in the `data` property
    being `None`. The label for this blank choice can be set by specifying the
    `blank_text` parameter.
    """

    widget = widgets.Select()

    def __init__(
        self,
        object_list: list = None,
        label: str = None,
        validators: list = None,
        get_label: Union[Callable, str] = None,
        allow_blank: bool = False,
        blank_text: str = "",
        **kwargs: Any,
    ) -> None:
        super().__init__(label=label, validators=validators, **kwargs)

        self._object_list = object_list or []

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
            for pk, obj in self._object_list:
                if pk == self._formdata:
                    self.data = obj
                    break
        return self._data

    @data.setter
    def data(self, data: tuple) -> None:
        self._data = data
        self._formdata = None

    def iter_choices(self) -> Generator[Tuple[str, str, bool], None, None]:
        if self.allow_blank:
            yield ("__None", self.blank_text, self.data is None)

        for pk, obj in self._object_list:
            yield (pk, self.get_label(obj), obj == self.data)

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
            for _, obj in self._object_list:
                if data == obj:
                    break
            else:
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
        object_list: list = None,
        label: str = None,
        validators: list = None,
        default: Any = None,
        **kwargs: Any,
    ) -> None:
        default = default or []
        super().__init__(label=label, validators=validators, default=default, **kwargs)

        self._object_list = object_list or []

        if kwargs.get("allow_blank", False):
            import warnings

            warnings.warn(
                "allow_blank=True does not do anything for QuerySelectMultipleField."
            )
        self._invalid_formdata = False
        self._formdata: Optional[List[str]] = None

    @property
    def data(self) -> Optional[tuple]:
        formdata = self._formdata
        if formdata is not None:
            data = []
            for pk, obj in self._object_list:
                if not formdata:
                    break
                elif pk in formdata:
                    formdata.remove(pk)
                    data.append(obj)
            if formdata:
                self._invalid_formdata = True
            self.data = data  # type: ignore
        return self._data

    @data.setter
    def data(self, data: tuple) -> None:
        self._data = data
        self._formdata = None

    def iter_choices(self) -> Generator[Tuple[str, Any, bool], None, None]:
        if self.data is not None:
            for pk, obj in self._object_list:
                yield (pk, self.get_label(obj), obj in self.data)

    def process_formdata(self, valuelist: List[str]) -> None:
        self._formdata = list(set(valuelist))

    def pre_validate(self, form: Form) -> None:
        if self._invalid_formdata:
            raise ValidationError(self.gettext("Not a valid choice"))
        elif self.data:
            obj_list = [x[1] for x in self._object_list]
            for v in self.data:
                if v not in obj_list:
                    raise ValidationError(self.gettext("Not a valid choice"))
