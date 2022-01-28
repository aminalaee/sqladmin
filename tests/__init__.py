from sqladmin.auth.utils.token import create_access_token


def get_test_token(username: str) -> str:
    return create_access_token({"username": username})
