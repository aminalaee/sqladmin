import pytest
from sqlalchemy import Column, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy_utils import (
    ColorType,
    CurrencyType,
    EmailType,
    IPAddressType,
    PhoneNumberType,
    TimezoneType,
    URLType,
    UUIDType,
)

from sqladmin.forms import get_model_form
from tests.common import DummyData, async_engine as engine

pytestmark = pytest.mark.anyio

Base = declarative_base()  # type: ignore


async def test_model_form_sqlalchemy_utils() -> None:
    class SQLAlchemyUtilsModel(Base):
        __tablename__ = "sqlalchemy_utils_model"

        id = Column(Integer, primary_key=True)
        email = Column(EmailType)
        ip = Column(IPAddressType)
        uuid = Column(UUIDType)
        url = Column(URLType)
        currency = Column(CurrencyType)
        timezone = Column(TimezoneType)
        phone = Column(PhoneNumberType)
        color = Column(ColorType)

    Form = await get_model_form(model=SQLAlchemyUtilsModel, engine=engine)
    data = DummyData(currency="IR", timezone=["Iran/Tehran"], color="bbb", phone="abc")
    form = Form(data)
    assert form.validate() is False
