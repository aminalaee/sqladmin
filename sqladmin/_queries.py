from typing import TYPE_CHECKING, Any, Dict, List

from sqlalchemy import select
from sqlalchemy.orm import joinedload
from sqlalchemy.sql.expression import Select

from sqladmin.helpers import get_column_python_type, get_direction, get_primary_key
from sqladmin.types import _MODEL_ATTR_TYPE

if TYPE_CHECKING:
    from sqladmin.models import ModelAdmin


def _get_to_many_stmt(relation: _MODEL_ATTR_TYPE, values: List[Any]) -> Select:
    target = relation.mapper.class_
    target_pk = get_primary_key(target)
    target_pk_type = get_column_python_type(target_pk)
    pk_values = [target_pk_type(value) for value in values]
    related_stmt = select(target).where(target_pk.in_(pk_values))
    return related_stmt


def _get_to_one_stmt(relation: _MODEL_ATTR_TYPE, value: Any) -> Select:
    target = relation.mapper.class_
    target_pk = get_primary_key(target)
    target_pk_type = get_column_python_type(target_pk)
    related_stmt = select(target).where(target_pk == target_pk_type(value))
    return related_stmt


def insert_sync(model_admin: "ModelAdmin", data: Dict[str, Any]) -> None:
    obj = model_admin.model()

    with model_admin.sessionmaker() as session:
        for key, value in data.items():
            relation = model_admin._mapper.relationships.get(key)
            if relation:
                direction = get_direction(relation)
                if direction in ["ONETOMANY", "MANYTOMANY"]:
                    related_stmt = _get_to_many_stmt(relation, value)
                    related_objs = session.execute(related_stmt).scalars().all()
                    setattr(obj, key, related_objs)
                elif direction == "ONETOONE":
                    if not value:
                        setattr(obj, key, value)
                        continue
                    related_stmt = _get_to_one_stmt(relation, value)
                    related_obj = session.execute(related_stmt).scalars().first()
                    setattr(obj, key, related_obj)
                else:
                    fk = relation.local_remote_pairs[0][0]
                    fk_type = get_column_python_type(fk)
                    setattr(obj, fk.name, fk_type(value))
            else:
                setattr(obj, key, value)

        session.add(obj)
        session.commit()


async def insert_async(model_admin: "ModelAdmin", data: Dict[str, Any]) -> None:
    obj = model_admin.model()

    async with model_admin.sessionmaker() as session:
        for key, value in data.items():
            relation = model_admin._mapper.relationships.get(key)
            if relation:
                direction = get_direction(relation)
                if direction in ["ONETOMANY", "MANYTOMANY"]:
                    related_stmt = _get_to_many_stmt(relation, value)
                    result = await session.execute(related_stmt)
                    related_objs = result.scalars().all()
                    setattr(obj, key, related_objs)
                elif direction == "ONETOONE":
                    if not value:
                        setattr(obj, key, value)
                        continue
                    related_stmt = _get_to_one_stmt(relation, value)
                    result = await session.execute(related_stmt)
                    related_obj = result.scalars().first()
                    setattr(obj, key, related_obj)
                else:
                    fk = relation.local_remote_pairs[0][0]
                    fk_type = get_column_python_type(fk)
                    setattr(obj, fk.name, fk_type(value))
            else:
                setattr(obj, key, value)

        session.add(obj)
        await session.commit()


def update_sync(model_admin: "ModelAdmin", pk: Any, data: Dict[str, Any]) -> None:
    pk = get_column_python_type(model_admin.pk_column)(pk)
    stmt = select(model_admin.model).where(model_admin.pk_column == pk)

    with model_admin.sessionmaker() as session:
        obj = session.execute(stmt).scalars().first()
        for key, value in data.items():
            relation = model_admin._mapper.relationships.get(key)
            if relation:
                direction = get_direction(relation)
                if direction in ["ONETOMANY", "MANYTOMANY"]:
                    related_stmt = _get_to_many_stmt(relation, value)
                    related_objs = session.execute(related_stmt).scalars().all()
                    setattr(obj, key, related_objs)
                elif direction == "ONETOONE":
                    if not value:
                        setattr(obj, key, value)
                        continue
                    related_stmt = _get_to_one_stmt(relation, value)
                    related_obj = session.execute(related_stmt).scalars().first()
                    setattr(obj, key, related_obj)
                else:
                    fk = relation.local_remote_pairs[0][0]
                    fk_type = get_column_python_type(fk)
                    setattr(obj, fk.name, fk_type(value))
            else:
                setattr(obj, key, value)

        session.commit()


async def update_async(
    model_admin: "ModelAdmin", pk: Any, data: Dict[str, Any]
) -> None:
    pk = get_column_python_type(model_admin.pk_column)(pk)
    stmt = select(model_admin.model).where(model_admin.pk_column == pk)

    for relation in model_admin._relations:
        stmt = stmt.options(joinedload(relation.key))

    async with model_admin.sessionmaker() as session:
        result = await session.execute(stmt)
        obj = result.scalars().first()
        for key, value in data.items():
            relation = model_admin._mapper.relationships.get(key)
            if relation:
                direction = get_direction(relation)
                if direction in ["ONETOMANY", "MANYTOMANY"]:
                    related_stmt = _get_to_many_stmt(relation, value)
                    result = await session.execute(related_stmt)
                    related_objs = result.scalars().all()
                    setattr(obj, key, related_objs)
                elif direction == "ONETOONE":
                    if not value:
                        setattr(obj, key, value)
                        continue
                    related_stmt = _get_to_one_stmt(relation, value)
                    result = await session.execute(related_stmt)
                    related_obj = result.scalars().first()
                    setattr(obj, key, related_obj)
                else:
                    fk = relation.local_remote_pairs[0][0]
                    fk_type = get_column_python_type(fk)
                    setattr(obj, fk.name, fk_type(value))
            else:
                setattr(obj, key, value)

        await session.commit()


def delete_sync(model_admin: "ModelAdmin", obj: Any) -> None:
    with model_admin.sessionmaker() as session:
        session.delete(obj)
        session.commit()


async def delete_async(model_admin: "ModelAdmin", obj: Any) -> None:
    async with model_admin.sessionmaker() as session:
        await session.delete(obj)
        await session.commit()
