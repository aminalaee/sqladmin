from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, TypeAlias

from wtforms.fields.core import UnboundField

from sqladmin._types import MODEL_ATTR
from sqladmin.exceptions import InvalidModelError
from sqladmin.forms import WTFORMS_ATTRS

if TYPE_CHECKING:
    from wtforms import Form

__all__ = [
    "FieldGroup",
    "Fieldset",
    "FieldsetConfig",
    "group_form_fields",
    "normalize_fieldsets",
    "validate_fieldsets",
]

#: A fieldset may be declared as a `Fieldset` or as Django's
#: ``(title, {"fields": [...], "classes": [...]})`` tuple.
FieldsetConfig: TypeAlias = "Fieldset | tuple[str | None, dict[str, Any]]"


@dataclass
class Fieldset:
    """A named group of form fields on the create and edit pages.

    Fields can be given as string names or as SQLAlchemy columns. Any field of
    the form that is not listed in a fieldset is rendered, ungrouped, after all
    of the declared ones, so adding a column to a model never silently drops it
    from the form.

    ???+ example
        ```python
        class UserAdmin(ModelView, model=User):
            form_fieldsets = [
                Fieldset(None, [User.name, User.email]),
                Fieldset(
                    "Permissions",
                    [User.is_admin, User.is_active],
                    description="Controls what this user is allowed to reach.",
                    collapsed=True,
                ),
            ]
        ```
    """

    title: str | None
    fields: Sequence[MODEL_ATTR] = field(default_factory=list)
    description: str | None = None
    collapsed: bool = False
    """Render the group behind a toggle, closed on page load."""

    classes: Sequence[str] = field(default_factory=list)
    """Extra CSS classes for the group wrapper."""

    @property
    def field_names(self) -> list[str]:
        return [f if isinstance(f, str) else f.key for f in self.fields]

    @property
    def wrapper_classes(self) -> list[str]:
        # ``collapse`` is consumed by ``collapsed``; passing it through would
        # hide the heading along with the body.
        return [c for c in self.classes if c != "collapse"]

    @classmethod
    def from_config(cls, entry: FieldsetConfig) -> Fieldset:
        """Accept either a `Fieldset` or Django's ``(title, options)`` tuple."""
        if isinstance(entry, Fieldset):
            return entry

        try:
            title, options = entry
            options = dict(options)
        except (TypeError, ValueError) as exc:
            raise InvalidModelError(
                "A fieldset must be a Fieldset or a (title, options) tuple, "
                f"got {entry!r}."
            ) from exc

        classes = list(options.get("classes", []))
        return cls(
            title=title,
            fields=list(options.get("fields", [])),
            description=options.get("description"),
            collapsed="collapse" in classes or bool(options.get("collapsed")),
            classes=classes,
        )


def normalize_fieldsets(
    fieldsets: Sequence[FieldsetConfig] | None,
) -> list[Fieldset]:
    return [Fieldset.from_config(entry) for entry in fieldsets or []]


@dataclass
class FieldGroup:
    """A resolved `Fieldset` together with the bound fields it renders."""

    fields: list[Any]
    title: str | None = None
    description: str | None = None
    collapsible: bool = False
    """Render behind a toggle."""

    collapsed: bool = False
    """Start closed. Always False when the group holds a validation error."""

    identifier: str = ""
    classes: list[str] = field(default_factory=list)


def _form_field_name(name: str, available: dict[str, Any]) -> str | None:
    """Map a model attribute name onto the form's field name.

    `get_model_form` renames attributes that collide with WTForms' own API
    (`data` becomes `data_`, and so on), so a fieldset naming the column has to
    be matched against the renamed field too.
    """
    if name in available:
        return name

    renamed = WTFORMS_ATTRS.get(name)
    if renamed is not None and renamed in available:
        return renamed

    return None


def _is_hidden(bound_field: Any) -> bool:
    """Mirror the template's ``f.widget.input_type != 'hidden'`` test.

    Not every widget declares ``input_type`` -- ``Select`` does not, for one.
    Jinja resolves the missing attribute to ``Undefined`` and treats the field
    as visible, so the Python port has to be equally forgiving.
    """
    return getattr(bound_field.widget, "input_type", None) == "hidden"


def group_form_fields(
    form: Form, fieldsets: Sequence[FieldsetConfig] | None
) -> list[FieldGroup]:
    """Split a bound form's visible fields into the groups to render."""
    visible = [f for f in form if not _is_hidden(f)]

    if not fieldsets:
        return [FieldGroup(fields=visible)]

    fieldsets = normalize_fieldsets(fieldsets)

    available = {f.name: f for f in visible}
    groups: list[FieldGroup] = []
    used: set[str] = set()

    for index, fieldset in enumerate(fieldsets):
        names = [
            resolved
            for resolved in (
                _form_field_name(name, available) for name in fieldset.field_names
            )
            if resolved is not None
        ]
        used.update(names)
        group_fields = [available[name] for name in names]

        # A collapsed group hiding a field that failed validation would hide
        # the error message with it, so re-open it. `errors` is only populated
        # once the form has been validated, so this is a no-op on a fresh GET.
        has_errors = any(getattr(f, "errors", None) for f in group_fields)

        groups.append(
            FieldGroup(
                fields=group_fields,
                title=fieldset.title,
                description=fieldset.description,
                collapsible=fieldset.collapsed,
                collapsed=fieldset.collapsed and not has_errors,
                identifier=f"form-fieldset-{index}",
                classes=fieldset.wrapper_classes,
            )
        )

    leftover = [f for f in visible if f.name not in used]
    if leftover:
        groups.append(
            FieldGroup(fields=leftover, identifier=f"form-fieldset-{len(fieldsets)}")
        )

    return groups


def validate_fieldsets(
    fieldsets: Sequence[FieldsetConfig] | None, form_class: type[Form]
) -> None:
    """Reject fieldsets naming unknown or repeated fields.

    Called once the form class is built. A typo would otherwise mean the field
    quietly never renders, which is the failure mode fieldsets exist to avoid.
    """
    if not fieldsets:
        return

    fieldsets = normalize_fieldsets(fieldsets)

    available = {
        name
        for name, value in form_class.__dict__.items()
        if isinstance(value, UnboundField)
    }

    unknown: list[str] = []
    duplicated: list[str] = []
    seen: set[str] = set()

    for fieldset in fieldsets:
        for name in fieldset.field_names:
            resolved = _form_field_name(name, dict.fromkeys(available))
            if resolved is None:
                unknown.append(name)
            elif resolved in seen:
                duplicated.append(name)
            else:
                seen.add(resolved)

    problems = []
    if unknown:
        problems.append(f"unknown field(s): {', '.join(sorted(set(unknown)))}")
    if duplicated:
        problems.append(
            f"field(s) in more than one fieldset: {', '.join(sorted(set(duplicated)))}"
        )

    if problems:
        raise InvalidModelError(
            f"Invalid fieldsets for {form_class.__name__}: {'; '.join(problems)}."
        )
