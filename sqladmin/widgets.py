from typing import Any

from wtforms import Field, widgets

__all__ = [
    "DatePickerWidget",
    "DateTimePickerWidget",
    "Select2Widget",
    "Select2TagsWidget",
]


class Select2Widget(widgets.Select):
    """
    `Select2 <https://github.com/select2/select2>`_ styled select widget.
    """

    def __call__(self, field: Field, **kwargs: Any) -> str:
        kwargs.setdefault("data-role", "select2")

        allow_blank = getattr(field, "allow_blank", False)
        if allow_blank and not self.multiple:
            kwargs["data-allow-blank"] = "1"

        return super().__call__(field, **kwargs)


class Select2TagsWidget(widgets.TextInput):
    """
    `Select2 <https://github.com/select2/select2>`_ styled text widget.
    """

    def __call__(self, field: Field, **kwargs: Any) -> str:
        kwargs.setdefault("data-role", "select2-tags")
        return super().__call__(field, **kwargs)


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
        kwargs.setdefault("data-date-format", "HH:mm:ss")
        return super().__call__(field, **kwargs)
