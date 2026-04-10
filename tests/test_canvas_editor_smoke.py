from __future__ import annotations

import unittest

from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QApplication, QWidget

from form_constructor.controller.document_controller import DocumentController
from form_constructor.registry.builtins import build_builtin_registry
from form_constructor.ui.main_editor.main_editor_window import MainEditorWindow


class CanvasEditorSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.controller = DocumentController(build_builtin_registry())
        self.window = MainEditorWindow(self.controller)
        self.window.show()
        self._process_events()
        self.controller.new_document(width=900, height=700)
        self._process_events()
        self.canvas = self.window._form_window._canvas

    def tearDown(self) -> None:
        self.window.close()
        self._process_events()

    def test_get_visual_parent_for_entity_handles_supported_contexts(self) -> None:
        frame = self.controller.create_entity_from_drop("QFrame", 20, 20, "form_root")
        label_in_frame = self.controller.create_entity_from_drop("QLabel", 10, 12, frame.id)

        tab_widget = self.controller.create_entity_from_drop("QTabWidget", 200, 20, "form_root")
        tab_page = self.controller.active_document.get_tab_pages(tab_widget.id)[0]
        label_in_tab = self.controller.create_entity_from_drop("QLabel", 14, 16, tab_page.id)

        scroll_area = self.controller.create_entity_from_drop("QScrollArea", 20, 220, "form_root")
        content = self.controller.active_document.get_scroll_content(scroll_area.id)
        label_in_scroll = self.controller.create_entity_from_drop("QLabel", 18, 20, content.id)

        splitter = self.controller.create_entity_from_drop("QSplitter", 420, 20, "form_root")
        pane = self.controller.active_document.get_splitter_panes(splitter.id)[0]
        label_in_splitter = self.controller.create_entity_from_drop("QLabel", 16, 18, pane.id)

        wizard = self.controller.create_entity_from_drop("QWizard", 420, 260, "form_root")
        wizard_page = self.controller.active_document.get_wizard_pages(wizard.id)[0]
        label_in_wizard = self.controller.create_entity_from_drop("QLabel", 20, 22, wizard_page.id)

        self._process_events()

        self.assertIs(self.canvas.get_visual_parent_for_entity(frame), self.canvas)
        self.assertIs(
            self.canvas.get_visual_parent_for_entity(label_in_frame),
            self.canvas._item_views_by_id[frame.id].get_content_widget(),
        )
        self.assertIs(
            self.canvas.get_visual_parent_for_entity(label_in_tab),
            self.canvas._item_views_by_id[tab_widget.id].get_page_content_widget(tab_page.id),
        )
        self.assertIs(
            self.canvas.get_visual_parent_for_entity(label_in_scroll),
            self.canvas._item_views_by_id[scroll_area.id].get_content_widget(),
        )
        self.assertIs(
            self.canvas.get_visual_parent_for_entity(label_in_splitter),
            self.canvas._item_views_by_id[splitter.id].get_pane_content_widget(pane.id),
        )
        self.assertIs(
            self.canvas.get_visual_parent_for_entity(label_in_wizard),
            self.canvas._item_views_by_id[wizard.id].get_page_content_widget(wizard_page.id),
        )

    def test_rebuild_all_clears_stale_views_and_preserves_selection(self) -> None:
        frame = self.controller.create_entity_from_drop("QFrame", 20, 20, "form_root")
        label = self.controller.create_entity_from_drop("QLabel", 10, 12, frame.id)
        splitter = self.controller.create_entity_from_drop("QSplitter", 260, 20, "form_root")
        panes = self.controller.active_document.get_splitter_panes(splitter.id)
        nested = self.controller.create_entity_from_drop("QPushButton", 12, 14, panes[0].id)
        self._process_events()

        self.controller.select_entity(label.id)
        self._process_events()
        self.canvas.rebuild_all()
        self._process_events()

        self.assertEqual(self.canvas._selected_entity_id, label.id)
        self.assertTrue(self.canvas._item_views_by_id[label.id].is_selected)
        self.assertEqual(set(self.canvas._item_views_by_id), self._expected_canvas_entity_ids())

        self.controller.delete_entity(splitter.id)
        self._process_events()

        self.assertNotIn(splitter.id, self.canvas._item_views_by_id)
        self.assertNotIn(nested.id, self.canvas._item_views_by_id)
        self.assertEqual(set(self.canvas._item_views_by_id), self._expected_canvas_entity_ids())

    def test_resolve_drop_parent_and_local_position_for_supported_special_containers(self) -> None:
        tab_widget = self.controller.create_entity_from_drop("QTabWidget", 20, 20, "form_root")
        tab_page = self.controller.active_document.get_tab_pages(tab_widget.id)[0]
        tab_content = self.canvas._item_views_by_id[tab_widget.id].get_page_content_widget(tab_page.id)

        scroll_area = self.controller.create_entity_from_drop("QScrollArea", 20, 240, "form_root")
        scroll_content = self.canvas._item_views_by_id[scroll_area.id].get_content_widget()
        scroll_content_entity = self.controller.active_document.get_scroll_content(scroll_area.id)

        splitter = self.controller.create_entity_from_drop("QSplitter", 420, 20, "form_root")
        splitter_pane = self.controller.active_document.get_splitter_panes(splitter.id)[0]
        splitter_content = self.canvas._item_views_by_id[splitter.id].get_pane_content_widget(splitter_pane.id)

        wizard = self.controller.create_entity_from_drop("QWizard", 420, 260, "form_root")
        wizard_page = self.controller.active_document.get_wizard_pages(wizard.id)[0]
        wizard_content = self.canvas._item_views_by_id[wizard.id].get_page_content_widget(wizard_page.id)

        self._process_events()

        cases = [
            (tab_page.id, tab_content, QPoint(18, 20)),
            (scroll_content_entity.id, scroll_content, QPoint(22, 24)),
            (splitter_pane.id, splitter_content, QPoint(16, 18)),
            (wizard_page.id, wizard_content, QPoint(26, 28)),
        ]

        for expected_parent_id, content_widget, local_point in cases:
            with self.subTest(parent_id=expected_parent_id):
                canvas_point = content_widget.mapTo(self.canvas, local_point)
                resolved_parent = self.canvas.resolve_drop_parent("QLabel", canvas_point)
                resolved_local = self.canvas.to_local_drop_position(expected_parent_id, canvas_point)
                self.assertEqual(resolved_parent, expected_parent_id)
                self.assertEqual(resolved_local, local_point)

        root_point = QPoint(self.canvas.width() - 12, self.canvas.height() - 12)
        self.assertEqual(self.canvas.resolve_drop_parent("QLabel", root_point), "form_root")
        self.assertEqual(self.canvas.to_local_drop_position("form_root", root_point), root_point)

    def test_container_drag_preview_does_not_flush_snapshot_until_commit(self) -> None:
        frame = self.controller.create_entity_from_drop("QFrame", 20, 20, "form_root")
        self._process_events()
        frame_view = self.canvas._item_views_by_id[frame.id]

        snapshot_events: list[str] = []
        self.controller.snapshot_changed.connect(snapshot_events.append)

        origin_global = QPoint(100, 100)
        frame_view._begin_interaction_from_points(
            Qt.MouseButton.LeftButton,
            QPoint(10, 10),
            origin_global,
        )
        frame_view._update_interaction_from_global(origin_global + QPoint(40, 30))

        self.assertEqual(snapshot_events, [])
        self.assertEqual(self.controller.active_document.get_entity(frame.id).geometry["x"], 20)
        self.assertEqual(self.controller.active_document.get_entity(frame.id).geometry["y"], 20)

        frame_view._finish_interaction_from_button(Qt.MouseButton.LeftButton)
        self._process_events()

        self.assertGreaterEqual(len(snapshot_events), 1)
        updated = self.controller.active_document.get_entity(frame.id)
        self.assertEqual(updated.geometry["x"], 60)
        self.assertEqual(updated.geometry["y"], 50)

    def test_selecting_internal_special_entities_highlights_visible_container(self) -> None:
        tab_widget = self.controller.create_entity_from_drop("QTabWidget", 20, 20, "form_root")
        tab_page = self.controller.active_document.get_tab_pages(tab_widget.id)[0]

        scroll_area = self.controller.create_entity_from_drop("QScrollArea", 20, 220, "form_root")
        scroll_content = self.controller.active_document.get_scroll_content(scroll_area.id)

        splitter = self.controller.create_entity_from_drop("QSplitter", 420, 20, "form_root")
        splitter_pane = self.controller.active_document.get_splitter_panes(splitter.id)[0]

        wizard = self.controller.create_entity_from_drop("QWizard", 420, 260, "form_root")
        wizard_page = self.controller.active_document.get_wizard_pages(wizard.id)[0]
        self._process_events()

        cases = [
            (tab_page.id, tab_widget.id),
            (scroll_content.id, scroll_area.id),
            (splitter_pane.id, splitter.id),
            (wizard_page.id, wizard.id),
        ]

        for selected_id, expected_visible_id in cases:
            with self.subTest(selected_id=selected_id):
                self.controller.select_entity(selected_id)
                self._process_events()
                self.assertEqual(self.canvas._selected_entity_id, expected_visible_id)
                self.assertTrue(self.canvas._item_views_by_id[expected_visible_id].is_selected)

    def _expected_canvas_entity_ids(self) -> set[str]:
        document = self.controller.active_document
        return {
            entity.id
            for entity in document.entities_by_id.values()
            if document.widget_registry.get_editor_kind(entity.type) != "internal"
        }

    @classmethod
    def _process_events(cls) -> None:
        cls._app.processEvents()


if __name__ == "__main__":
    unittest.main()
