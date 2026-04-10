from __future__ import annotations

from pathlib import Path
import unittest

from PySide6.QtWidgets import QApplication, QTimeEdit

from form_constructor.controller.document_controller import DocumentController
from form_constructor.conversion.importer import PythonImporter
from form_constructor.registry.builtins import build_builtin_registry
from form_constructor.serialization.form_serializer import FormSerializer
from form_constructor.ui.main_editor.main_editor_window import MainEditorWindow
from tests.support import managed_test_paths, structure_signature


class QTimeEditSmokeTests(unittest.TestCase):
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

    def test_qtimeedit_appears_in_palette_and_can_be_created(self) -> None:
        palette_types = {definition.type_name for definition in self.registry.list_palette_types()}
        self.assertIn("QTimeEdit", palette_types)

        entity = self.controller.create_entity_from_drop("QTimeEdit", 160, 170, "form_root")
        self._process_events()

        self.assertEqual(entity.type, "QTimeEdit")
        self.assertEqual(self.controller.selected_entity.id, entity.id)
        view = self.window._form_window._canvas._item_views_by_id[entity.id]
        self.assertIsInstance(view.inner_widget, QTimeEdit)

    def test_qtimeedit_properties_update_canvas_and_snapshot(self) -> None:
        entity = self.controller.create_entity_from_drop("QTimeEdit", 160, 170, "form_root")
        self.controller.update_entity_property(entity.id, "minimum_time", "08:00:00")
        self.controller.update_entity_property(entity.id, "maximum_time", "18:00:00")
        self.controller.update_entity_property(entity.id, "time", "09:30:00")
        self.controller.update_entity_property(entity.id, "display_format", "HH:mm")
        self._process_events()

        updated = self.controller.active_document.get_entity(entity.id)
        self.assertEqual(updated.properties["minimum_time"], "08:00:00")
        self.assertEqual(updated.properties["maximum_time"], "18:00:00")
        self.assertEqual(updated.properties["time"], "09:30:00")
        self.assertEqual(updated.properties["display_format"], "HH:mm")

        time_widget = self.window._form_window._canvas._item_views_by_id[entity.id].inner_widget
        self.assertEqual(time_widget.minimumTime().toString("HH:mm:ss"), "08:00:00")
        self.assertEqual(time_widget.maximumTime().toString("HH:mm:ss"), "18:00:00")
        self.assertEqual(time_widget.time().toString("HH:mm:ss"), "09:30:00")
        self.assertEqual(time_widget.displayFormat(), "HH:mm")
        self.assertIn('"type": "QTimeEdit"', self.controller.get_snapshot())

    def test_qtimeedit_range_normalization_keeps_document_valid(self) -> None:
        entity = self.controller.create_entity_from_drop("QTimeEdit", 160, 170, "form_root")

        self.controller.update_entity_property(entity.id, "minimum_time", "20:00:00")
        self.controller.update_entity_property(entity.id, "maximum_time", "18:00:00")
        self._process_events()

        updated = self.controller.active_document.get_entity(entity.id)
        self.assertEqual(updated.properties["minimum_time"], "18:00:00")
        self.assertEqual(updated.properties["maximum_time"], "18:00:00")
        self.assertEqual(updated.properties["time"], "18:00:00")
        self.controller.validate_active_document()

        self.controller.update_entity_property(entity.id, "minimum_time", "08:00:00")
        self.controller.update_entity_property(entity.id, "maximum_time", "18:00:00")
        self.controller.update_entity_property(entity.id, "time", "22:30:00")
        self._process_events()

        updated = self.controller.active_document.get_entity(entity.id)
        self.assertEqual(updated.properties["time"], "18:00:00")
        self.controller.validate_active_document()

    def test_qtimeedit_json_and_python_round_trip(self) -> None:
        entity = self.controller.create_entity_from_drop("QTimeEdit", 160, 170, "form_root")
        self.controller.rename_entity(entity.id, "start_time")
        self.controller.update_entity_property(entity.id, "minimum_time", "08:00:00")
        self.controller.update_entity_property(entity.id, "maximum_time", "18:00:00")
        self.controller.update_entity_property(entity.id, "time", "09:30:00")
        self.controller.update_entity_property(entity.id, "display_format", "HH:mm")
        before_payload = self.serializer.serialize_to_dict(self.controller.active_document)

        with managed_test_paths("tests\\_tmp_qtimeedit.json", "tests\\_tmp_qtimeedit.py") as (json_path, py_path):
            self.controller.save_document_to_json(str(json_path))
            self.controller.load_document(str(json_path))
            after_json = self.serializer.serialize_to_dict(self.controller.active_document)
            self.assertEqual(
                structure_signature(before_payload),
                structure_signature(after_json),
            )

            python_source = self.controller.export_document_to_python_source()
            self.assertIn("QTimeEdit", python_source)
            self.assertIn("from PySide6.QtCore import QTime", python_source)
            self.assertIn(".setMinimumTime(QTime(8, 0, 0))", python_source)
            self.assertIn(".setMaximumTime(QTime(18, 0, 0))", python_source)
            self.assertIn(".setTime(QTime(9, 30, 0))", python_source)
            self.assertIn(".setDisplayFormat('HH:mm')", python_source)

            self.controller.export_document_to_python(str(py_path))
            self.controller.load_document(str(py_path))
            after_python = self.serializer.serialize_to_dict(self.controller.active_document)
            self.assertEqual(
                structure_signature(before_payload),
                structure_signature(after_python),
            )

    def test_qtimeedit_supports_nested_supported_container_contexts(self) -> None:
        group_box = self.controller.create_entity_from_drop("QGroupBox", 20, 20, "form_root")
        time_in_group = self.controller.create_entity_from_drop("QTimeEdit", 10, 15, group_box.id)

        tab_widget = self.controller.create_entity_from_drop("QTabWidget", 20, 140, "form_root")
        tab_page = self.controller.active_document.get_tab_pages(tab_widget.id)[0]
        time_in_tab = self.controller.create_entity_from_drop("QTimeEdit", 12, 16, tab_page.id)

        scroll_area = self.controller.create_entity_from_drop("QScrollArea", 260, 20, "form_root")
        scroll_content = self.controller.active_document.get_scroll_content(scroll_area.id)
        time_in_scroll = self.controller.create_entity_from_drop("QTimeEdit", 8, 10, scroll_content.id)

        splitter = self.controller.create_entity_from_drop("QSplitter", 260, 180, "form_root")
        splitter_pane = self.controller.active_document.get_splitter_panes(splitter.id)[0]
        time_in_splitter = self.controller.create_entity_from_drop("QTimeEdit", 6, 8, splitter_pane.id)
        self._process_events()

        self.assertEqual(self.controller.active_document.get_entity(time_in_group.id).parent_id, group_box.id)
        self.assertEqual(self.controller.active_document.get_entity(time_in_tab.id).parent_id, tab_page.id)
        self.assertEqual(self.controller.active_document.get_entity(time_in_scroll.id).parent_id, scroll_content.id)
        self.assertEqual(self.controller.active_document.get_entity(time_in_splitter.id).parent_id, splitter_pane.id)
        self.controller.validate_active_document()

    def test_qtimeedit_import_preserves_display_format(self) -> None:
        importer = PythonImporter(self.registry)
        source = """
import sys
from PySide6.QtWidgets import QApplication, QWidget, QTimeEdit
from PySide6.QtCore import QTime

class GeneratedWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        self.setObjectName("form")
        self.resize(320, 200)
        self.time_edit_1 = QTimeEdit(self)
        self.time_edit_1.setObjectName("time_edit_1")
        self.time_edit_1.setGeometry(10, 10, 120, 26)
        self.time_edit_1.setMinimumTime(QTime(8, 0, 0))
        self.time_edit_1.setMaximumTime(QTime(18, 0, 0))
        self.time_edit_1.setTime(QTime(9, 30, 0))
        self.time_edit_1.setDisplayFormat("HH:mm")
"""
        document = importer.import_from_code(source)
        entity = document.get_root_entities()[0]
        self.assertEqual(entity.properties["display_format"], "HH:mm")

    @classmethod
    def _process_events(cls) -> None:
        cls._app.processEvents()


if __name__ == "__main__":
    unittest.main()
