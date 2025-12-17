import json
from typing import Any

from markupsafe import Markup
from wtforms import Field, widgets
from wtforms.widgets import html_params

__all__ = [
    "AjaxSelect2Widget",
    "DatePickerWidget",
    "DateTimePickerWidget",
    "Select2TagsWidget",
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


class AjaxSelect2Widget(widgets.Select):
    def __init__(self, multiple: bool = False):
        self.multiple = multiple
        self.lookup_url = ""

    def __call__(self, field: Field, **kwargs: Any) -> Markup:
        kwargs.setdefault("data-role", "select2-ajax")
        kwargs.setdefault("data-url", field.loader.model_admin.ajax_lookup_url)

        allow_blank = getattr(field, "allow_blank", False)
        if allow_blank and not self.multiple:
            kwargs["data-allow-blank"] = "1"

        kwargs.setdefault("id", field.id)
        kwargs.setdefault("type", "hidden")

        if self.multiple:
            result = [field.loader.format(value) for value in field.data]
            kwargs["data-json"] = json.dumps(result)
            kwargs["multiple"] = "1"
        else:
            try:
                data = field.loader.format(field.data)
            except Exception:
                data = None
            if data:
                kwargs["data-json"] = json.dumps([data])

        return Markup(f"<select {html_params(name=field.name, **kwargs)}></select>")


class Select2TagsWidget(widgets.Select):
    def __call__(self, field: Field, **kwargs: Any) -> str:
        kwargs.setdefault("data-role", "select2-tags")
        kwargs.setdefault("data-json", json.dumps(field.data))
        kwargs.setdefault("multiple", "multiple")
        return super().__call__(field, **kwargs)


class FileInputWidget(widgets.FileInput):
    """
    File input widget with clear checkbox.
    """

    def __call__(self, field: Field, **kwargs: Any) -> str:
        if not field.flags.required:
            checkbox_id = f"{field.id}_checkbox"
            checkbox_label = Markup(
                f'<label class="form-check-label" for="{checkbox_id}">Clear</label>'
            )
            checkbox_input = Markup(
                f'<input class="form-check-input" type="checkbox" id="{checkbox_id}" name="{checkbox_id}">'  # noqa: E501
            )
            checkbox = Markup(
                f'<div class="form-check">{checkbox_input}{checkbox_label}</div>'
            )
        else:
            checkbox = Markup()

        if field.data:
            current_value = Markup(f"<p>Currently: {field.data}</p>")
            field.flags.required = False
            return current_value + checkbox + super().__call__(field, **kwargs)
        else:
            return super().__call__(field, **kwargs)


class BooleanInputWidget(widgets.Input):
    """
    Render a checkbox.

    The ``checked`` HTML attribute is set if the field's data is a non-false value.
    """

    input_type = "checkbox"

    def __call__(self, field: Field, **kwargs: Any) -> Markup:
        kwargs["checked"] = field.object_data

        return Markup(
            '<div class="form-switch d-flex align-items-center h-100">'
            + str(Markup.escape(super().__call__(field, **kwargs)))
            + "</div>"
        )
