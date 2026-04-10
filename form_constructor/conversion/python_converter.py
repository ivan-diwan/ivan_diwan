from __future__ import annotations

from form_constructor.conversion.exporter import PythonExporter
from form_constructor.conversion.importer import PythonImporter
from form_constructor.document.form_document import FormDocument
from form_constructor.document.validator import DocumentValidator
from form_constructor.registry.widget_registry import WidgetRegistry


class PythonConverter:
    def __init__(
        self,
        widget_registry: WidgetRegistry,
        validator: DocumentValidator | None = None,
    ) -> None:
        self._exporter = PythonExporter()
        self._importer = PythonImporter(widget_registry=widget_registry, validator=validator)

    def export_to_python(self, document: FormDocument, path: str) -> None:
        self._exporter.export_to_file(document, path)

    def import_from_python(self, path: str) -> FormDocument:
        return self._importer.import_from_file(path)
