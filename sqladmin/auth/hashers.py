import binascii
import hashlib

from sqladmin.conf import settings

SECRET_KEY = settings.SECRET_KEY


def make_password(raw_password: str) -> str:
    password = hashlib.pbkdf2_hmac(
        "sha256", raw_password.encode("utf-8"), SECRET_KEY.encode("utf-8"), 16
    )
    return binascii.hexlify(password).decode()


def verify_password(raw_password: str, password: str) -> bool:
    random_salt = SECRET_KEY.encode("utf-8")
    raw_password_bytes = hashlib.pbkdf2_hmac(
        "sha256", raw_password.encode("utf-8"), random_salt, 16
    )
    if binascii.hexlify(raw_password_bytes).decode() == password:
        return True
    else:
        return False
