from typing import Any

from wtforms import Field, widgets

__all__ = [
    "DatePickerWidget",
    "DateTimePickerWidget",
    "TimePickerWidget",
]


class DatePickerWidget(widgets.TextInput):
    """
    Date picker widget.
    """

    def __call__(self, field: Field, **kwargs: Any) -> str:
        kwargs.setdefault("data-role", "datepicker")
        return super().__call__(field, **kwargs)


class DateTimePickerWidget(widgets.TextInput):
    """
    Datetime picker widget.
    """

    def __call__(self, field: Field, **kwargs: Any) -> str:
        kwargs.setdefault("data-role", "datetimepicker")
        return super().__call__(field, **kwargs)


class TimePickerWidget(widgets.TextInput):
    """
    Time picker widget.
    """

    def __call__(self, field: Field, **kwargs: Any) -> str:
        kwargs.setdefault("data-role", "timepicker")
        return super().__call__(field, **kwargs)
