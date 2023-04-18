from typing import Any, AsyncGenerator

import pytest
from httpx import AsyncClient
from sqlalchemy import Column, Integer, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy_fields.storages import FileSystemStorage, StorageFile
from sqlalchemy_fields.types import FileType, ImageType
from starlette.applications import Starlette

from sqladmin import Admin, ModelView
from tests.common import async_engine as engine

pytestmark = pytest.mark.anyio

Base = declarative_base()  # type: Any
LocalSession = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

app = Starlette()
admin = Admin(app=app, engine=engine)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    file = Column(FileType(FileSystemStorage(".uploads")))
    image = Column(ImageType(FileSystemStorage(".uploads")))


@pytest.fixture
async def prepare_database() -> AsyncGenerator[None, None]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def client(prepare_database: Any) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(app=app, base_url="http://testserver") as c:
        yield c


class UserAdmin(ModelView, model=User):
    ...


admin.add_view(UserAdmin)


async def _query_user() -> Any:
    stmt = select(User).limit(1)
    async with LocalSession() as s:
        result = await s.execute(stmt)
    return result.scalar_one()


async def test_create_form_fields(client: AsyncClient) -> None:
    response = await client.get("/admin/user/create")

    assert response.status_code == 200
    assert (
        '<input class="form-control" id="file" name="file" type="file">'
        in response.text
    )
    assert '<input class="form-check-input" type="checkbox"' in response.text
    assert (
        '<label class="form-check-label" for="file_checkbox">Clear</label>'
        in response.text
    )


async def test_create_form_post(client: AsyncClient) -> None:
    files = {"file": ("upload.txt", b"abc")}
    response = await client.post("/admin/user/create", files=files)

    user = await _query_user()

    assert response.status_code == 302
    assert isinstance(user.file, StorageFile) is True
    assert user.file.name == "upload.txt"
    assert user.file.path == ".uploads/upload.txt"


async def test_create_form_update(client: AsyncClient) -> None:
    files = {"file": ("upload.txt", b"abc")}
    response = await client.post("/admin/user/create", files=files)

    user = await _query_user()

    files = {"file": ("new_upload.txt", b"abc")}
    response = await client.post("/admin/user/edit/1", files=files)

    user = await _query_user()
    assert response.status_code == 302
    assert user.file.name == "new_upload.txt"
    assert user.file.path == ".uploads/new_upload.txt"

    files = {"file": ("empty.txt", b"")}
    response = await client.post("/admin/user/edit/1", files=files)

    user = await _query_user()
    assert user.file.name == "new_upload.txt"
    assert user.file.path == ".uploads/new_upload.txt"

    files = {"file": ("new_upload.txt", b"abc")}
    response = await client.post(
        "/admin/user/edit/1", files=files, data={"file_checkbox": True}
    )

    user = await _query_user()
    assert user.file is None
