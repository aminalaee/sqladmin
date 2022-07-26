from typing import TYPE_CHECKING

from sqlalchemy import String, and_, cast, or_, select, text

from sqladmin.helpers import (
    get_primary_key,
    is_association_proxy,
    is_relationship,
)

if TYPE_CHECKING:
    from sqladmin.models import ModelAdmin


DEFAULT_PAGE_SIZE = 10


class AjaxModelLoader(object):
    """Ajax related model loader. Override this to implement custom loading behavior."""

    def __init__(self, name: str, options: dict):
        self.name = name
        self.options = options

    def format(self, model: type):
        """Return (id, name) tuple from the model."""
        raise NotImplementedError()

    def get_list(self, query, offset: int = 0, limit: int = DEFAULT_PAGE_SIZE):
        """Return models that match `query`."""
        raise NotImplementedError()


class QueryAjaxModelLoader(AjaxModelLoader):
    def __init__(
        self,
        name: str,
        model: type,
        model_admin: "ModelAdmin",
        **options: dict,
    ):
        super().__init__(name, options)

        self.model = model
        self.model_admin = model_admin
        self.fields = options.get("fields")
        self.order_by = options.get("order_by")
        self.filters = options.get("filters")

        if not self.fields:
            raise ValueError(
                "AJAX loading requires `fields` to be specified for "
                f"{self.model}.{self.name}"
            )

        self._cached_fields = self._process_fields()
        self.pk = get_primary_key(self.model)

    def _process_fields(self):
        remote_fields = []

        for field in self.fields:
            if isinstance(field, str):
                attr = getattr(self.model, field, None)

                if not attr:
                    raise ValueError(f"{self.model}.{field} does not exist.")

                remote_fields.append(attr)
            else:
                remote_fields.append(field)

        return remote_fields

    def format(self, model: type) -> dict:
        if not model:
            return None

        return {"id": getattr(model, self.pk.key), "text": str(model)}

    async def get_list(
        self, term: str, offset: int = 0, limit: int = DEFAULT_PAGE_SIZE
    ):
        stmt = select(self.model)

        # no type casting to string if a ColumnAssociationProxyInstance is given
        filters = (
            field.ilike("%%%s%%" % term)
            if is_association_proxy(field)
            else cast(field, String).ilike("%%%s%%" % term)
            for field in self._cached_fields
        )
        stmt = stmt.filter(or_(*filters))

        if self.filters:
            filters = [
                text("%s.%s" % (self.model.__tablename__.lower(), value))
                for value in self.filters
            ]
            stmt = stmt.filter(and_(*filters))

        if self.order_by:
            stmt = stmt.order_by(self.order_by)

        stmt = stmt.offset(offset).limit(limit)
        print(stmt, "!!!")
        result = await self.model_admin._run_query(stmt)
        return result


def create_ajax_loader(
    model_admin: "ModelAdmin",
    name: str,
    field_name: str,
    options: dict,
):
    attr = getattr(model_admin.model, field_name, None)

    if attr is None:
        raise ValueError(f"Model {model_admin.model} does not have field {field_name}.")

    if not is_relationship(attr) and not is_association_proxy(attr):
        raise ValueError(f"{model_admin.model}.{field_name} is not a relation.")

    if is_association_proxy(attr):
        attr = attr.remote_attr

    remote_model = attr.prop.mapper.class_
    return QueryAjaxModelLoader(name, remote_model, model_admin, **options)
