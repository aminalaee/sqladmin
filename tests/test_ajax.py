from typing import Any, AsyncGenerator

import pytest
from httpx import AsyncClient
from sqlalchemy import Column, ForeignKey, Integer, String, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, selectinload, sessionmaker
from starlette.applications import Starlette

from sqladmin import Admin, ModelView
from sqladmin.ajax import create_ajax_loader
from tests.common import async_engine as engine

pytestmark = pytest.mark.anyio

Base = declarative_base()  # type: Any

LocalSession = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

session: AsyncSession = LocalSession()

app = Starlette()
admin = Admin(app=app, engine=engine)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String(length=16))

    addresses = relationship("Address", back_populates="user")

    def __str__(self) -> str:
        return f"User {self.id}"


class Address(Base):
    __tablename__ = "addresses"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    user = relationship("User", back_populates="addresses")

    def __str__(self) -> str:
        return f"Address {self.id}"


class UserAdmin(ModelView, model=User):
    form_ajax_refs = {
        "addresses": {
            "fields": ("id",),
        }
    }


class AddressAdmin(ModelView, model=Address):
    form_ajax_refs = {
        "user": {
            "fields": ("name",),
            "order_by": ("id"),
        }
    }


admin.add_view(UserAdmin)
admin.add_view(AddressAdmin)


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


async def test_ajax_lookup_invalid_query_params(client: AsyncClient) -> None:
    response = await client.get("/admin/user/ajax/lookup")
    assert response.status_code == 400

    response = await client.get("/admin/address/ajax/lookup")
    assert response.status_code == 400

    response = await client.get("/admin/user/ajax/lookup?name=test&term=x")
    assert response.status_code == 400


async def test_ajax_response(client: AsyncClient) -> None:
    user = User(name="John Snow")
    async with LocalSession() as s:
        s.add(user)
        await s.commit()

    response = await client.get("/admin/address/ajax/lookup?name=user&term=john")

    assert response.status_code == 200
    assert response.json() == {"results": [{"id": 1, "text": "User 1"}]}


async def test_create_ajax_loader_exceptions() -> None:
    with pytest.raises(ValueError):
        create_ajax_loader(model_admin=AddressAdmin(), name="x", options={})

    with pytest.raises(ValueError):
        create_ajax_loader(model_admin=AddressAdmin(), name="user", options={})


async def test_create_page_template(client: AsyncClient) -> None:
    response = await client.get("/admin/user/create")

    assert response.text.count('data-json="[]"') == 1
    assert response.text.count('data-role="select2-ajax"') == 1
    assert response.text.count('data-url="/admin/user/ajax/lookup"') == 1

    response = await client.get("/admin/address/create")

    assert response.text.count('data-role="select2-ajax"') == 1
    assert response.text.count('data-url="/admin/address/ajax/lookup"') == 1


async def test_edit_page_template(client: AsyncClient) -> None:
    user = User(name="John Snow")
    async with LocalSession() as s:
        s.add(user)
        await s.flush()

        address = Address(user=user)
        s.add(address)
        await s.commit()

    response = await client.get("/admin/user/edit/1")
    assert (
        response.text.count(
            'data-json="[{&#34;id&#34;: 1, &#34;text&#34;: &#34;Address 1&#34;}]"'
        )
        == 1
    )
    assert response.text.count('data-role="select2-ajax"') == 1
    assert response.text.count('data-url="/admin/user/ajax/lookup"') == 1

    response = await client.get("/admin/address/edit/1")
    assert (
        response.text.count(
            'data-json="[{&#34;id&#34;: 1, &#34;text&#34;: &#34;User 1&#34;}]"'
        )
        == 1
    )
    assert response.text.count('data-role="select2-ajax"') == 1
    assert response.text.count('data-url="/admin/address/ajax/lookup"') == 1


async def test_crete_and_edit_forms(client: AsyncClient) -> None:
    response = await client.post("/admin/address/create", data={})
    assert response.status_code == 302

    data = {"addresses": ["1"], "name": "Tyrion"}
    response = await client.post("/admin/user/create", data=data)
    assert response.status_code == 302

    data = {}
    response = await client.post("/admin/address/edit/1", data=data)
    assert response.status_code == 302

    async with LocalSession() as s:
        stmt = select(User).options(selectinload(User.addresses))
        result = await s.execute(stmt)

    user = result.scalar_one()
    assert len(user.addresses) == 0

    data = {"addresses": ["1"]}
    response = await client.post("/admin/user/edit/1", data=data)
    assert response.status_code == 302

    async with LocalSession() as s:
        stmt = select(User).options(selectinload(User.addresses))
        result = await s.execute(stmt)

    user = result.scalar_one()
    assert len(user.addresses) == 1
