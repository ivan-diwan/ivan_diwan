from __future__ import annotations

from pathlib import Path
import unittest

from PySide6.QtWidgets import QApplication, QDateTimeEdit

from form_constructor.controller.document_controller import DocumentController
from form_constructor.conversion.importer import PythonImporter
from form_constructor.registry.builtins import build_builtin_registry
from form_constructor.serialization.form_serializer import FormSerializer
from form_constructor.ui.main_editor.main_editor_window import MainEditorWindow
from tests.support import managed_test_paths, structure_signature


class QDateTimeEditSmokeTests(unittest.TestCase):
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

    def test_qdatetimeedit_appears_in_palette_and_can_be_created(self) -> None:
        palette_types = {definition.type_name for definition in self.registry.list_palette_types()}
        self.assertIn("QDateTimeEdit", palette_types)

        entity = self.controller.create_entity_from_drop("QDateTimeEdit", 160, 170, "form_root")
        self._process_events()

        self.assertEqual(entity.type, "QDateTimeEdit")
        self.assertEqual(self.controller.selected_entity.id, entity.id)
        view = self.window._form_window._canvas._item_views_by_id[entity.id]
        self.assertIsInstance(view.inner_widget, QDateTimeEdit)

    def test_qdatetimeedit_properties_update_canvas_and_snapshot(self) -> None:
        entity = self.controller.create_entity_from_drop("QDateTimeEdit", 160, 170, "form_root")
        self.controller.update_entity_property(entity.id, "minimum_datetime", "2020-01-01 00:00:00")
        self.controller.update_entity_property(entity.id, "maximum_datetime", "2030-12-31 23:59:59")
        self.controller.update_entity_property(entity.id, "datetime", "2026-04-08 09:30:00")
        self._process_events()

        updated = self.controller.active_document.get_entity(entity.id)
        self.assertEqual(updated.properties["minimum_datetime"], "2020-01-01 00:00:00")
        self.assertEqual(updated.properties["maximum_datetime"], "2030-12-31 23:59:59")
        self.assertEqual(updated.properties["datetime"], "2026-04-08 09:30:00")

        datetime_widget = self.window._form_window._canvas._item_views_by_id[entity.id].inner_widget
        self.assertEqual(datetime_widget.minimumDateTime().toString("yyyy-MM-dd HH:mm:ss"), "2020-01-01 00:00:00")
        self.assertEqual(datetime_widget.maximumDateTime().toString("yyyy-MM-dd HH:mm:ss"), "2030-12-31 23:59:59")
        self.assertEqual(datetime_widget.dateTime().toString("yyyy-MM-dd HH:mm:ss"), "2026-04-08 09:30:00")
        self.assertIn('"type": "QDateTimeEdit"', self.controller.get_snapshot())

    def test_qdatetimeedit_range_normalization_keeps_document_valid(self) -> None:
        entity = self.controller.create_entity_from_drop("QDateTimeEdit", 160, 170, "form_root")

        self.controller.update_entity_property(entity.id, "minimum_datetime", "2035-01-01 00:00:00")
        self.controller.update_entity_property(entity.id, "maximum_datetime", "2030-01-01 00:00:00")
        self._process_events()

        updated = self.controller.active_document.get_entity(entity.id)
        self.assertEqual(updated.properties["minimum_datetime"], "2030-01-01 00:00:00")
        self.assertEqual(updated.properties["maximum_datetime"], "2030-01-01 00:00:00")
        self.assertEqual(updated.properties["datetime"], "2030-01-01 00:00:00")
        self.controller.validate_active_document()

        self.controller.update_entity_property(entity.id, "minimum_datetime", "2025-01-01 00:00:00")
        self.controller.update_entity_property(entity.id, "maximum_datetime", "2025-12-31 23:59:59")
        self.controller.update_entity_property(entity.id, "datetime", "2026-04-08 09:30:00")
        self._process_events()

        updated = self.controller.active_document.get_entity(entity.id)
        self.assertEqual(updated.properties["datetime"], "2025-12-31 23:59:59")
        self.controller.validate_active_document()

    def test_qdatetimeedit_json_and_python_round_trip(self) -> None:
        entity = self.controller.create_entity_from_drop("QDateTimeEdit", 160, 170, "form_root")
        self.controller.rename_entity(entity.id, "start_datetime")
        self.controller.update_entity_property(entity.id, "minimum_datetime", "2020-01-01 00:00:00")
        self.controller.update_entity_property(entity.id, "maximum_datetime", "2030-12-31 23:59:59")
        self.controller.update_entity_property(entity.id, "datetime", "2026-04-08 09:30:00")
        before_payload = self.serializer.serialize_to_dict(self.controller.active_document)

        with managed_test_paths(
            "tests\\_tmp_qdatetimeedit.json",
            "tests\\_tmp_qdatetimeedit.py",
        ) as (json_path, py_path):
            self.controller.save_document_to_json(str(json_path))
            self.controller.load_document(str(json_path))
            after_json = self.serializer.serialize_to_dict(self.controller.active_document)
            self.assertEqual(structure_signature(before_payload), structure_signature(after_json))

            python_source = self.controller.export_document_to_python_source()
            self.assertIn("QDateTimeEdit", python_source)
            self.assertIn("from PySide6.QtCore import QDate, QDateTime, QTime", python_source)
            self.assertIn(
                ".setMinimumDateTime(QDateTime(QDate(2020, 1, 1), QTime(0, 0, 0)))",
                python_source,
            )
            self.assertIn(
                ".setMaximumDateTime(QDateTime(QDate(2030, 12, 31), QTime(23, 59, 59)))",
                python_source,
            )
            self.assertIn(
                ".setDateTime(QDateTime(QDate(2026, 4, 8), QTime(9, 30, 0)))",
                python_source,
            )

            self.controller.export_document_to_python(str(py_path))
            self.controller.load_document(str(py_path))
            after_python = self.serializer.serialize_to_dict(self.controller.active_document)
            self.assertEqual(structure_signature(before_payload), structure_signature(after_python))

    def test_qdatetimeedit_supports_nested_supported_container_contexts(self) -> None:
        group_box = self.controller.create_entity_from_drop("QGroupBox", 20, 20, "form_root")
        datetime_in_group = self.controller.create_entity_from_drop("QDateTimeEdit", 10, 15, group_box.id)

        tab_widget = self.controller.create_entity_from_drop("QTabWidget", 20, 140, "form_root")
        tab_page = self.controller.active_document.get_tab_pages(tab_widget.id)[0]
        datetime_in_tab = self.controller.create_entity_from_drop("QDateTimeEdit", 12, 16, tab_page.id)

        scroll_area = self.controller.create_entity_from_drop("QScrollArea", 260, 20, "form_root")
        scroll_content = self.controller.active_document.get_scroll_content(scroll_area.id)
        datetime_in_scroll = self.controller.create_entity_from_drop("QDateTimeEdit", 8, 10, scroll_content.id)

        splitter = self.controller.create_entity_from_drop("QSplitter", 260, 180, "form_root")
        splitter_pane = self.controller.active_document.get_splitter_panes(splitter.id)[0]
        datetime_in_splitter = self.controller.create_entity_from_drop("QDateTimeEdit", 6, 8, splitter_pane.id)
        self._process_events()

        self.assertEqual(self.controller.active_document.get_entity(datetime_in_group.id).parent_id, group_box.id)
        self.assertEqual(self.controller.active_document.get_entity(datetime_in_tab.id).parent_id, tab_page.id)
        self.assertEqual(self.controller.active_document.get_entity(datetime_in_scroll.id).parent_id, scroll_content.id)
        self.assertEqual(self.controller.active_document.get_entity(datetime_in_splitter.id).parent_id, splitter_pane.id)
        self.controller.validate_active_document()

    def test_qdatetimeedit_import_rejects_display_format_for_current_version(self) -> None:
        importer = PythonImporter(self.registry)
        source = """
import sys
from PySide6.QtWidgets import QApplication, QWidget, QDateTimeEdit
from PySide6.QtCore import QDate, QDateTime, QTime

class GeneratedWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        self.setObjectName("form")
        self.resize(320, 200)
        self.datetime_edit_1 = QDateTimeEdit(self)
        self.datetime_edit_1.setObjectName("datetime_edit_1")
        self.datetime_edit_1.setGeometry(10, 10, 160, 26)
        self.datetime_edit_1.setMinimumDateTime(QDateTime(QDate(2020, 1, 1), QTime(0, 0, 0)))
        self.datetime_edit_1.setMaximumDateTime(QDateTime(QDate(2030, 12, 31), QTime(23, 59, 59)))
        self.datetime_edit_1.setDateTime(QDateTime(QDate(2026, 4, 8), QTime(9, 30, 0)))
        self.datetime_edit_1.setDisplayFormat("yyyy-MM-dd HH:mm")
"""
        with self.assertRaisesRegex(ValueError, "display format import is not supported"):
            importer.import_from_code(source)

    @classmethod
    def _process_events(cls) -> None:
        cls._app.processEvents()


if __name__ == "__main__":
    unittest.main()
