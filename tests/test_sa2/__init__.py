import pytest
from sqlalchemy import __version__ as __sa_version__

if __sa_version__.startswith("1."):
    pytest.skip("SQLAlchemy 1.4 does not support this api", allow_module_level=True)
