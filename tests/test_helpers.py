from sqladmin.helpers import secure_filename


def test_secure_filename(monkeypatch):
    assert secure_filename("My cool movie.mov") == "My_cool_movie.mov"
    assert secure_filename("../../../etc/passwd") == "etc_passwd"
    assert (
        secure_filename("i contain cool \xfcml\xe4uts.txt")
        == "i_contain_cool_umlauts.txt"
    )
    assert secure_filename("__filename__") == "filename"
    assert secure_filename("foo$&^*)bar") == "foobar"
