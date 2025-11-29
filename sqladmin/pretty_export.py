import json
from typing import TYPE_CHECKING, Any, AsyncGenerator, List

from starlette.responses import StreamingResponse

from sqladmin.helpers import Writer, secure_filename, stream_to_csv

if TYPE_CHECKING:
    from .models import ModelView


class PrettyExport:
    @staticmethod
    async def _base_export_cell(
        model_view: "ModelView", name: str, value: Any, formatted_value: Any
    ) -> str:
        """
        Default formatting logic for a cell in pretty export.

        Used when `custom_export_cell` returns None.
        Applies standard rules for related fields, booleans, etc.

        Only used when `use_pretty_export = True`.
        """
        # Check if this is a related field
        related_model_relations = getattr(model_view, "related_model_relations", [])
        if name in model_view._relation_names or name in related_model_relations:
            if isinstance(value, list):
                cell_value = ",".join(str(v) for v in formatted_value)
            else:
                cell_value = str(formatted_value)
        else:
            if isinstance(value, bool):
                cell_value = "TRUE" if value else "FALSE"
            else:
                cell_value = str(formatted_value)
        return cell_value

    @classmethod
    async def _get_export_row_values(
        cls, model_view: "ModelView", row: Any, column_names: List[str]
    ) -> List[Any]:
        row_values = []
        for name in column_names:
            value, formatted_value = await model_view.get_list_value(row, name)
            custom_value = await model_view.custom_export_cell(row, name, value)
            if custom_value is None:
                cell_value = await cls._base_export_cell(
                    model_view, name, value, formatted_value
                )
            else:
                cell_value = custom_value
            row_values.append(cell_value)
        return row_values

    @classmethod
    async def pretty_export_csv(
        cls, model_view: "ModelView", rows: List[Any]
    ) -> StreamingResponse:
        async def generate(writer: Writer) -> AsyncGenerator[Any, None]:
            column_names = model_view.get_export_columns()
            headers = [
                model_view._column_labels.get(name, name) for name in column_names
            ]

            yield writer.writerow(headers)

            for row in rows:
                vals = await cls._get_export_row_values(model_view, row, column_names)
                yield writer.writerow(vals)

        filename = secure_filename(model_view.get_export_name(export_type="csv"))

        return StreamingResponse(
            content=stream_to_csv(generate),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment;filename={filename}"},
        )

    @classmethod
    async def pretty_export_json(
        cls, model_view: "ModelView", rows: List[Any]
    ) -> StreamingResponse:
        """Export data as JSON with pretty formatting applied."""

        async def generate() -> AsyncGenerator[str, None]:
            yield "["
            column_names = model_view.get_export_columns()
            len_data = len(rows)
            last_idx = len_data - 1
            separator = "," if len_data > 1 else ""

            for idx, row in enumerate(rows):
                vals = await cls._get_export_row_values(model_view, row, column_names)
                # Create dict with labeled keys
                row_dict = {
                    model_view._column_labels.get(name, name): val
                    for name, val in zip(column_names, vals)
                }
                yield json.dumps(row_dict, ensure_ascii=False) + (
                    separator if idx < last_idx else ""
                )

            yield "]"

        filename = secure_filename(model_view.get_export_name(export_type="json"))
        return StreamingResponse(
            content=generate(),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment;filename={filename}"},
        )
