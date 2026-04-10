from __future__ import annotations

from pathlib import Path
import unittest

from form_constructor.conversion.exporter import PythonExporter
from form_constructor.conversion.importer import PythonImporter
from form_constructor.registry.builtins import build_builtin_registry
from form_constructor.serialization.form_serializer import FormSerializer
from tests.support import compare_document_structure, managed_test_paths


class PythonImportCaseFilesSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._cases_dir = Path("tests/export_cases")

    def setUp(self) -> None:
        self.registry = build_builtin_registry()
        self.serializer = FormSerializer(widget_registry=self.registry)
        self.exporter = PythonExporter()
        self.importer = PythonImporter(widget_registry=self.registry)

    def test_import_from_file_matches_fixture_structure_for_all_cases(self) -> None:
        for case_path in sorted(self._cases_dir.glob("*.json")):
            with self.subTest(case=case_path.name):
                original = self.serializer.load_json(str(case_path))
                python_path_str = str(self._cases_dir / f"_{case_path.stem}_roundtrip.py")
                with managed_test_paths(python_path_str) as (python_path,):
                    self.exporter.export_to_file(original, str(python_path))
                    imported = self.importer.import_from_file(str(python_path))
                    self.assertTrue(
                        compare_document_structure(
                            original,
                            imported,
                            self.serializer,
                            parent_reference="name",
                        )
                    )

    def test_import_from_file_reexport_is_stable_for_all_cases(self) -> None:
        for case_path in sorted(self._cases_dir.glob("*.json")):
            with self.subTest(case=case_path.name):
                original = self.serializer.load_json(str(case_path))
                python_path_str = str(self._cases_dir / f"_{case_path.stem}_stability.py")
                reexport_path_str = str(self._cases_dir / f"_{case_path.stem}_stability_reexport.py")
                with managed_test_paths(python_path_str, reexport_path_str) as (python_path, reexport_path):
                    original_source = self.exporter.export(original)
                    self.exporter.export_to_file(original, str(python_path))
                    imported = self.importer.import_from_file(str(python_path))
                    imported_source = self.exporter.export(imported)
                    self.exporter.export_to_file(imported, str(reexport_path))

                    self.assertEqual(original_source, imported_source)
                    self.assertEqual(
                        python_path.read_text(encoding="utf-8"),
                        reexport_path.read_text(encoding="utf-8"),
                    )

if __name__ == "__main__":
    unittest.main()
