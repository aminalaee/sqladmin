from typing import TYPE_CHECKING, Any, Dict

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from sqladmin.helpers import get_direction, get_primary_key

if TYPE_CHECKING:
    from sqladmin.models import ModelAdmin


def insert_sync(model_admin: "ModelAdmin", data: Dict[str, Any]) -> None:
    obj = model_admin.model()

    with model_admin.sessionmaker() as session:
        for key, value in data.items():
            relation = model_admin._mapper.relationships.get(key)
            if relation:
                if get_direction(relation) in ["ONETOMANY", "MANYTOMANY"]:
                    target = relation.mapper.class_
                    target_pk = get_primary_key(target)
                    related_stmt = select(target).where(target_pk.in_(value))
                    related_objs = session.execute(related_stmt).scalars().all()
                    setattr(obj, key, related_objs)
                elif get_direction(relation) == "ONETOONE":
                    target = relation.mapper.class_
                    target_pk = get_primary_key(target)
                    related_stmt = select(target).where(target_pk == value)
                    related_obj = session.execute(related_stmt).scalars().first()
                    setattr(obj, key, related_obj)
                else:
                    fk = relation.local_remote_pairs[0][0]
                    setattr(obj, fk.name, value)
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
                if get_direction(relation) in ["ONETOMANY", "MANYTOMANY"]:
                    target = relation.mapper.class_
                    target_pk = get_primary_key(target)
                    related_stmt = select(target).where(target_pk.in_(value))
                    result = await session.execute(related_stmt)
                    related_objs = result.scalars().all()
                    setattr(obj, key, related_objs)
                elif get_direction(relation) == "ONETOONE":
                    target = relation.mapper.class_
                    target_pk = get_primary_key(target)
                    related_stmt = select(target).where(target_pk == value)
                    result = await session.execute(related_stmt)
                    related_obj = result.scalars().first()
                    setattr(obj, key, related_obj)
                else:
                    fk = relation.local_remote_pairs[0][0]
                    setattr(obj, fk.name, value)
            else:
                setattr(obj, key, value)

        session.add(obj)
        await session.commit()


def update_sync(model_admin: "ModelAdmin", pk: Any, data: Dict[str, Any]) -> None:
    pk = model_admin._get_column_python_type(model_admin.pk_column)(pk)
    stmt = select(model_admin.model).where(model_admin.pk_column == pk)

    relationships = model_admin._mapper.relationships

    with model_admin.sessionmaker() as session:
        obj = session.execute(stmt).scalars().first()
        for key, value in data.items():
            relation = relationships.get(key)
            if relation:
                if get_direction(relation) in ["ONETOMANY", "MANYTOMANY"]:
                    target = relation.mapper.class_
                    target_pk = get_primary_key(target)
                    related_stmt = select(target).where(target_pk.in_(value))
                    related_objs = session.execute(related_stmt).scalars().all()
                    setattr(obj, key, related_objs)
                elif get_direction(relation) == "ONETOONE":
                    target = relation.mapper.class_
                    target_pk = get_primary_key(target)
                    related_stmt = select(target).where(target_pk == value)
                    related_obj = session.execute(related_stmt).scalars().first()
                    setattr(obj, key, related_obj)
                else:
                    fk = relation.local_remote_pairs[0][0]
                    setattr(obj, fk.name, value)
            else:
                setattr(obj, key, value)

        session.commit()


async def update_async(
    model_admin: "ModelAdmin", pk: Any, data: Dict[str, Any]
) -> None:
    pk = model_admin._get_column_python_type(model_admin.pk_column)(pk)
    stmt = select(model_admin.model).where(model_admin.pk_column == pk)

    for relation in model_admin._relations:
        stmt = stmt.options(joinedload(relation.key))

    async with model_admin.sessionmaker() as session:
        result = await session.execute(stmt)
        obj = result.scalars().first()
        for key, value in data.items():
            relation = model_admin._mapper.relationships.get(key)
            if relation:
                if get_direction(relation) in ["ONETOMANY", "MANYTOMANY"]:
                    target = relation.mapper.class_
                    target_pk = get_primary_key(target)
                    related_stmt = select(target).where(target_pk.in_(value))
                    result = await session.execute(related_stmt)
                    related_objs = result.scalars().all()
                    setattr(obj, key, related_objs)
                elif get_direction(relation) == "ONETOONE":
                    target = relation.mapper.class_
                    target_pk = get_primary_key(target)
                    related_stmt = select(target).where(target_pk == value)
                    result = await session.execute(related_stmt)
                    related_obj = result.scalars().first()
                    setattr(obj, key, related_obj)
                else:
                    fk = relation.local_remote_pairs[0][0]
                    setattr(obj, fk.name, value)
            else:
                setattr(obj, key, value)

        await session.commit()


def delete_sync(model_admin: "ModelAdmin", obj: Any) -> None:
    with model_admin.sessionmaker() as session:
        session.delete(obj)
        session.commit()


async def delete_async(model_admin: "ModelAdmin", obj: Any) -> None:
    async with model_admin.sessionmaker.begin() as session:
        await session.delete(obj)
