from __future__ import annotations

from pathlib import Path
import unittest

from form_constructor.conversion.exporter import PythonExporter
from form_constructor.conversion.importer import ImportDiagnosticError, PythonImporter
from form_constructor.conversion.python_converter import PythonConverter
from form_constructor.registry.builtins import build_builtin_registry
from form_constructor.serialization.form_serializer import FormSerializer
from tests.support import (
    compare_document_payloads,
    compare_document_structure,
    managed_test_paths,
)


class PythonImporterSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._cases_dir = Path("tests/export_cases")

    def setUp(self) -> None:
        self.registry = build_builtin_registry()
        self.serializer = FormSerializer(widget_registry=self.registry)
        self.exporter = PythonExporter()
        self.importer = PythonImporter(widget_registry=self.registry)

    def test_importer_rejects_invalid_python_syntax(self) -> None:
        with self.assertRaises(ImportDiagnosticError) as context:
            self.importer.import_from_code("class Broken(:\n    pass\n")
        diagnostic = context.exception.diagnostic
        self.assertEqual(diagnostic.stage, "parse_ast")
        self.assertEqual(diagnostic.line, 1)
        self.assertFalse(diagnostic.unsupported)

    def test_importer_rejects_missing_form_class(self) -> None:
        with self.assertRaises(ImportDiagnosticError) as context:
            self.importer.import_from_code("def setup_ui():\n    pass\n")
        diagnostic = context.exception.diagnostic
        self.assertEqual(diagnostic.stage, "find_form_class")
        self.assertIn("GeneratedWidget", diagnostic.pattern or "")

    def test_imports_dialog_root_from_exported_python(self) -> None:
        document = self.serializer.load_json("tests/export_cases/empty_form.json")
        document.form_root.root_widget_type = "QDialog"
        source = self.exporter.export(document)

        imported = self.importer.import_from_code(source)

        self.assertEqual(imported.form_root.root_widget_type, "QDialog")
        self.assertEqual(imported.form_root.width, 800)
        self.assertEqual(imported.form_root.height, 600)

    def test_fixture_cases_roundtrip_structure(self) -> None:
        for case_path in sorted(self._cases_dir.glob("*.json")):
            with self.subTest(case=case_path.name):
                original = self.serializer.load_json(str(case_path))
                source = self.exporter.export(original)
                imported = self.importer.import_from_code(source)
                self.assertTrue(
                    compare_document_structure(
                        original,
                        imported,
                        self.serializer,
                        parent_reference="name",
                    )
                )

    def test_fixture_cases_roundtrip_python_is_stable(self) -> None:
        for case_path in sorted(self._cases_dir.glob("*.json")):
            with self.subTest(case=case_path.name):
                original = self.serializer.load_json(str(case_path))
                first_source = self.exporter.export(original)
                imported = self.importer.import_from_code(first_source)
                second_source = self.exporter.export(imported)
                self.assertEqual(first_source, second_source)

    def test_python_converter_supports_both_directions(self) -> None:
        converter = PythonConverter(widget_registry=self.registry)
        document = self.serializer.load_json("tests/export_cases/basic_leafs.json")
        with managed_test_paths("tests\\_tmp_converter_roundtrip.py") as (path,):
            converter.export_to_python(document, str(path))
            imported = converter.import_from_python(str(path))
            self.assertTrue(compare_document_payloads(document, imported, self.serializer))

    def test_importer_exposes_structured_unsupported_case_diagnostic(self) -> None:
        code = """
from PySide6.QtWidgets import QApplication, QTextEdit, QWidget

class GeneratedWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        self.setObjectName("form_root")
        self.resize(400, 300)
        self.editor_1 = QTextEdit(self)
        self.editor_1.setObjectName("editor_1")
        self.editor_1.setGeometry(10, 10, 100, 80)
        self.editor_1.setHtml("<b>Broken</b>")
"""
        with self.assertRaises(ImportDiagnosticError) as context:
            self.importer.import_from_code(code)
        diagnostic = context.exception.diagnostic
        self.assertEqual(diagnostic.stage, "apply_entity_call")
        self.assertTrue(diagnostic.unsupported)
        self.assertEqual(diagnostic.entity_type, "QTextEdit")
        self.assertEqual(diagnostic.entity_ref, "editor_1")
        self.assertEqual(diagnostic.line, 15)
        self.assertIn("setHtml", diagnostic.pattern or "")

if __name__ == "__main__":
    unittest.main()
