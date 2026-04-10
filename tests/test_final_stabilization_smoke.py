from __future__ import annotations

import unittest

from PySide6.QtWidgets import QApplication

from form_constructor.controller.document_controller import DocumentController
from form_constructor.registry.builtins import build_builtin_registry
from form_constructor.ui.main_editor.main_editor_window import MainEditorWindow


class FinalStabilizationSmokeTests(unittest.TestCase):
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

    def test_close_document_clears_editor_ui_and_closes_form_window(self) -> None:
        self.controller.new_document(width=800, height=600)
        self._process_events()

        self.assertIsNotNone(self.window._form_window)
        self.assertTrue(self.window._save_button.isEnabled())
        self.assertTrue(self.window._export_python_button.isEnabled())

        self.controller.close_document()
        self._process_events()

        self.assertIsNone(self.window._form_window)
        self.assertFalse(self.window._save_button.isEnabled())
        self.assertFalse(self.window._export_python_button.isEnabled())
        self.assertFalse(self.window._delete_button.isEnabled())
        self.assertEqual(self.controller.get_snapshot(), "")
        self.assertIs(self.window._property_panel._mode_stack.currentWidget(), self.window._property_panel._form_box)
        self.assertEqual(self.window._property_panel._form_id_edit.text(), "No active form")

    def test_delete_special_container_subtree_rebuilds_canvas_and_resets_panel(self) -> None:
        self.controller.new_document(width=900, height=700)
        wizard = self.controller.create_entity_from_drop("QWizard", 40, 40, "form_root")
        pages = self.controller.active_document.get_wizard_pages(wizard.id)
        nested = self.controller.create_entity_from_drop("QLabel", 20, 20, pages[0].id)
        self._process_events()

        self.controller.select_entity(nested.id)
        self._process_events()
        self.assertEqual(self.window._property_panel._active_entity_id, nested.id)
        self.assertEqual(self.window._property_panel._entity_type_edit.text(), "QLabel")

        self.controller.delete_entity(wizard.id)
        self._process_events()

        self.assertIsNone(self.controller.selected_entity)
        self.assertNotIn(wizard.id, self.window._form_window._canvas._item_views_by_id)
        self.assertEqual(
            set(self.window._form_window._canvas._item_views_by_id),
            {
                entity.id
                for entity in self.controller.active_document.entities_by_id.values()
                if self.controller.active_document.widget_registry.get_editor_kind(entity.type) != "internal"
            },
        )
        self.assertIs(self.window._property_panel._mode_stack.currentWidget(), self.window._property_panel._form_box)
        self.assertEqual(self.window._property_panel._form_id_edit.text(), "form_root")

    @classmethod
    def _process_events(cls) -> None:
        cls._app.processEvents()


if __name__ == "__main__":
    unittest.main()
