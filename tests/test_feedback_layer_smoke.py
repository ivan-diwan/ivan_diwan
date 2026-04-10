from __future__ import annotations

from pathlib import Path
import unittest
from unittest.mock import patch

from PySide6.QtCore import QPoint, QPointF
from PySide6.QtWidgets import QApplication

from form_constructor.controller.document_controller import DocumentController
from form_constructor.registry.builtins import build_builtin_registry
from form_constructor.ui.main_editor.main_editor_window import MainEditorWindow
from tests.support import managed_test_paths


class _FakeMimeData:
    def __init__(self, text: str) -> None:
        self._text = text

    def text(self) -> str:
        return self._text


class _FakeDropEvent:
    def __init__(self, text: str, pos: QPoint) -> None:
        self._mime_data = _FakeMimeData(text)
        self._position = QPointF(pos)
        self.ignored = False
        self.accepted = False

    def mimeData(self):
        return self._mime_data

    def position(self):
        return self._position

    def ignore(self) -> None:
        self.ignored = True

    def acceptProposedAction(self) -> None:
        self.accepted = True


class FeedbackLayerSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.registry = build_builtin_registry()
        self.controller = DocumentController(self.registry)
        self.window = MainEditorWindow(self.controller)
        self.window.show()
        self._process_events()

    def tearDown(self) -> None:
        if self.window._form_window is not None:
            self.window._form_window.close()
        self.window.close()
        self._process_events()

    def test_success_status_messages_are_visible_in_ui(self) -> None:
        with managed_test_paths("tests\\_tmp_feedback_status.json", "tests\\_tmp_feedback_status.py") as (
            json_path,
            py_path,
        ):
            self.controller.new_document(width=800, height=600)
            self._process_events()
            self.assertIn("[INFO] Form created.", self.window._message_log.toPlainText())

            self.controller.save_document_to_json(str(json_path))
            self._process_events()
            self.assertIn("[INFO] JSON saved.", self.window._message_log.toPlainText())

            self.controller.export_document_to_python(str(py_path))
            self._process_events()
            self.assertIn("[INFO] Python exported.", self.window._message_log.toPlainText())

            self.controller.load_document(str(json_path))
            self._process_events()
            self.assertIn("[INFO] Form loaded.", self.window._message_log.toPlainText())

            self.controller.load_document(str(py_path))
            self._process_events()
            self.assertIn("[INFO] Python imported.", self.window._message_log.toPlainText())
            self.assertEqual(self.window.statusBar().currentMessage(), "Python imported.")

    def test_load_errors_and_drop_reject_are_visible_in_ui(self) -> None:
        self.controller.new_document(width=800, height=600)
        self._process_events()

        with managed_test_paths("tests\\_tmp_feedback_unsupported.txt") as (unsupported_path,):
            unsupported_path.write_text("unsupported", encoding="utf-8")
            with patch(
                "form_constructor.ui.main_editor.main_editor_window.QFileDialog.getOpenFileName",
                return_value=(str(unsupported_path), "All Files (*)"),
            ):
                self.window._load_document()
            self._process_events()
            self.assertIn("Unsupported document format", self.window._message_log.toPlainText())
            self.assertIn("[ERROR]", self.window._message_log.toPlainText())

            canvas = self.window._form_window._canvas
            fake_event = _FakeDropEvent("UnknownWidget", QPoint(30, 30))
            canvas.dropEvent(fake_event)
            self._process_events()

            self.assertTrue(fake_event.ignored)
            self.assertFalse(fake_event.accepted)
            self.assertIn("Drop rejected", self.window._message_log.toPlainText())

    @classmethod
    def _process_events(cls) -> None:
        cls._app.processEvents()


if __name__ == "__main__":
    unittest.main()
