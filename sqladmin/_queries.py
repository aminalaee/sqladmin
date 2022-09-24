from re import L
from typing import TYPE_CHECKING, Any, Dict, List

import anyio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.sql.expression import Select

from sqladmin._types import MODEL_ATTR_TYPE
from sqladmin.helpers import get_column_python_type, get_direction, get_primary_key

if TYPE_CHECKING:
    from sqladmin.models import ModelView


class Query:
    def __init__(self, model_view: "ModelView") -> None:
        self.model_view = model_view

    def _get_to_many_stmt(self, relation: MODEL_ATTR_TYPE, values: List[Any]) -> Select:
        target = relation.mapper.class_
        target_pk = get_primary_key(target)
        target_pk_type = get_column_python_type(target_pk)
        pk_values = [target_pk_type(value) for value in values]
        related_stmt = select(target).where(target_pk.in_(pk_values))
        return related_stmt

    def _get_to_one_stmt(self, relation: MODEL_ATTR_TYPE, value: Any) -> Select:
        target = relation.mapper.class_
        target_pk = get_primary_key(target)
        target_pk_type = get_column_python_type(target_pk)
        related_stmt = select(target).where(target_pk == target_pk_type(value))
        return related_stmt

    def _set_many_to_one(self, obj: Any, relation: MODEL_ATTR_TYPE, value: Any) -> Any:
        fk = relation.local_remote_pairs[0][0]
        fk_type = get_column_python_type(fk)
        setattr(obj, fk.name, fk_type(value))
        return obj

    def _set_attributes_sync(self, session: Session, obj: Any, data: dict) -> Any:
        for key, value in data.items():
            column = self.model_view._mapper.columns.get(key)
            relation = self.model_view._mapper.relationships.get(key)

            if not value:
                # Set falsy values to None, if column is Nullable
                if not relation and column.nullable and value is not False:
                    value = None

                setattr(obj, key, value)
                continue

            relation = self.model_view._mapper.relationships.get(key)
            if relation:
                direction = get_direction(relation)
                if direction in ["ONETOMANY", "MANYTOMANY"]:
                    related_stmt = self._get_to_many_stmt(relation, value)
                    related_objs = session.execute(related_stmt).scalars().all()
                    setattr(obj, key, related_objs)
                elif direction == "ONETOONE":
                    related_stmt = self._get_to_one_stmt(relation, value)
                    related_obj = session.execute(related_stmt).scalars().first()
                    setattr(obj, key, related_obj)
                else:
                    obj = self._set_many_to_one(obj, relation, value)
            else:
                setattr(obj, key, value)

        return obj

    async def _set_attributes_async(
        self, session: AsyncSession, obj: Any, data: dict
    ) -> Any:
        for key, value in data.items():
            column = self.model_view._mapper.columns.get(key)
            relation = self.model_view._mapper.relationships.get(key)

            if not value:
                # Set falsy values to None, if column is Nullable
                if not relation and column.nullable and value is not False:
                    value = None

                setattr(obj, key, value)
                continue

            if relation:
                direction = get_direction(relation)
                if direction in ["ONETOMANY", "MANYTOMANY"]:
                    related_stmt = self._get_to_many_stmt(relation, value)
                    result = await session.execute(related_stmt)
                    related_objs = result.scalars().all()
                    setattr(obj, key, related_objs)
                elif direction == "ONETOONE":
                    related_stmt = self._get_to_one_stmt(relation, value)
                    result = await session.execute(related_stmt)
                    related_obj = result.scalars().first()
                    setattr(obj, key, related_obj)
                else:
                    obj = self._set_many_to_one(obj, relation, value)
            else:
                setattr(obj, key, value)
        return obj

    def _update_sync(self, pk: Any, data: Dict[str, Any]) -> None:
        pk = get_column_python_type(self.model_view.pk_column)(pk)
        stmt = select(self.model_view.model).where(self.model_view.pk_column == pk)

        with self.model_view.sessionmaker() as session:
            obj = session.execute(stmt).scalars().first()
            obj = self._set_attributes_sync(session, obj, data)
            session.commit()

    async def _update_async(self, pk: Any, data: Dict[str, Any]) -> None:
        pk = get_column_python_type(self.model_view.pk_column)(pk)
        stmt = select(self.model_view.model).where(self.model_view.pk_column == pk)

        for relation in self.model_view._relations:
            stmt = stmt.options(joinedload(relation.key))

        async with self.model_view.sessionmaker() as session:
            result = await session.execute(stmt)
            obj = result.scalars().first()
            obj = await self._set_attributes_async(session, obj, data)
            await session.commit()

    def _delete_sync(self, obj: Any) -> None:
        with self.model_view.sessionmaker() as session:
            session.delete(obj)
            session.commit()

    async def _delete_async(self, obj: Any) -> None:
        async with self.model_view.sessionmaker() as session:
            await session.delete(obj)
            await session.commit()

    def _insert_sync(self, data: Dict[str, Any]) -> None:
        obj = self.model_view.model()

        with self.model_view.sessionmaker() as session:
            obj = self._set_attributes_sync(session, obj, data)
            session.add(obj)
            session.commit()

    async def _insert_async(self, data: Dict[str, Any]) -> None:
        obj = self.model_view.model()

        async with self.model_view.sessionmaker() as session:
            obj = await self._set_attributes_async(session, obj, data)
            session.add(obj)
            await session.commit()

    async def delete(self, obj: Any) -> None:
        if self.model_view.async_engine:
            await self._delete_async(obj)
        else:
            await anyio.to_thread.run_sync(self._delete_sync, obj)

    async def insert(self, data: dict) -> None:
        if self.model_view.async_engine:
            await self._insert_async(data)
        else:
            await anyio.to_thread.run_sync(self._insert_sync, data)

    async def update(self, pk: Any, data: dict) -> None:
        if self.model_view.async_engine:
            await self._update_async(pk, data)
        else:
            await anyio.to_thread.run_sync(self._update_sync, pk, data)
