from typing import Tuple

import pytest


@pytest.fixture(scope="module")
def anyio_backend() -> Tuple[str, dict]:
    return ("asyncio", {"debug": True})
