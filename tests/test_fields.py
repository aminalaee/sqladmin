from datetime import date, datetime
from typing import Any, Generator

import pytest
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker
from wtforms import Form

from sqladmin.fields import (
    DateField,
    DateTimeField,
    JSONField,
    QuerySelectField,
    QuerySelectMultipleField,
    Select2TagsField,
    SelectField,
    TimeField,
)
from tests.common import DummyData, sync_engine as engine

Base = declarative_base()  # type: Any

LocalSession = sessionmaker(bind=engine)

session: Session = LocalSession()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String)


@pytest.fixture(autouse=True, scope="function")
def prepare_database() -> Generator[None, None, None]:
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


def test_date_field() -> None:
    class F(Form):
        date = DateField()

    form = F()
    assert form.date.format == ["%Y-%m-%d"]

    assert 'data-role="datepicker"' in form.date()
    assert 'data-date-format="YYYY-MM-DD"' in form.date()

    form = F(DummyData(date=["2021-12-22"]))
    assert form.date.data == date(2021, 12, 22)


def test_datetime_field() -> None:
    class F(Form):
        datetime = DateTimeField()

    form = F()
    assert form.datetime.format == "%Y-%m-%d %H:%M:%S"

    assert 'data-role="datetimepicker"' in form.datetime()
    assert 'data-date-format="YYYY-MM-DD HH:mm:ss"' in form.datetime()

    form = F(DummyData(datetime=["2021-12-22 12:30:00"]))
    assert form.datetime.data == datetime(2021, 12, 22, 12, 30, 0, 0)


def test_time_field() -> None:
    class F(Form):
        time = TimeField()

    form = F()
    assert form.time.default_format == "%H:%M:%S"
    assert 'data-role="timepicker"' in form.time()
    assert 'data-date-format="HH:mm:ss"' in form.time()

    form = F(DummyData(time=["12:30:00"]))
    assert form.time.data == datetime(2021, 12, 22, 12, 30, 0, 0).time()
    assert 'data-date-format="HH:mm:ss"' in form.time()

    form = F(DummyData(time=["12:30"]))
    form.time.raw_data = None
    assert form.time.data == datetime(2021, 12, 22, 12, 30, 0, 0).time()
    assert 'data-date-format="HH:mm:ss"' in form.time()

    form = F(DummyData(time=["12:30:00 AM"]))
    assert form.time.data == datetime(2021, 12, 22, 0, 30, 0, 0).time()

    form = F(DummyData(time=["12:30 AM"]))
    assert form.time.data == datetime(2021, 12, 22, 0, 30, 0, 0).time()

    form = F(DummyData(time=["Invalid"]))
    assert form.time.data is None

    form = F(DummyData(time=[""]))
    assert form.time.data is None


def test_json_field() -> None:
    class F(Form):
        json = JSONField()

    form = F()
    assert form.json() == """<textarea id="json" name="json">\r\n{}</textarea>"""

    form = F(DummyData(json=[""]))
    assert form.json.data is None

    form = F(DummyData(json=['{"a": 1}']))
    assert form.json.data == {"a": 1}
    assert (
        form.json()
        == """<textarea id="json" name="json">\r\n{&#34;a&#34;: 1}</textarea>"""
    )

    form = F(DummyData(json=["""'{"A": 10}'"""]))
    assert form.json.data is None


def test_select_field() -> None:
    class F(Form):
        select = SelectField(
            choices=[(1, "A"), (2, "B")],
            coerce=int,
        )

    form = F()
    assert '<option value="1">A</option><option value="2">B</option>' in form.select()

    form = F(DummyData(select=["1"]))
    assert form.validate() is True
    assert form.select.data == 1

    form = F(DummyData(select=["A"]))
    assert form.validate() is False
    assert form.select.data is None

    class F(Form):  # type: ignore
        select = SelectField(coerce=int, allow_blank=True)

    form = F()
    assert '<option selected value="__None">' in form.select()
    assert form.validate() is True

    form = F(DummyData(select=["__None"]))
    assert form.select.data is None


def test_select2_tags_field() -> None:
    class F(Form):
        select = Select2TagsField(coerce=int)

    form = F(DummyData(select=["1"]))
    assert form.select.data == 1
    assert 'data-role="select2-tags"' in form.select()
    assert 'value="1"' in form.select()

    form = F(DummyData(select=["A"]))
    assert form.select.data is None

    class F(Form):  # type: ignore
        select = Select2TagsField(coerce=int, save_as_list=True)

    form = F(DummyData(select=["1"]))
    assert form.select.data == [1]
    assert 'value="1"' in form.select()

    form = F()
    assert 'value=""' in form.select()


def test_query_select_field() -> None:
    object_list = [(str(i), User(id=i)) for i in range(5)]

    class F(Form):
        select = QuerySelectField(object_list=object_list, get_label="__doc__")

    form = F(DummyData(select=["1"]))
    form.select._object_list = []
    assert form.validate() is False

    class F(Form):  # type: ignore
        select = QuerySelectField(
            object_list=object_list,
            allow_blank=True,
        )

    form = F(DummyData(select=["__None"]))
    assert form.validate() is True

    class F(Form):  # type: ignore
        select = QuerySelectField()

    form = F(DummyData(select=["1"]))
    assert form.validate() is False


def test_query_select_multiple_field() -> None:
    object_list = [(str(i), User(id=i)) for i in range(5)]

    class F(Form):
        select = QuerySelectMultipleField(allow_blank=True, object_list=object_list)

    form = F()
    assert form.validate() is True

    form = F(DummyData(select=["1"]))
    form.select._object_list = object_list
    assert form.validate() is True

    form = F(DummyData(select=["100"]))
    form.select._object_list = object_list
    assert form.select.data == []
    assert form.validate() is False
