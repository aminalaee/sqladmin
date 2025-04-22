from typing import Any, Generator

import pytest
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from starlette.applications import Starlette
from starlette.testclient import TestClient

from sqladmin import Admin, ModelView
from tests.common import sync_engine as engine

Base = declarative_base()
SessionLocal = sessionmaker(bind=engine)  # Create a sessionmaker instance

app = Starlette()
admin = Admin(app=app, engine=engine)  # Initialize Admin for testing


class Table1(Base):
    __tablename__ = "table1"

    id = Column(Integer, primary_key=True)
    field1 = Column(String, nullable=False)

    def __repr__(self) -> str:
        return f"<Table1(id={self.id}, field1={self.field1})>"


class Table2(Base):
    __tablename__ = "table2"

    id = Column(Integer, primary_key=True)
    field2 = Column(String, nullable=False)
    table1_id = Column(Integer, ForeignKey("table1.id"), nullable=False)

    table1 = relationship("Table1", back_populates="table2s")

    def __repr__(self) -> str:
        return (
            f"<Table2(id={self.id}, field2={self.field2}, table1_id={self.table1_id})>"
        )


class Table3(Base):
    __tablename__ = "table3"

    id = Column(Integer, primary_key=True)
    table2_id = Column(Integer, ForeignKey("table2.id"), nullable=False)

    table2 = relationship("Table2", back_populates="table3s")

    def __repr__(self) -> str:
        return f"<Table3(id={self.id}, table2_id={self.table2_id})>"


Table1.table2s = relationship(
    "Table2", back_populates="table1", cascade="all, delete-orphan"
)
Table2.table3s = relationship(
    "Table3", back_populates="table2", cascade="all, delete-orphan"
)


class Table3Admin(ModelView, model=Table3):
    column_searchable_list = ["table2.table1.field1", "table2.field2"]


admin.add_view(Table3Admin)


@pytest.fixture
def prepare_database() -> Generator[None, None, None]:
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def client(prepare_database: Any) -> Generator[TestClient, None, None]:
    with TestClient(app=app, base_url="http://testserver") as c:
        yield c


def base_content():
    with SessionLocal() as session:
        # Add base data to the database
        t1 = Table1(id=1, field1="Field1_Value1")
        t2 = Table1(id=2, field1="Field1_Value2")

        table2_1 = Table2(id=1, field2="Field2_Value1", table1=t1)
        table2_2 = Table2(id=2, field2="Field2_Value2", table1=t2)

        table3_1 = Table3(id=1, table2=table2_1)
        table3_2 = Table3(id=2, table2=table2_2)

        session.add_all([t1, t2, table2_1, table2_2, table3_1, table3_2])
        session.commit()


@pytest.mark.parametrize(
    "term, expected, not_expected",
    [
        ("Field1_Value1", 1, 2),
        ("Field1_Value2", 2, 1),
        ("Field2_Value1", 1, 2),
        ("Field2_Value2", 2, 1),
    ],
)
def test_search_by_multiple_related_columns(
    client: TestClient, term: str, expected: int, not_expected: int
) -> None:
    base_content()
    response = client.get(f"/admin/table3/list?search={term}")
    assert response.status_code == 200

    assert (
        f'<a href="http://testserver/admin/table3/details/{not_expected}"'
        not in response.text
    )
    assert (
        f'<a href="http://testserver/admin/table3/details/{expected}"' in response.text
    )
