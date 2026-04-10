from __future__ import annotations

from pathlib import Path
import unittest

from PySide6.QtGui import QStandardItemModel
from PySide6.QtWidgets import QApplication, QTreeView

from form_constructor.controller.document_controller import DocumentController
from form_constructor.registry.builtins import build_builtin_registry
from form_constructor.serialization.form_serializer import FormSerializer
from form_constructor.ui.main_editor.main_editor_window import MainEditorWindow
from tests.support import managed_test_paths, structure_signature


class QTreeViewSmokeTests(unittest.TestCase):
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

    def test_qtreeview_appears_in_palette_and_can_be_created(self) -> None:
        palette_types = {definition.type_name for definition in self.registry.list_palette_types()}
        self.assertIn("QTreeView", palette_types)

        entity = self.controller.create_entity_from_drop("QTreeView", 160, 170, "form_root")
        self._process_events()

        self.assertEqual(entity.type, "QTreeView")
        self.assertEqual(self.controller.selected_entity.id, entity.id)
        view = self.window._form_window._canvas._item_views_by_id[entity.id]
        self.assertIsInstance(view.inner_widget, QTreeView)

    def test_qtreeview_properties_update_canvas_and_snapshot(self) -> None:
        entity = self.controller.create_entity_from_drop("QTreeView", 160, 170, "form_root")
        self.controller.update_entity_property(entity.id, "header_labels", ["A", "B", "C"])
        self._process_events()

        updated = self.controller.active_document.get_entity(entity.id)
        self.assertEqual(updated.properties["header_labels"], ["A", "B", "C"])

        tree_view = self.window._form_window._canvas._item_views_by_id[entity.id].inner_widget
        self.assertIsInstance(tree_view.model(), QStandardItemModel)
        model = tree_view.model()
        self.assertEqual(model.horizontalHeaderItem(0).text(), "A")
        self.assertEqual(model.horizontalHeaderItem(1).text(), "B")
        self.assertEqual(model.horizontalHeaderItem(2).text(), "C")
        self.assertIn('"type": "QTreeView"', self.controller.get_snapshot())

    def test_qtreeview_normalization_keeps_document_valid(self) -> None:
        entity = self.controller.create_entity_from_drop("QTreeView", 160, 170, "form_root")

        self.controller.update_entity_property(entity.id, "header_labels", ("A", 2, None))
        self._process_events()

        updated = self.controller.active_document.get_entity(entity.id)
        self.assertEqual(updated.properties["header_labels"], ["A", "2", "None"])
        self.controller.validate_active_document()

    def test_qtreeview_json_and_python_round_trip(self) -> None:
        entity = self.controller.create_entity_from_drop("QTreeView", 160, 170, "form_root")
        self.controller.rename_entity(entity.id, "catalog_tree")
        self.controller.update_entity_property(entity.id, "header_labels", ["Первый", "Второй"])
        before_payload = self.serializer.serialize_to_dict(self.controller.active_document)

        with managed_test_paths("tests\\_tmp_qtreeview.json", "tests\\_tmp_qtreeview.py") as (json_path, py_path):
            self.controller.save_document_to_json(str(json_path))
            self.controller.load_document(str(json_path))
            after_json = self.serializer.serialize_to_dict(self.controller.active_document)
            self.assertEqual(structure_signature(before_payload), structure_signature(after_json))

            python_source = self.controller.export_document_to_python_source()
            self.assertIn("QTreeView", python_source)
            self.assertIn("QStandardItemModel", python_source)
            self.assertIn(".setHorizontalHeaderLabels(['Первый', 'Второй'])", python_source)
            self.assertIn(".setModel(", python_source)

            self.controller.export_document_to_python(str(py_path))
            self.controller.load_document(str(py_path))
            after_python = self.serializer.serialize_to_dict(self.controller.active_document)
            self.assertEqual(structure_signature(before_payload), structure_signature(after_python))

    def test_qtreeview_supports_nested_supported_container_contexts(self) -> None:
        group_box = self.controller.create_entity_from_drop("QGroupBox", 20, 20, "form_root")
        view_in_group = self.controller.create_entity_from_drop("QTreeView", 10, 15, group_box.id)

        tab_widget = self.controller.create_entity_from_drop("QTabWidget", 20, 140, "form_root")
        tab_page = self.controller.active_document.get_tab_pages(tab_widget.id)[0]
        view_in_tab = self.controller.create_entity_from_drop("QTreeView", 12, 16, tab_page.id)

        scroll_area = self.controller.create_entity_from_drop("QScrollArea", 260, 20, "form_root")
        scroll_content = self.controller.active_document.get_scroll_content(scroll_area.id)
        view_in_scroll = self.controller.create_entity_from_drop("QTreeView", 8, 10, scroll_content.id)

        splitter = self.controller.create_entity_from_drop("QSplitter", 260, 180, "form_root")
        splitter_pane = self.controller.active_document.get_splitter_panes(splitter.id)[0]
        view_in_splitter = self.controller.create_entity_from_drop("QTreeView", 6, 8, splitter_pane.id)
        self._process_events()

        self.assertEqual(self.controller.active_document.get_entity(view_in_group.id).parent_id, group_box.id)
        self.assertEqual(self.controller.active_document.get_entity(view_in_tab.id).parent_id, tab_page.id)
        self.assertEqual(self.controller.active_document.get_entity(view_in_scroll.id).parent_id, scroll_content.id)
        self.assertEqual(self.controller.active_document.get_entity(view_in_splitter.id).parent_id, splitter_pane.id)
        self.controller.validate_active_document()

    @classmethod
    def _process_events(cls) -> None:
        cls._app.processEvents()


if __name__ == "__main__":
    unittest.main()
