from sqladmin.auth.utils.token import create_access_token


def get_test_token() -> str:
    return create_access_token({"user": "root"})
