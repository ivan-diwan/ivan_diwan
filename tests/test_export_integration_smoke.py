from __future__ import annotations

from pathlib import Path
import unittest
from unittest.mock import patch

from PySide6.QtWidgets import QApplication

from form_constructor.controller.document_controller import DocumentController
from form_constructor.conversion.export_validation import ExportDiagnosticError
from form_constructor.registry.builtins import build_builtin_registry
from form_constructor.ui.main_editor.main_editor_window import MainEditorWindow
from tests.support import managed_test_paths


class ExportIntegrationSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.controller = DocumentController(build_builtin_registry())
        self.window = MainEditorWindow(self.controller)
        self.window.show()
        self._process_events()

    def tearDown(self) -> None:
        self.window.close()
        self._process_events()

    def test_export_python_button_follows_document_state(self) -> None:
        self.assertFalse(self.window._export_python_button.isEnabled())

        self.controller.new_document(width=640, height=480)
        self._process_events()

        self.assertTrue(self.window._export_python_button.isEnabled())

    def test_controller_exports_python_file_for_active_document(self) -> None:
        self.controller.new_document(width=640, height=480)
        self.controller.create_entity_from_drop("QPushButton", 10, 20, "form_root")
        with managed_test_paths("tests\\_tmp_exported_form.py") as (target_path,):
            exported_path = self.controller.export_document_to_python(str(target_path))
            self.assertEqual(exported_path, str(target_path))
            self.assertEqual(self.controller.editor_state.current_python_path, str(target_path))
            self.assertTrue(target_path.exists())
            source = target_path.read_text(encoding="utf-8")
            self.assertIn("class GeneratedWidget(QWidget):", source)
            self.assertIn("QPushButton", source)
            compile(source, "<exported_form>", "exec")

    def test_controller_save_python_alias_exports_file(self) -> None:
        self.controller.new_document(width=640, height=480)
        with managed_test_paths("tests\\_tmp_save_python_alias.py") as (target_path,):
            exported_path = self.controller.save_python(str(target_path))
            self.assertEqual(exported_path, str(target_path))
            self.assertTrue(target_path.exists())

    def test_controller_adds_py_suffix_when_export_path_has_no_extension(self) -> None:
        self.controller.new_document(width=640, height=480)
        with managed_test_paths("tests\\_tmp_export_no_suffix", "tests\\_tmp_export_no_suffix.py") as (
            target_path,
            normalized_path,
        ):
            exported_path = self.controller.export_document_to_python(str(target_path))
            self.assertEqual(exported_path, str(normalized_path))
            self.assertEqual(self.controller.editor_state.current_python_path, str(normalized_path))
            self.assertTrue(normalized_path.exists())

    def test_python_export_path_resets_for_new_document_and_close(self) -> None:
        self.controller.new_document(width=640, height=480)
        with managed_test_paths("tests\\_tmp_export_reset.py") as (target_path,):
            self.controller.export_document_to_python(str(target_path))
            self.assertEqual(self.controller.editor_state.current_python_path, str(target_path))

            self.controller.new_document(width=320, height=240)
            self.assertIsNone(self.controller.editor_state.current_python_path)

            self.controller.export_document_to_python(str(target_path))
            self.assertEqual(self.controller.editor_state.current_python_path, str(target_path))

            self.controller.close_document()
            self.assertIsNone(self.controller.editor_state.current_python_path)

    def test_controller_python_source_matches_file_export(self) -> None:
        self.controller.new_document(width=640, height=480)
        self.controller.create_entity_from_drop("QPushButton", 10, 20, "form_root")
        with managed_test_paths("tests\\_tmp_export_compare.py") as (target_path,):
            source_from_controller = self.controller.export_document_to_python_source()
            self.controller.export_document_to_python(str(target_path))
            source_from_file = target_path.read_text(encoding="utf-8")

            self.assertEqual(source_from_controller, source_from_file)

    def test_controller_python_export_does_not_write_invalid_file(self) -> None:
        self.controller.new_document(width=640, height=480)
        with managed_test_paths("tests\\_tmp_invalid_controller_export.py") as (target_path,):
            with patch.object(
                self.controller._python_exporter._export_validator,
                "validate_python_syntax",
                side_effect=SyntaxError("broken export"),
            ):
                with self.assertRaises(ExportDiagnosticError) as context:
                    self.controller.export_document_to_python(str(target_path))
            self.assertEqual(context.exception.diagnostic.stage, "export_to_file")
            self.assertIn("broken export", context.exception.diagnostic.message)
            self.assertFalse(target_path.exists())

    def test_python_export_keeps_selection_and_dirty_state(self) -> None:
        self.controller.new_document(width=640, height=480)
        entity = self.controller.create_entity_from_drop("QPushButton", 10, 20, "form_root")
        document = self.controller.active_document
        self.assertIsNotNone(document)
        self.assertTrue(document.is_dirty)
        self.assertEqual(self.controller.selected_entity.id, entity.id)

        with managed_test_paths("tests\\_tmp_export_state.py") as (target_path,):
            self.controller.export_document_to_python(str(target_path))
            self.assertTrue(document.is_dirty)
            self.assertIsNotNone(self.controller.selected_entity)
            self.assertEqual(self.controller.selected_entity.id, entity.id)

    def test_suggest_python_export_path_uses_python_then_json_path(self) -> None:
        self.controller.new_document(width=640, height=480)
        self.assertEqual(self.controller.suggest_python_export_path(), "form_root.py")

        with managed_test_paths("tests\\demo_form.json", "tests\\explicit_export.py") as (json_path, explicit_path):
            self.controller.save_document_to_json(str(json_path))
            self.assertEqual(
                self.controller.suggest_python_export_path(),
                "tests\\demo_form.py",
            )

            self.controller.export_document_to_python(str(explicit_path))
            self.assertEqual(
                self.controller.suggest_python_export_path(),
                str(explicit_path),
            )

    def test_suggest_python_export_path_falls_back_to_form_name(self) -> None:
        self.controller.new_document(width=640, height=480)
        self.controller.update_form_root(name="My Demo Form")
        self.assertEqual(self.controller.suggest_python_export_path(), "my_demo_form.py")

        self.controller.update_form_root(name="***")
        self.assertEqual(self.controller.suggest_python_export_path(), "generated_form.py")

    def test_controller_loads_document_from_python(self) -> None:
        self.controller.new_document(width=640, height=480)
        self.controller.create_entity_from_drop("QPushButton", 10, 20, "form_root")
        with managed_test_paths("tests\\_tmp_import_from_python.py") as (export_path,):
            self.controller.export_document_to_python(str(export_path))
            self.controller.close_document()
            loaded = self.controller.load_document_from_python(str(export_path))
            self.assertEqual(loaded.form_root.root_widget_type, "QWidget")
            self.assertEqual(self.controller.editor_state.current_python_path, str(export_path))
            self.assertEqual(len(loaded.get_root_entities()), 1)
            self.assertEqual(loaded.get_root_entities()[0].type, "QPushButton")

    def test_controller_load_document_routes_by_extension(self) -> None:
        self.controller.new_document(width=640, height=480)
        self.controller.create_entity_from_drop("QPushButton", 10, 20, "form_root")
        with managed_test_paths("tests\\_tmp_load_route.json", "tests\\_tmp_load_route.py") as (json_path, py_path):
            self.controller.save_document_to_json(str(json_path))
            self.controller.export_document_to_python(str(py_path))

            loaded_json = self.controller.load_document(str(json_path))
            self.assertEqual(self.controller.editor_state.current_json_path, str(json_path))
            self.assertIsNone(self.controller.editor_state.current_python_path)
            self.assertEqual(len(loaded_json.get_root_entities()), 1)

            loaded_py = self.controller.load_document(str(py_path))
            self.assertIsNone(self.controller.editor_state.current_json_path)
            self.assertEqual(self.controller.editor_state.current_python_path, str(py_path))
            self.assertEqual(len(loaded_py.get_root_entities()), 1)
            self.assertEqual(loaded_py.get_root_entities()[0].type, "QPushButton")

    def test_controller_reexports_loaded_python_document_for_mixed_case(self) -> None:
        json_path = Path("tests\\export_cases\\mixed_complex.json")
        with managed_test_paths(
            "tests\\_tmp_mixed_complex_roundtrip.py",
            "tests\\_tmp_mixed_complex_reexport.py",
        ) as (export_path, reexport_path):
            original = self.controller.load_document_from_json_path(str(json_path))
            original_source = self.controller.export_document_to_python_source()
            self.controller.export_document_to_python(str(export_path))

            self.controller.load_document_from_python(str(export_path))
            reexported_source = self.controller.export_document_to_python_source()
            self.controller.export_document_to_python(str(reexport_path))

            self.assertEqual(original_source, reexported_source)
            self.assertTrue(export_path.exists())
            self.assertTrue(reexport_path.exists())
            self.assertEqual(
                export_path.read_text(encoding="utf-8"),
                reexport_path.read_text(encoding="utf-8"),
            )

    def test_load_and_import_reset_selection_and_dirty_state(self) -> None:
        self.controller.new_document(width=640, height=480)
        entity = self.controller.create_entity_from_drop("QPushButton", 10, 20, "form_root")
        self.assertEqual(self.controller.selected_entity.id, entity.id)
        self.assertTrue(self.controller.active_document.is_dirty)

        with managed_test_paths("tests\\_tmp_selection_reset.json", "tests\\_tmp_selection_reset.py") as (
            json_path,
            py_path,
        ):
            self.controller.save_document_to_json(str(json_path))
            self.controller.export_document_to_python(str(py_path))

            loaded_json = self.controller.load_document(str(json_path))
            self.assertFalse(loaded_json.is_dirty)
            self.assertIsNone(self.controller.selected_entity)
            self.assertEqual(self.controller.get_snapshot(), self.controller._serializer.serialize_to_json(loaded_json))

            loaded_py = self.controller.load_document(str(py_path))
            self.assertFalse(loaded_py.is_dirty)
            self.assertIsNone(self.controller.selected_entity)
            self.assertEqual(self.controller.get_snapshot(), self.controller._serializer.serialize_to_json(loaded_py))

    def test_can_continue_editing_after_python_import(self) -> None:
        self.controller.new_document(width=640, height=480)
        self.controller.create_entity_from_drop("QPushButton", 10, 20, "form_root")
        with managed_test_paths(
            "tests\\_tmp_continue_after_import.py",
            "tests\\_tmp_continue_after_import.json",
            "tests\\_tmp_continue_after_import_reexport.py",
        ) as (py_path, json_path, reexport_path):
            self.controller.export_document_to_python(str(py_path))
            self.controller.load_document_from_python(str(py_path))

            created = self.controller.create_entity_from_drop("QLabel", 40, 60, "form_root")
            self.assertEqual(created.type, "QLabel")
            self.assertTrue(self.controller.active_document.is_dirty)
            self.assertEqual(self.controller.selected_entity.id, created.id)

            saved_json_path = self.controller.save_document_to_json(str(json_path))
            self.assertEqual(saved_json_path, str(json_path))
            self.assertFalse(self.controller.active_document.is_dirty)
            self.assertEqual(self.controller.editor_state.current_json_path, str(json_path))

            exported_path = self.controller.export_document_to_python(str(reexport_path))
            self.assertEqual(exported_path, str(reexport_path))
            self.assertTrue(reexport_path.exists())
            self.assertIn("QLabel", reexport_path.read_text(encoding="utf-8"))

    def test_load_document_rejects_unsupported_extension(self) -> None:
        with self.assertRaises(ValueError):
            self.controller.load_document("tests\\unsupported.txt")

    def test_main_window_load_routes_python_files_to_importer(self) -> None:
        self.controller.new_document(width=640, height=480)
        self.controller.create_entity_from_drop("QPushButton", 10, 20, "form_root")
        with managed_test_paths("tests\\_tmp_window_import.py") as (export_path,):
            self.controller.export_document_to_python(str(export_path))
            with patch(
                "form_constructor.ui.main_editor.main_editor_window.QFileDialog.getOpenFileName",
                return_value=(str(export_path), "Python Files (*.py)"),
            ):
                self.window._load_document()
            self.assertIsNotNone(self.controller.active_document)
            self.assertEqual(self.controller.editor_state.current_python_path, str(export_path))
            self.assertEqual(len(self.controller.active_document.get_root_entities()), 1)
            self.assertEqual(self.controller.active_document.get_root_entities()[0].type, "QPushButton")

    @classmethod
    def _process_events(cls) -> None:
        cls._app.processEvents()


if __name__ == "__main__":
    unittest.main()
