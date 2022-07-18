from typing import Any

from markupsafe import Markup
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


class ListWidget:
    """
    ListWidget looks like WTForm's ListField but with a sub html tag.

    The `sub_html_tag` is the tag that will be used to
    render the sub-fields of the list.
    The `sub_render_kw` looks like the `render_kw` but for render sub-fields.
    """

    def __init__(
        self,
        html_tag="div",
        sub_html_tag="label",
        sub_render_kw=None,
        prefix_label=True,
    ):
        self.html_tag = html_tag
        self.sub_html_tag = sub_html_tag
        self.sub_render_kw = sub_render_kw
        self.prefix_label = prefix_label

    def __call__(self, field, **kwargs):
        kwargs.setdefault("id", field.id)
        html = [f"<{self.html_tag} {widgets.html_params(**kwargs)}>"]
        render_kw = (
            self.sub_render_kw
            and " ".join([f"{k}={v}" for k, v in self.sub_render_kw.items()])
            or ""
        )
        for subfield in field:
            if self.prefix_label:
                html.append(
                    f"""
                    <{self.sub_html_tag} {render_kw}>
                    {subfield.label} {subfield()}
                    </{self.sub_html_tag}>
                    """
                )
            else:
                html.append(
                    f"""
                    <{self.sub_html_tag} {render_kw}>
                    {subfield()} {subfield.label}
                    </{self.sub_html_tag}>"""
                )
        html.append("</%s>" % self.html_tag)
        return Markup("".join(html))


class RadioInput(widgets.RadioInput):
    """
    RadioInput looks like WTForm's RadioField but add tabler UI class.
    """

    def __call__(self, field, **kwargs):
        kwargs["class"] = "form-check-input"
        return super().__call__(field, **kwargs)
