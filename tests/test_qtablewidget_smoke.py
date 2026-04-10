from __future__ import annotations

from pathlib import Path
import unittest

from PySide6.QtWidgets import QApplication, QTableWidget

from form_constructor.controller.document_controller import DocumentController
from form_constructor.conversion.importer import PythonImporter
from form_constructor.registry.builtins import build_builtin_registry
from form_constructor.serialization.form_serializer import FormSerializer
from form_constructor.ui.main_editor.main_editor_window import MainEditorWindow
from tests.support import managed_test_paths, structure_signature


class QTableWidgetSmokeTests(unittest.TestCase):
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

    def test_qtablewidget_appears_in_palette_and_can_be_created(self) -> None:
        palette_types = {definition.type_name for definition in self.registry.list_palette_types()}
        self.assertIn("QTableWidget", palette_types)

        entity = self.controller.create_entity_from_drop("QTableWidget", 160, 170, "form_root")
        self._process_events()

        self.assertEqual(entity.type, "QTableWidget")
        self.assertEqual(self.controller.selected_entity.id, entity.id)
        view = self.window._form_window._canvas._item_views_by_id[entity.id]
        self.assertIsInstance(view.inner_widget, QTableWidget)

    def test_qtablewidget_properties_update_canvas_and_snapshot(self) -> None:
        entity = self.controller.create_entity_from_drop("QTableWidget", 160, 170, "form_root")
        self.controller.update_entity_property(entity.id, "row_count", 5)
        self.controller.update_entity_property(entity.id, "column_count", 4)
        self.controller.update_entity_property(entity.id, "horizontal_headers", ["A", "B", "C", "D"])
        self.controller.update_entity_property(entity.id, "vertical_headers", ["1", "2", "3", "4", "5"])
        self.controller.update_entity_property(entity.id, "cell_values", [["A1", "B1"], ["A2", "", "C2"]])
        self._process_events()

        updated = self.controller.active_document.get_entity(entity.id)
        self.assertEqual(updated.properties["row_count"], 5)
        self.assertEqual(updated.properties["column_count"], 4)
        self.assertEqual(updated.properties["horizontal_headers"], ["A", "B", "C", "D"])
        self.assertEqual(updated.properties["vertical_headers"], ["1", "2", "3", "4", "5"])
        self.assertEqual(updated.properties["cell_values"], [["A1", "B1"], ["A2", "", "C2"]])

        table_widget = self.window._form_window._canvas._item_views_by_id[entity.id].inner_widget
        self.assertEqual(table_widget.rowCount(), 5)
        self.assertEqual(table_widget.columnCount(), 4)
        self.assertEqual(table_widget.horizontalHeaderItem(0).text(), "A")
        self.assertEqual(table_widget.horizontalHeaderItem(3).text(), "D")
        self.assertEqual(table_widget.verticalHeaderItem(0).text(), "1")
        self.assertEqual(table_widget.verticalHeaderItem(4).text(), "5")
        self.assertEqual(table_widget.item(0, 0).text(), "A1")
        self.assertEqual(table_widget.item(0, 1).text(), "B1")
        self.assertEqual(table_widget.item(1, 0).text(), "A2")
        self.assertEqual(table_widget.item(1, 1).text(), "")
        self.assertEqual(table_widget.item(1, 2).text(), "C2")
        self.assertIn('"type": "QTableWidget"', self.controller.get_snapshot())

    def test_qtablewidget_normalization_keeps_document_valid(self) -> None:
        entity = self.controller.create_entity_from_drop("QTableWidget", 160, 170, "form_root")

        self.controller.update_entity_property(entity.id, "row_count", -4)
        self.controller.update_entity_property(entity.id, "column_count", -2)
        self.controller.update_entity_property(entity.id, "horizontal_headers", ["A", "B", "C"])
        self.controller.update_entity_property(entity.id, "vertical_headers", ["1", "2", "3"])
        self.controller.update_entity_property(entity.id, "cell_values", [["A1", "B1"], ["A2", "B2"]])
        self._process_events()

        updated = self.controller.active_document.get_entity(entity.id)
        self.assertEqual(updated.properties["row_count"], 0)
        self.assertEqual(updated.properties["column_count"], 0)
        self.assertEqual(updated.properties["horizontal_headers"], [])
        self.assertEqual(updated.properties["vertical_headers"], [])
        self.assertEqual(updated.properties["cell_values"], [])
        self.controller.validate_active_document()

        self.controller.update_entity_property(entity.id, "row_count", 2)
        self.controller.update_entity_property(entity.id, "column_count", 1)
        self.controller.update_entity_property(entity.id, "horizontal_headers", ["A", "B", "C"])
        self.controller.update_entity_property(entity.id, "vertical_headers", ["1", "2", "3"])
        self.controller.update_entity_property(entity.id, "cell_values", [["A1", "B1"], ["A2", "B2"], ["A3"]])
        self._process_events()

        updated = self.controller.active_document.get_entity(entity.id)
        self.assertEqual(updated.properties["horizontal_headers"], ["A"])
        self.assertEqual(updated.properties["vertical_headers"], ["1", "2"])
        self.assertEqual(updated.properties["cell_values"], [["A1"], ["A2"]])
        self.controller.validate_active_document()

    def test_qtablewidget_json_and_python_round_trip(self) -> None:
        entity = self.controller.create_entity_from_drop("QTableWidget", 160, 170, "form_root")
        self.controller.rename_entity(entity.id, "catalog_table")
        self.controller.update_entity_property(entity.id, "row_count", 3)
        self.controller.update_entity_property(entity.id, "column_count", 4)
        self.controller.update_entity_property(entity.id, "horizontal_headers", ["Код", "Имя", "Группа", "Статус"])
        self.controller.update_entity_property(entity.id, "vertical_headers", ["1", "2", "3"])
        self.controller.update_entity_property(
            entity.id,
            "cell_values",
            [["001", "Болт", "Метизы"], ["002", "Гайка", ""], ["003"]],
        )
        before_payload = self.serializer.serialize_to_dict(self.controller.active_document)

        with managed_test_paths("tests\\_tmp_qtablewidget.json", "tests\\_tmp_qtablewidget.py") as (
            json_path,
            py_path,
        ):
            self.controller.save_document_to_json(str(json_path))
            self.controller.load_document(str(json_path))
            after_json = self.serializer.serialize_to_dict(self.controller.active_document)
            self.assertEqual(structure_signature(before_payload), structure_signature(after_json))

            python_source = self.controller.export_document_to_python_source()
            self.assertIn("QTableWidget", python_source)
            self.assertIn(".setRowCount(3)", python_source)
            self.assertIn(".setColumnCount(4)", python_source)
            self.assertIn(".setHorizontalHeaderLabels(['Код', 'Имя', 'Группа', 'Статус'])", python_source)
            self.assertIn(".setVerticalHeaderLabels(['1', '2', '3'])", python_source)

            self.assertIn("QTableWidgetItem", python_source)
            self.assertIn(".setItem(0, 0, QTableWidgetItem('001'))", python_source)
            self.assertIn(".setItem(1, 2, QTableWidgetItem(''))", python_source)

            self.controller.export_document_to_python(str(py_path))
            self.controller.load_document(str(py_path))
            after_python = self.serializer.serialize_to_dict(self.controller.active_document)
            self.assertEqual(structure_signature(before_payload), structure_signature(after_python))

    def test_qtablewidget_supports_nested_supported_container_contexts(self) -> None:
        group_box = self.controller.create_entity_from_drop("QGroupBox", 20, 20, "form_root")
        table_in_group = self.controller.create_entity_from_drop("QTableWidget", 10, 15, group_box.id)

        tab_widget = self.controller.create_entity_from_drop("QTabWidget", 20, 140, "form_root")
        tab_page = self.controller.active_document.get_tab_pages(tab_widget.id)[0]
        table_in_tab = self.controller.create_entity_from_drop("QTableWidget", 12, 16, tab_page.id)

        scroll_area = self.controller.create_entity_from_drop("QScrollArea", 260, 20, "form_root")
        scroll_content = self.controller.active_document.get_scroll_content(scroll_area.id)
        table_in_scroll = self.controller.create_entity_from_drop("QTableWidget", 8, 10, scroll_content.id)

        splitter = self.controller.create_entity_from_drop("QSplitter", 260, 180, "form_root")
        splitter_pane = self.controller.active_document.get_splitter_panes(splitter.id)[0]
        table_in_splitter = self.controller.create_entity_from_drop("QTableWidget", 6, 8, splitter_pane.id)
        self._process_events()

        self.assertEqual(self.controller.active_document.get_entity(table_in_group.id).parent_id, group_box.id)
        self.assertEqual(self.controller.active_document.get_entity(table_in_tab.id).parent_id, tab_page.id)
        self.assertEqual(self.controller.active_document.get_entity(table_in_scroll.id).parent_id, scroll_content.id)
        self.assertEqual(self.controller.active_document.get_entity(table_in_splitter.id).parent_id, splitter_pane.id)
        self.controller.validate_active_document()

    def test_qtablewidget_import_parses_inline_cell_content(self) -> None:
        importer = PythonImporter(self.registry)
        source = """
import sys
from PySide6.QtWidgets import QApplication, QWidget, QTableWidget, QTableWidgetItem

class GeneratedWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        self.setObjectName("form")
        self.resize(320, 200)
        self.table_widget_1 = QTableWidget(self)
        self.table_widget_1.setObjectName("table_widget_1")
        self.table_widget_1.setGeometry(10, 10, 220, 140)
        self.table_widget_1.setRowCount(2)
        self.table_widget_1.setColumnCount(2)
        self.table_widget_1.setItem(0, 0, QTableWidgetItem("A1"))
        self.table_widget_1.setItem(1, 1, QTableWidgetItem("B2"))
"""
        document = importer.import_from_code(source)
        entity = next(item for item in document.entities_by_id.values() if item.type == "QTableWidget")
        self.assertEqual(entity.properties["cell_values"], [["A1"], ["", "B2"]])

    @classmethod
    def _process_events(cls) -> None:
        cls._app.processEvents()


if __name__ == "__main__":
    unittest.main()
