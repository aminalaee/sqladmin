import json
from typing import Any

from markupsafe import Markup
from wtforms import Field, widgets
from wtforms.widgets import html_params

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
        kwargs.setdefault("data-date-format", "YYYY-MM-DD")

        self.date_format = kwargs["data-date-format"]
        return super().__call__(field, **kwargs)


class DateTimePickerWidget(widgets.TextInput):
    """
    Datetime picker widget.
    """

    def __call__(self, field: Field, **kwargs: Any) -> str:
        kwargs.setdefault("data-role", "datetimepicker")
        kwargs.setdefault("data-date-format", "YYYY-MM-DD HH:mm:ss")
        return super().__call__(field, **kwargs)


class TimePickerWidget(widgets.TextInput):
    """
    Time picker widget.
    """

    def __call__(self, field: Field, **kwargs: Any) -> str:
        kwargs.setdefault("data-role", "timepicker")
        kwargs.setdefault("data-date-format", "HH:mm:ss")
        return super().__call__(field, **kwargs)


class AjaxSelect2Widget(object):
    def __init__(self, multiple: bool = False):
        self.multiple = multiple
        self.lookup_url = ""

    def __call__(self, field: Field, **kwargs: dict) -> Markup:
        kwargs.setdefault("data-role", "select2-ajax")
        kwargs.setdefault("data-url", field.loader.model_admin.ajax_lookup_url)

        allow_blank = getattr(field, "allow_blank", False)
        if allow_blank and not self.multiple:
            kwargs["data-allow-blank"] = "1"

        kwargs.setdefault("id", field.id)
        kwargs.setdefault("type", "hidden")

        if self.multiple:
            result = []
            ids = []

            for value in field.data:
                data = field.loader.format(value)
                result.append(data)
                ids.append(str(data[0]))

            separator = getattr(field, "separator", ",")

            kwargs["value"] = separator.join(ids)
            kwargs["data-json"] = json.dumps(result)
            kwargs["data-multiple"] = "1"
        else:
            data = field.loader.format(field.data)

            if data:
                kwargs["value"] = data[0]
                kwargs["data-json"] = json.dumps(data)

        placeholder = field.loader.options.get("placeholder", "Please select model")
        kwargs.setdefault("data-placeholder", placeholder)

        minimum_input_length = int(field.loader.options.get("minimum_input_length", 1))
        kwargs.setdefault("data-minimum-input-length", minimum_input_length)

        return Markup(f"<select {html_params(name=field.name, **kwargs)}></select>")
