from __future__ import annotations

from form_constructor.document.form_document import FormDocument
from form_constructor.document.models import EntityModel, FormRootModel
from form_constructor.document.validator import DocumentValidator
from form_constructor.registry.widget_registry import WidgetRegistry
from form_constructor.serialization.parser import parse_json_document, parse_json_file
from form_constructor.serialization.writer import write_json_document, write_json_file


class FormSerializer:
    def __init__(
        self,
        widget_registry: WidgetRegistry,
        validator: DocumentValidator | None = None,
    ) -> None:
        self._widget_registry = widget_registry
        self._validator = validator or DocumentValidator()

    def serialize_to_dict(self, document: FormDocument) -> dict:
        self._validator.validate_document(document)
        return {
            "meta": {
                "format_version": 1,
                "document_type": "pyside6_form",
            },
            "form": document.get_form_root().to_dict(),
            "objects": [entity.to_dict() for entity in self._iter_entities_in_document_order(document)],
        }

    def serialize_to_json(self, document: FormDocument) -> str:
        return write_json_document(self.serialize_to_dict(document))

    def deserialize_from_dict(self, data: dict) -> FormDocument:
        meta = data.get("meta", {})
        if meta.get("document_type") not in {None, "pyside6_form"}:
            raise ValueError(f"Unsupported document_type: {meta.get('document_type')}")
        form_root = FormRootModel.from_dict(data["form"])
        entities = {
            entity_data["id"]: EntityModel.from_dict(entity_data)
            for entity_data in data.get("objects", [])
        }
        document = FormDocument(
            form_root=form_root,
            widget_registry=self._widget_registry,
            entities_by_id=entities,
        )
        self._validator.validate_document(document)
        return document

    def deserialize_from_json(self, payload: str) -> FormDocument:
        return self.deserialize_from_dict(parse_json_document(payload))

    def save_json(self, document: FormDocument, path: str) -> None:
        write_json_file(path, self.serialize_to_dict(document))

    def load_json(self, path: str) -> FormDocument:
        return self.deserialize_from_dict(parse_json_file(path))

    def _iter_entities_in_document_order(self, document: FormDocument) -> list[EntityModel]:
        ordered_entities: list[EntityModel] = []

        def collect(parent_id: str) -> None:
            for child in document.get_children(parent_id):
                ordered_entities.append(child)
                collect(child.id)

        collect(document.form_root.id)
        return ordered_entities
