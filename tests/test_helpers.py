from datetime import timedelta

from sqladmin.helpers import is_falsy_value, parse_interval, secure_filename


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
