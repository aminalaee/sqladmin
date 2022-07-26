from typing import Any, Callable

from wtforms import Field, Form, ValidationError


class CurrencyValidator:
    """Form validator for sqlalchemy_utils CurrencyType."""

    def __call__(self, form: Form, field: Field) -> None:
        from sqlalchemy_utils import Currency

        try:
            Currency(field.data)
        except (TypeError, ValueError):
            raise ValidationError("Not a valid ISO currency code (e.g. USD, EUR, CNY).")


class TimezoneValidator:
    """Form validator for sqlalchemy_utils TimezoneType."""

    def __init__(self, coerce_function: Callable[[Any], Any]) -> None:
        self.coerce_function = coerce_function

    def __call__(self, form: Form, field: Field) -> None:
        try:
            self.coerce_function(str(field.data))
        except Exception:
            raise ValidationError("Not a valid timezone (e.g. 'Asia/Singapore').")
