from __future__ import annotations

import unittest

from PySide6.QtWidgets import QApplication

from form_constructor.controller.document_controller import DocumentController
from form_constructor.registry.builtins import build_builtin_registry
from form_constructor.ui.main_editor.main_editor_window import MainEditorWindow


class MainEditorWindowSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.controller = DocumentController(build_builtin_registry())
        self.window = MainEditorWindow(self.controller)
        self.window.show()
        self._process_events()

    def tearDown(self) -> None:
        if self.window._form_window is not None:
            self.window._form_window.close()
        self.window.close()
        self._process_events()

    def test_toolbar_state_tracks_document_lifecycle(self) -> None:
        self.assertTrue(self.window._load_button.isEnabled())
        self.assertFalse(self.window._save_button.isEnabled())
        self.assertFalse(self.window._export_python_button.isEnabled())

        self.controller.new_document(width=800, height=600)
        self._process_events()

        self.assertTrue(self.window._save_button.isEnabled())
        self.assertTrue(self.window._export_python_button.isEnabled())

        self.controller.close_document()
        self._process_events()

        self.assertTrue(self.window._load_button.isEnabled())
        self.assertFalse(self.window._save_button.isEnabled())
        self.assertFalse(self.window._export_python_button.isEnabled())

    def test_message_log_appends_status_and_error_lines_in_order(self) -> None:
        self.window._show_status_message("First status")
        self.window._show_error_message("Second error")
        self.window._show_status_message("Third status")

        self.assertEqual(
            self.window._message_log.toPlainText().splitlines(),
            [
                "[INFO] First status",
                "[ERROR] Second error",
                "[INFO] Third status",
            ],
        )

    @classmethod
    def _process_events(cls) -> None:
        cls._app.processEvents()


if __name__ == "__main__":
    unittest.main()
