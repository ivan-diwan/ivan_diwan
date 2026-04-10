from __future__ import annotations

from pathlib import Path
import re

from form_constructor.conversion.exporter import PythonExporter
from form_constructor.conversion.importer import PythonImporter
from form_constructor.document.form_document import FormDocument
from form_constructor.document.validator import DocumentValidator
from form_constructor.registry.widget_registry import WidgetRegistry
from form_constructor.serialization.form_serializer import FormSerializer


class DocumentIOService:
    def __init__(
        self,
        *,
        widget_registry: WidgetRegistry,
        validator: DocumentValidator,
    ) -> None:
        self._validator = validator
        self.serializer = FormSerializer(widget_registry=widget_registry, validator=validator)
        self.python_exporter = PythonExporter()
        self.python_importer = PythonImporter(widget_registry=widget_registry, validator=validator)

    def load_json_payload(self, payload: str) -> FormDocument:
        return self.serializer.deserialize_from_json(payload)

    def load_json_path(self, path: str) -> FormDocument:
        return self.serializer.load_json(path)

    def load_python_path(self, path: str) -> FormDocument:
        return self.python_importer.import_from_file(path)

    def load_path(self, path: str) -> FormDocument:
        lowered = str(path).lower()
        if lowered.endswith(".json"):
            return self.load_json_path(path)
        if lowered.endswith(".py"):
            return self.load_python_path(path)
        raise ValueError(f"Unsupported document format for '{path}'.")

    def save_json(self, document: FormDocument, path: str) -> str:
        self.serializer.save_json(document, path)
        return path

    def export_python(self, document: FormDocument, path: str) -> str:
        self._validator.validate_document(document)
        target_path = self.normalize_python_export_path(path)
        self.python_exporter.export_to_file(document, target_path)
        return target_path

    def export_python_source(self, document: FormDocument) -> str:
        self._validator.validate_document(document)
        self.python_exporter.validate_export(document)
        return self.python_exporter.export(document)

    def serialize_snapshot(self, document: FormDocument) -> str:
        return self.serializer.serialize_to_json(document)

    def suggest_python_export_path(
        self,
        *,
        current_python_path: str | None,
        current_json_path: str | None,
        active_document: FormDocument | None,
    ) -> str:
        if current_python_path:
            return current_python_path
        if current_json_path:
            return str(Path(current_json_path).with_suffix(".py"))
        if active_document is None:
            return ""
        base_name = self.python_export_base_name(active_document.form_root.name)
        return f"{base_name}.py"

    @staticmethod
    def python_export_base_name(value: str) -> str:
        normalized = re.sub(r"\W+", "_", str(value).strip().lower()).strip("_")
        return normalized or "generated_form"

    @staticmethod
    def normalize_python_export_path(path: str) -> str:
        normalized_path = Path(path)
        if normalized_path.suffix:
            return str(normalized_path)
        return str(normalized_path.with_suffix(".py"))
