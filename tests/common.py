import os
from typing import Any, List

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine

test_database_uri_sync = os.environ.get("TEST_DATABASE_URI_SYNC", "sqlite:///test.db")
test_database_uri_async = os.environ.get(
    "TEST_DATABASE_URI_ASYNC", "sqlite+aiosqlite:///test.db"
)


connect_args = (
    {"check_same_thread": False} if "sqlite" in test_database_uri_sync else {}
)

sync_engine = create_engine(test_database_uri_sync, connect_args=connect_args)
async_engine = create_async_engine(test_database_uri_async, connect_args=connect_args)


class DummyData(dict):  # pragma: no cover
    def getlist(self, key: str) -> List[Any]:
        v = self[key]
        if not isinstance(v, (list, tuple)):
            v = [v]
        return v
