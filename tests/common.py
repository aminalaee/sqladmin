import os
from typing import Any, List

TEST_DATABASE_URI_SYNC = os.environ.get("TEST_DATABASE_URI_SYNC", "sqlite:///test.db")
TEST_DATABASE_URI_ASYNC = os.environ.get(
    "TEST_DATABASE_URI_ASYNC", "sqlite+aiosqlite:///test.db"
)


class DummyData(dict):  # pragma: no cover
    def getlist(self, key: str) -> List[Any]:
        v = self[key]
        if not isinstance(v, (list, tuple)):
            v = [v]
        return v
