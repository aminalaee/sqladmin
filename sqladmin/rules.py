"""
Credit to Flask-Admin forms/rules.py
"""

from typing import Generator, TypeVar

from markupsafe import Markup
from wtforms import Form

from sqladmin.forms import FormOpts

T = TypeVar("T")


class BaseRule:
    """
    Base form rule. All form formatting rules should derive from `BaseRule`.
    """

    def __init__(self) -> None:
        self.parent: "BaseRule"
        self.rule_set: "RuleSet"

    def configure(self: T, rule_set: "RuleSet", parent: T) -> T:
        self.parent = parent
        self.rule_set = rule_set
        return self

    @property
    def visible_fields(self) -> list:
        """
        A list of visible fields for the given rule.
        """
        return []

    def __call__(
        self, form: Form, form_opts: FormOpts | None = None, field_args: dict = {}
    ) -> None:
        """
        Render rule.

        :param form:
            Form object
        :param form_opts:
            Form options
        :param field_args:
            Optional arguments that should be passed to template or the field
        """
        raise NotImplementedError()


class NestedRule(BaseRule):
    """Nested rule. Can contain child rules and render them."""

    def __init__(self, rules: list["RuleSet"] = [], separator: str = ""):
        super().__init__()
        self.rules = list(rules)
        self.separator = separator

    def configure(self, rule_set: "RuleSet", parent: T) -> T:
        self.rules = rule_set.configure_rules(self.rules, self)
        return super().configure(rule_set, parent)

    @property
    def visible_fields(self):
        """
        Return visible fields for all child rules.
        """
        visible_fields = []
        for rule in self.rules:
            for field in rule.visible_fields:
                visible_fields.append(field)
        return visible_fields

    def __iter__(self):
        """
        Return rules.
        """
        return self.rules

    def __call__(self, form, form_opts=None, field_args={}):
        """
        Render all children.

        :param form:
            Form object
        :param form_opts:
            Form options
        :param field_args:
            Optional arguments that should be passed to template or the field
        """
        result = []

        for r in self.rules:
            result.append(str(r(form, form_opts, field_args)))

        return Markup(self.separator.join(result))


class Field(BaseRule):
    def __init__(self, field_name):
        super().__init__()
        self.field_name = field_name

    @property
    def visible_fields(self):
        return [self.field_name]

    def __call__(self, form, form_opts=None, field_args={}):
        field = getattr(form, self.field_name, None)

        if field is None:
            raise ValueError("Form %s does not have field %s" % (form, self.field_name))

        opts = {}

        if form_opts:
            opts.update(form_opts.widget_args.get(self.field_name, {}))

        opts.update(field_args)

        return field(**opts)


class Row(NestedRule):
    def __init__(self, *columns, **kw):
        super().__init__()
        self.rules = columns

    def __call__(self, form, form_opts=None, field_args={}):
        cols = []
        for col in self.rules:
            # if col.visible_fields:
            #     w_args = form_opts.widget_args.setdefault(col.visible_fields[0], {})
            #     w_args.setdefault('column_class', 'col')
            cols.append(col(form, form_opts, field_args))

        return Markup('<div class="form-row">%s</div>' % "".join(cols))


class RuleSet:
    def __init__(self, view, rules):
        self.view = view
        self.rules = self.configure_rules(rules)

    @property
    def visible_fields(self):
        visible_fields = []
        for rule in self.rules:
            for field in rule.visible_fields:
                visible_fields.append(field)
        return visible_fields

    def convert_string(self, value):
        return Field(value)

    def configure_rules(self, rules: "RuleSet", parent: "RuleSet"):
        """
        Configure all rules recursively - bind them to current RuleSet and
        convert string references to `Field` rules.

        :param rules:
            Rule list
        :param parent:
            Parent rule (if any)
        """
        result = []

        for r in rules:
            if isinstance(r, str):
                result.append(self.convert_string(r).configure(self, parent))
            elif isinstance(r, (tuple, list)):
                row = Row(*r)
                result.append(row.configure(self, parent))
            else:
                try:
                    result.append(r.configure(self, parent))
                except AttributeError:
                    raise TypeError('Could not convert "%s" to rule' % repr(r))

        return result

    def __iter__(self) -> Generator[None, None, None]:
        for r in self.rules:
            yield r
