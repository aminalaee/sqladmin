from datetime import timedelta
from typing import Any

import pytest
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base

from sqladmin.helpers import (
    get_object_identifier,
    is_falsy_value,
    object_identifier_values,
    parse_interval,
    secure_filename,
    slugify_action_name,
)

Base: Any = declarative_base()


def test_secure_filename(monkeypatch):
    assert secure_filename("My cool movie.mov") == "My_cool_movie.mov"
    assert secure_filename("../../../etc/passwd") == "etc_passwd"
    assert (
        secure_filename("i contain cool \xfcml\xe4uts.txt")
        == "i_contain_cool_umlauts.txt"
    )
    assert secure_filename("__filename__") == "filename"
    assert secure_filename("foo$&^*)bar") == "foobar"


def test_parse_interval():
    assert parse_interval("1 day") == timedelta(days=1)
    assert parse_interval("-1 day") == timedelta(days=-1)
    assert parse_interval("1.10000") == timedelta(seconds=1, microseconds=100000)
    assert parse_interval("P3DT01H00M00S") == timedelta(days=3, seconds=3600)


def test_is_falsy_values():
    assert is_falsy_value(None) is True
    assert is_falsy_value("") is True
    assert is_falsy_value(0) is False
    assert is_falsy_value("example") is False


def test_slugify_action_name():
    assert slugify_action_name("custom action") == "custom-action"

    with pytest.raises(ValueError):
        slugify_action_name("custom action !@#$%")


class Person(Base):
    __tablename__ = "users"

    family_id = Column(String, ForeignKey("family.id"), primary_key=True)
    member_id = Column(Integer, primary_key=True)
    version = Column(String, primary_key=True)


def person(family_id, member_id, version):
    return Person(family_id=family_id, member_id=member_id, version=version)


class Family(Base):
    __tablename__ = "family"
    id = Column(String, primary_key=True)


class Profile(Base):
    __tablename__ = "profile"
    id = Column(Integer, primary_key=True)


def test_single_pk_identifier():
    assert get_object_identifier(Family(id="test")) == "test"
    assert get_object_identifier(Family(id="C:\\Files\\")) == "C:\\Files\\"
    assert get_object_identifier(Family(id=r"1;2\;3")) == r"1;2\;3"

    assert get_object_identifier(Profile(id=0)) == 0
    assert get_object_identifier(Profile(id=3217)) == 3217


def test_single_pk_id_values():
    assert object_identifier_values("test", Family) == ("test",)
    assert object_identifier_values("C:\\Files\\", Family) == ("C:\\Files\\",)
    assert object_identifier_values(r"1;2\;3", Family) == (r"1;2\;3",)

    assert object_identifier_values(str(0), Profile) == (0,)
    assert object_identifier_values(str(3217), Profile) == (3217,)


def test_multi_pk_identifier():
    assert get_object_identifier(person("Johnson", 7, "A")) == "Johnson;7;A"
    assert (
        get_object_identifier(person("C:\\Files\\", 404, "F")) == r"C:\\Files\\;404;F"
    )
    assert get_object_identifier(person(r"1;2\;3", 201, "S")) == r"1\;2\\\;3;201;S"
    assert get_object_identifier(person("Doe", 3, "\\")) == "Doe;3;\\\\"
    assert get_object_identifier(person("", 1, "")) == ";1;"


def test_multi_pk_id_values():
    def id_values(ident):
        return object_identifier_values(ident, Person)

    assert id_values("Johnson;7;A") == ("Johnson", 7, "A")
    assert id_values(r"C:\\Files\\;404;F") == ("C:\\Files\\", 404, "F")
    assert id_values(r"1\;2\\\;3;201;S") == (r"1;2\;3", 201, "S")
    assert id_values("Doe;3;\\\\") == ("Doe", 3, "\\")
    assert id_values(";1;") == ("", 1, "")


def test_catch_malformed_id():
    def test_case(ident):
        with pytest.raises(ValueError):
            object_identifier_values(ident, Person)

    test_case("Missing;1")
    test_case("Johnson;7;A;Extra")
