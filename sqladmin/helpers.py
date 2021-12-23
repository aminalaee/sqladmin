from typing import Union


def as_str(s: Union[str, bytes]) -> str:
    if isinstance(s, bytes):
        return s.decode("utf-8")

    return str(s)
