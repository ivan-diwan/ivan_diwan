from __future__ import annotations

from pathlib import Path
import unittest

from PySide6.QtWidgets import QApplication, QTreeWidget

from form_constructor.controller.document_controller import DocumentController
from form_constructor.conversion.importer import PythonImporter
from form_constructor.registry.builtins import build_builtin_registry
from form_constructor.serialization.form_serializer import FormSerializer
from form_constructor.ui.main_editor.main_editor_window import MainEditorWindow
from tests.support import managed_test_paths, structure_signature


class QTreeWidgetSmokeTests(unittest.TestCase):
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

    def test_qtreewidget_appears_in_palette_and_can_be_created(self) -> None:
        palette_types = {definition.type_name for definition in self.registry.list_palette_types()}
        self.assertIn("QTreeWidget", palette_types)

        entity = self.controller.create_entity_from_drop("QTreeWidget", 160, 170, "form_root")
        self._process_events()

        self.assertEqual(entity.type, "QTreeWidget")
        self.assertEqual(self.controller.selected_entity.id, entity.id)
        view = self.window._form_window._canvas._item_views_by_id[entity.id]
        self.assertIsInstance(view.inner_widget, QTreeWidget)

    def test_qtreewidget_properties_update_canvas_and_snapshot(self) -> None:
        entity = self.controller.create_entity_from_drop("QTreeWidget", 160, 170, "form_root")
        self.controller.update_entity_property(entity.id, "column_count", 3)
        self.controller.update_entity_property(entity.id, "header_labels", ["Name", "Type", "Value"])
        self.controller.update_entity_property(
            entity.id,
            "tree_items",
            [
                {
                    "texts": ["Materials", "Group"],
                    "children": [
                        {"texts": ["Bolt", "Item", "M8"], "children": []},
                        {"texts": ["Nut", "Item", ""], "children": []},
                    ],
                },
                {
                    "texts": ["Services", "Group"],
                    "children": [],
                },
            ],
        )
        self._process_events()

        updated = self.controller.active_document.get_entity(entity.id)
        self.assertEqual(updated.properties["column_count"], 3)
        self.assertEqual(updated.properties["header_labels"], ["Name", "Type", "Value"])
        self.assertEqual(
            updated.properties["tree_items"],
            [
                {
                    "texts": ["Materials", "Group"],
                    "children": [
                        {"texts": ["Bolt", "Item", "M8"], "children": []},
                        {"texts": ["Nut", "Item", ""], "children": []},
                    ],
                },
                {
                    "texts": ["Services", "Group"],
                    "children": [],
                },
            ],
        )

        tree_widget = self.window._form_window._canvas._item_views_by_id[entity.id].inner_widget
        self.assertEqual(tree_widget.columnCount(), 3)
        self.assertEqual(tree_widget.headerItem().text(0), "Name")
        self.assertEqual(tree_widget.headerItem().text(1), "Type")
        self.assertEqual(tree_widget.headerItem().text(2), "Value")
        self.assertEqual(tree_widget.topLevelItemCount(), 2)
        self.assertEqual(tree_widget.topLevelItem(0).text(0), "Materials")
        self.assertEqual(tree_widget.topLevelItem(0).childCount(), 2)
        self.assertEqual(tree_widget.topLevelItem(0).child(0).text(0), "Bolt")
        self.assertEqual(tree_widget.topLevelItem(0).child(0).text(2), "M8")
        self.assertEqual(tree_widget.topLevelItem(0).child(1).text(0), "Nut")
        self.assertEqual(tree_widget.topLevelItem(1).text(0), "Services")
        self.assertIn('"type": "QTreeWidget"', self.controller.get_snapshot())

    def test_qtreewidget_normalization_keeps_document_valid(self) -> None:
        entity = self.controller.create_entity_from_drop("QTreeWidget", 160, 170, "form_root")

        self.controller.update_entity_property(entity.id, "column_count", -3)
        self.controller.update_entity_property(entity.id, "header_labels", ["A", "B", "C"])
        self.controller.update_entity_property(
            entity.id,
            "tree_items",
            [{"texts": ["A", "B"], "children": [{"texts": ["Child"], "children": []}]}],
        )
        self._process_events()

        updated = self.controller.active_document.get_entity(entity.id)
        self.assertEqual(updated.properties["column_count"], 0)
        self.assertEqual(updated.properties["header_labels"], [])
        self.assertEqual(
            updated.properties["tree_items"],
            [{"texts": [], "children": [{"texts": [], "children": []}]}],
        )
        self.controller.validate_active_document()

        self.controller.update_entity_property(entity.id, "column_count", 2)
        self.controller.update_entity_property(entity.id, "header_labels", ["A", "B", "C", "D"])
        self.controller.update_entity_property(
            entity.id,
            "tree_items",
            [
                {
                    "texts": ["Node", "Type", "Ignored"],
                    "children": [
                        {"texts": ["Child", "Leaf", "Ignored"], "children": []},
                    ],
                }
            ],
        )
        self._process_events()

        updated = self.controller.active_document.get_entity(entity.id)
        self.assertEqual(updated.properties["header_labels"], ["A", "B"])
        self.assertEqual(
            updated.properties["tree_items"],
            [
                {
                    "texts": ["Node", "Type"],
                    "children": [
                        {"texts": ["Child", "Leaf"], "children": []},
                    ],
                }
            ],
        )
        self.controller.validate_active_document()

    def test_qtreewidget_json_and_python_round_trip(self) -> None:
        entity = self.controller.create_entity_from_drop("QTreeWidget", 160, 170, "form_root")
        self.controller.rename_entity(entity.id, "materials_tree")
        self.controller.update_entity_property(entity.id, "column_count", 3)
        self.controller.update_entity_property(entity.id, "header_labels", ["Section", "Type", "Value"])
        self.controller.update_entity_property(
            entity.id,
            "tree_items",
            [
                {
                    "texts": ["Materials", "Group"],
                    "children": [
                        {"texts": ["Bolt", "Item", "M8"], "children": []},
                        {"texts": ["Nut", "Item", ""], "children": []},
                    ],
                }
            ],
        )
        before_payload = self.serializer.serialize_to_dict(self.controller.active_document)

        with managed_test_paths("tests\\_tmp_qtreewidget.json", "tests\\_tmp_qtreewidget.py") as (
            json_path,
            py_path,
        ):
            self.controller.save_document_to_json(str(json_path))
            self.controller.load_document(str(json_path))
            after_json = self.serializer.serialize_to_dict(self.controller.active_document)
            self.assertEqual(structure_signature(before_payload), structure_signature(after_json))

            python_source = self.controller.export_document_to_python_source()
            self.assertIn("QTreeWidget", python_source)
            self.assertIn(".setColumnCount(3)", python_source)
            self.assertIn(".setHeaderLabels(['Section', 'Type', 'Value'])", python_source)
            self.assertIn("QTreeWidgetItem", python_source)
            self.assertIn("addTopLevelItem", python_source)
            self.assertIn("addChild", python_source)

            self.controller.export_document_to_python(str(py_path))
            self.controller.load_document(str(py_path))
            after_python = self.serializer.serialize_to_dict(self.controller.active_document)
            self.assertEqual(structure_signature(before_payload), structure_signature(after_python))

    def test_qtreewidget_supports_nested_supported_container_contexts(self) -> None:
        group_box = self.controller.create_entity_from_drop("QGroupBox", 20, 20, "form_root")
        tree_in_group = self.controller.create_entity_from_drop("QTreeWidget", 10, 15, group_box.id)

        tab_widget = self.controller.create_entity_from_drop("QTabWidget", 20, 140, "form_root")
        tab_page = self.controller.active_document.get_tab_pages(tab_widget.id)[0]
        tree_in_tab = self.controller.create_entity_from_drop("QTreeWidget", 12, 16, tab_page.id)

        scroll_area = self.controller.create_entity_from_drop("QScrollArea", 260, 20, "form_root")
        scroll_content = self.controller.active_document.get_scroll_content(scroll_area.id)
        tree_in_scroll = self.controller.create_entity_from_drop("QTreeWidget", 8, 10, scroll_content.id)

        splitter = self.controller.create_entity_from_drop("QSplitter", 260, 180, "form_root")
        splitter_pane = self.controller.active_document.get_splitter_panes(splitter.id)[0]
        tree_in_splitter = self.controller.create_entity_from_drop("QTreeWidget", 6, 8, splitter_pane.id)
        self._process_events()

        self.assertEqual(self.controller.active_document.get_entity(tree_in_group.id).parent_id, group_box.id)
        self.assertEqual(self.controller.active_document.get_entity(tree_in_tab.id).parent_id, tab_page.id)
        self.assertEqual(self.controller.active_document.get_entity(tree_in_scroll.id).parent_id, scroll_content.id)
        self.assertEqual(self.controller.active_document.get_entity(tree_in_splitter.id).parent_id, splitter_pane.id)
        self.controller.validate_active_document()

    def test_qtreewidget_import_parses_tree_items_hierarchy(self) -> None:
        importer = PythonImporter(self.registry)
        source = """
import sys
from PySide6.QtWidgets import QApplication, QWidget, QTreeWidget, QTreeWidgetItem

class GeneratedWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        self.setObjectName("form")
        self.resize(320, 200)
        self.tree_widget_1 = QTreeWidget(self)
        self.tree_widget_1.setObjectName("tree_widget_1")
        self.tree_widget_1.setGeometry(10, 10, 220, 140)
        self.tree_widget_1.setColumnCount(2)
        self.tree_widget_1.setHeaderLabels(["Name", "Type"])
        root_item = QTreeWidgetItem(["Materials", "Group"])
        child_item = QTreeWidgetItem(["Bolt", "Item"])
        root_item.addChild(child_item)
        self.tree_widget_1.addTopLevelItem(root_item)
"""
        document = importer.import_from_code(source)
        entity = next(item for item in document.entities_by_id.values() if item.type == "QTreeWidget")
        self.assertEqual(
            entity.properties["tree_items"],
            [
                {
                    "texts": ["Materials", "Group"],
                    "children": [
                        {"texts": ["Bolt", "Item"], "children": []},
                    ],
                }
            ],
        )

    @classmethod
    def _process_events(cls) -> None:
        cls._app.processEvents()


if __name__ == "__main__":
    unittest.main()
