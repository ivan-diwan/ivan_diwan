from __future__ import annotations

from pathlib import Path
import unittest

from PySide6.QtWidgets import QApplication, QSpinBox

from form_constructor.controller.document_controller import DocumentController
from form_constructor.registry.builtins import build_builtin_registry
from form_constructor.serialization.form_serializer import FormSerializer
from form_constructor.ui.main_editor.main_editor_window import MainEditorWindow
from tests.support import managed_test_paths, structure_signature


class QSpinBoxSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.registry = build_builtin_registry()
        self.controller = DocumentController(self.registry)
        self.serializer = FormSerializer(widget_registry=self.registry)
        self.window = MainEditorWindow(self.controller)
        self.window.show()
        self._process_events()
        self.controller.new_document(width=800, height=600)
        self._process_events()

    def tearDown(self) -> None:
        self.window.close()
        self._process_events()

    def test_qspinbox_appears_in_palette_and_can_be_created(self) -> None:
        palette_types = {definition.type_name for definition in self.registry.list_palette_types()}
        self.assertIn("QSpinBox", palette_types)

        entity = self.controller.create_entity_from_drop("QSpinBox", 40, 50, "form_root")
        self._process_events()

        self.assertEqual(entity.type, "QSpinBox")
        self.assertEqual(self.controller.selected_entity.id, entity.id)
        view = self.window._form_window._canvas._item_views_by_id[entity.id]
        self.assertIsInstance(view.inner_widget, QSpinBox)

    def test_qspinbox_properties_update_canvas_and_snapshot(self) -> None:
        entity = self.controller.create_entity_from_drop("QSpinBox", 40, 50, "form_root")
        self.controller.update_entity_property(entity.id, "value", 5)
        self.controller.update_entity_property(entity.id, "minimum", 0)
        self.controller.update_entity_property(entity.id, "maximum", 20)
        self.controller.update_entity_property(entity.id, "step", 2)
        self.controller.update_entity_property(entity.id, "prefix", "$ ")
        self.controller.update_entity_property(entity.id, "suffix", " kg")
        self._process_events()

        updated = self.controller.active_document.get_entity(entity.id)
        self.assertEqual(updated.properties["value"], 5)
        self.assertEqual(updated.properties["minimum"], 0)
        self.assertEqual(updated.properties["maximum"], 20)
        self.assertEqual(updated.properties["step"], 2)
        self.assertEqual(updated.properties["prefix"], "$ ")
        self.assertEqual(updated.properties["suffix"], " kg")

        spin_widget = self.window._form_window._canvas._item_views_by_id[entity.id].inner_widget
        self.assertEqual(spin_widget.minimum(), 0)
        self.assertEqual(spin_widget.maximum(), 20)
        self.assertEqual(spin_widget.singleStep(), 2)
        self.assertEqual(spin_widget.prefix(), "$ ")
        self.assertEqual(spin_widget.suffix(), " kg")
        self.assertEqual(spin_widget.value(), 5)
        self.assertIn('"type": "QSpinBox"', self.controller.get_snapshot())

    def test_qspinbox_range_normalization_keeps_document_valid(self) -> None:
        entity = self.controller.create_entity_from_drop("QSpinBox", 40, 50, "form_root")

        self.controller.update_entity_property(entity.id, "minimum", 50)
        self.controller.update_entity_property(entity.id, "maximum", 10)
        self._process_events()

        updated = self.controller.active_document.get_entity(entity.id)
        self.assertEqual(updated.properties["minimum"], 10)
        self.assertEqual(updated.properties["maximum"], 10)
        self.assertEqual(updated.properties["value"], 10)
        self.controller.validate_active_document()

        self.controller.update_entity_property(entity.id, "step", 0)
        self._process_events()
        updated = self.controller.active_document.get_entity(entity.id)
        self.assertEqual(updated.properties["step"], 1)
        self.controller.validate_active_document()

    def test_qspinbox_json_and_python_round_trip(self) -> None:
        entity = self.controller.create_entity_from_drop("QSpinBox", 40, 50, "form_root")
        self.controller.rename_entity(entity.id, "weight_spin")
        self.controller.update_entity_property(entity.id, "value", 7)
        self.controller.update_entity_property(entity.id, "minimum", -5)
        self.controller.update_entity_property(entity.id, "maximum", 25)
        self.controller.update_entity_property(entity.id, "step", 3)
        self.controller.update_entity_property(entity.id, "prefix", "~ ")
        self.controller.update_entity_property(entity.id, "suffix", " mm")
        before_payload = self.serializer.serialize_to_dict(self.controller.active_document)

        with managed_test_paths("tests\\_tmp_qspinbox.json", "tests\\_tmp_qspinbox.py") as (json_path, py_path):
            self.controller.save_document_to_json(str(json_path))
            self.controller.load_document(str(json_path))
            after_json = self.serializer.serialize_to_dict(self.controller.active_document)
            self.assertEqual(structure_signature(before_payload), structure_signature(after_json))

            python_source = self.controller.export_document_to_python_source()
            self.assertIn("QSpinBox", python_source)
            self.assertIn(".setMinimum(-5)", python_source)
            self.assertIn(".setMaximum(25)", python_source)
            self.assertIn(".setSingleStep(3)", python_source)
            self.assertIn(".setPrefix('~ ')", python_source)
            self.assertIn(".setSuffix(' mm')", python_source)
            self.assertIn(".setValue(7)", python_source)

            self.controller.export_document_to_python(str(py_path))
            self.controller.load_document(str(py_path))
            after_python = self.serializer.serialize_to_dict(self.controller.active_document)
            self.assertEqual(structure_signature(before_payload), structure_signature(after_python))

    @classmethod
    def _process_events(cls) -> None:
        cls._app.processEvents()


if __name__ == "__main__":
    unittest.main()
