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


class PhoneNumberValidator:
    """Form validator for sqlalchemy_utils PhoneNumberType."""

    def __call__(self, form: Form, field: Field) -> None:
        from sqlalchemy_utils import PhoneNumber, PhoneNumberParseException

        try:
            PhoneNumber(field.data)
        except PhoneNumberParseException:
            raise ValidationError("Not a valid phone number.")


class ColorValidator:
    """General Color validator using `colour` package."""

    def __call__(self, form: Form, field: Field) -> None:
        from colour import Color

        try:
            Color(field.data)
        except ValueError:
            raise ValidationError('Not a valid color (e.g. "red", "#f00", "#ff0000").')


class TimezoneValidator:
    """Form validator for sqlalchemy_utils TimezoneType."""

    def __init__(self, coerce_function: Callable[[Any], Any]) -> None:
        self.coerce_function = coerce_function

    def __call__(self, form: Form, field: Field) -> None:
        try:
            self.coerce_function(str(field.data))
        except Exception:
            raise ValidationError("Not a valid timezone (e.g. 'Asia/Singapore').")
