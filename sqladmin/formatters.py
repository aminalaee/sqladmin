import datetime
from enum import StrEnum
from typing import Any

from markupsafe import Markup

from sqladmin._types import BASE_FORMATTERS_TYPE


def empty_formatter(value: Any) -> Markup:
    """Return empty string for `None` value"""

    return Markup("")


def bool_formatter(value: bool) -> Markup:
    """Return check icon if value is `True` or X otherwise."""

    icon_class = "fa-check text-success" if value else "fa-times text-danger"
    return Markup("<i class='fa {}'></i>").format(icon_class)


def str_enum_formatter(value: StrEnum) -> Markup:
    """Return badge for value and list of available StrEnum values in tooltip."""

    title = ""
    if hasattr(value, "_member_names_") and len(value._member_names_) > 0:
        title = f'title="Available values: {", ".join(value._member_names_)}">'

    return Markup(
        f'<span class="my-1 py-1 px-2 badge bg-secondary '
        f'text-light lead d-inline-block text-truncate" '
        f'data-bs-toggle="tooltip" '
        f'data-bs-html="true" '
        f'data-bs-placement="bottom" '
        f"{title}"
        f"{value}"
        f"</span>"
    )


def datetime_formatter(value: datetime.datetime) -> Markup:
    """Return badge for easy viewing of datetime."""

    return Markup(
        f'<span '
        f'class="my-1 py-1 px-2 badge bg-secondary text-light '
        f'lead d-inline-block text-truncate" '
        f'data-bs-toggle="tooltip" '
        f'data-bs-html="true" '
        f'data-bs-placement="bottom" '
        f'title="{value}"'
        f'>'
        f'<i class="fa-solid fa-calendar-days"></i> '
        f'{value.strftime('%d %B %Y %H:%M:%S')}'
        f'</span>'
    )


def copy_to_clipboard_formatter(value: Any) -> Markup:
    """Return value with copy to clipboard button and alert."""

    return Markup(
        f'<div class="d-flex justify-content-start align-items-center">'
        f'<div class="me-2">{value}</div>'
        f"<button "
        f'class="btn btn-link p-2 me-2" '
        f"""onclick='copyToClipboard(this, "{value}")'"""
        f">"
        f'<i class="fas fa-copy"></i>'
        f"</button>"
        f'<div class="alert alert-primary fade mb-0 p-1">Copied!</div>'
        f"</div>"
    )


BASE_FORMATTERS: BASE_FORMATTERS_TYPE = {
    type(None): empty_formatter,
    bool: bool_formatter,
}
