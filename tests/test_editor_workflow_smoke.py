from __future__ import annotations

from pathlib import Path
import unittest

from PySide6.QtWidgets import QApplication

from form_constructor.controller.document_controller import DocumentController
from form_constructor.registry.builtins import build_builtin_registry
from form_constructor.serialization.form_serializer import FormSerializer
from tests.support import compare_document_structure, managed_test_paths


class EditorWorkflowSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.registry = build_builtin_registry()
        self.controller = DocumentController(self.registry)
        self.serializer = FormSerializer(widget_registry=self.registry)

    def test_create_edit_save_json_close_load_json_cycle(self) -> None:
        self.controller.new_document(width=800, height=600)
        self.controller.update_form_root(name="Json Cycle", window_title="JSON Cycle")
        frame = self.controller.create_entity_from_drop("QFrame", 20, 20, "form_root")
        self.controller.update_entity_property(frame.id, "frame_shape", "Box")
        self.controller.update_entity_property(frame.id, "frame_shadow", "Sunken")
        label = self.controller.create_entity_from_drop("QLabel", 12, 14, frame.id)
        self.controller.rename_entity(label.id, "json_cycle_label")
        self.controller.update_entity_property(label.id, "text", "Loaded Back")

        before_save_snapshot = self.controller.get_snapshot()
        with managed_test_paths("tests\\_tmp_workflow_cycle.json") as (json_path,):
            self.controller.save_document_to_json(str(json_path))
            self.assertTrue(json_path.exists())
            self.assertFalse(self.controller.active_document.is_dirty)

            self.controller.close_document()
            self.assertIsNone(self.controller.active_document)

            loaded = self.controller.load_document(str(json_path))
            self.assertEqual(loaded.form_root.name, "Json Cycle")
            self.assertEqual(loaded.form_root.window_title, "JSON Cycle")
            self.assertFalse(loaded.is_dirty)
            self.assertEqual(self.controller.get_snapshot(), before_save_snapshot)

            root_entities = loaded.get_root_entities()
            self.assertEqual(len(root_entities), 1)
            self.assertEqual(root_entities[0].type, "QFrame")
            frame_loaded = root_entities[0]
            children = loaded.get_children(frame_loaded.id)
            self.assertEqual(len(children), 1)
            self.assertEqual(children[0].name, "json_cycle_label")
            self.assertEqual(children[0].properties["text"], "Loaded Back")

    def test_create_edit_export_python_import_continue_edit_export_cycle(self) -> None:
        self.controller.new_document(width=900, height=700)
        self.controller.update_form_root(name="Python Cycle", window_title="Python Cycle")

        tab_widget = self.controller.create_entity_from_drop("QTabWidget", 20, 20, "form_root")
        tab_pages = self.controller.active_document.get_tab_pages(tab_widget.id)
        self.controller.rename_tab_page(tab_pages[0].id, "First")
        self.controller.rename_tab_page(tab_pages[1].id, "Second")
        self.controller.set_current_tab(tab_widget.id, 1)

        self.controller.create_entity_from_drop("QPushButton", 10, 12, tab_pages[0].id)
        second_label = self.controller.create_entity_from_drop("QLabel", 14, 18, tab_pages[1].id)
        self.controller.rename_entity(second_label.id, "python_cycle_label")
        self.controller.update_entity_property(second_label.id, "text", "Before Import")

        splitter = self.controller.create_entity_from_drop("QSplitter", 420, 30, "form_root")
        self.controller.set_splitter_orientation(splitter.id, "vertical")
        self.controller.set_splitter_sizes(splitter.id, [120, 240])
        panes = self.controller.active_document.get_splitter_panes(splitter.id)
        self.controller.create_entity_from_drop("QLineEdit", 10, 14, panes[0].id)
        self.controller.create_entity_from_drop("QCheckBox", 12, 16, panes[1].id)

        original_source = self.controller.export_document_to_python_source()
        with managed_test_paths(
            "tests\\_tmp_workflow_cycle.py",
            "tests\\_tmp_workflow_cycle_reexport.py",
        ) as (export_path, reexport_path):
            self.controller.export_document_to_python(str(export_path))
            self.controller.load_document_from_python(str(export_path))

            imported_source = self.controller.export_document_to_python_source()
            self.assertEqual(original_source, imported_source)

            created = self.controller.create_entity_from_drop("QGroupBox", 30, 320, "form_root")
            self.controller.update_entity_property(created.id, "title", "After Import")
            self.controller.update_entity_property(created.id, "checkable", True)
            self.controller.update_entity_property(created.id, "checked", True)

            reexported_path = self.controller.export_document_to_python(str(reexport_path))
            self.assertEqual(reexported_path, str(reexport_path))
            self.assertTrue(reexport_path.exists())

            final_source = reexport_path.read_text(encoding="utf-8")
            self.assertIn("QGroupBox", final_source)
            self.assertIn("After Import", final_source)
            self.assertIn("python_cycle_label", final_source)

    def test_mixed_form_full_roundtrip_preserves_structure_signature(self) -> None:
        json_path = Path("tests\\export_cases\\mixed_complex.json")
        with managed_test_paths("tests\\_tmp_mixed_full_roundtrip.py") as (python_path,):
            original_document = self.controller.load_document(str(json_path))
            self.controller.export_document_to_python(str(python_path))

            roundtrip_document = self.controller.load_document(str(python_path))
            self.assertTrue(
                compare_document_structure(
                    original_document,
                    roundtrip_document,
                    self.serializer,
                    parent_reference="name",
                )
            )
            self.assertFalse(roundtrip_document.is_dirty)
            self.assertIsNone(self.controller.selected_entity)


if __name__ == "__main__":
    unittest.main()
