from __future__ import annotations

import json
from pathlib import Path
import unittest

from PySide6.QtWidgets import QApplication

from form_constructor.controller.document_controller import DocumentController
from form_constructor.registry.builtins import build_builtin_registry
from tests.support import managed_test_paths


class LoadValidationSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.controller = DocumentController(build_builtin_registry())
        self.controller.new_document(width=800, height=600)
        self.controller.update_form_root(name="baseline_form", window_title="Baseline")
        created = self.controller.create_entity_from_drop("QPushButton", 20, 20, "form_root")
        self.baseline_entity_id = created.id
        self.baseline_snapshot = self.controller.get_snapshot()
        self.baseline_document = self.controller.active_document
        self.baseline_document_id = id(self.baseline_document)

    def test_invalid_json_payload_does_not_replace_active_document(self) -> None:
        broken_payload = json.dumps(
            {
                "document_type": "pyside6_form",
                "form": {
                    "id": "form_root",
                    "type": "FormRoot",
                    "name": "broken",
                    "root_widget_type": "QWidget",
                    "width": 800,
                    "height": 600,
                    "window_title": "Broken",
                },
                "objects": [
                    {
                        "id": "tab_widget_1",
                        "type": "QTabWidget",
                        "parent_id": "form_root",
                        "name": "tab_widget_1",
                        "order": 0,
                        "geometry": {"x": 20, "y": 20, "width": 300, "height": 200},
                        "properties": {"current_index": 0, "tabs_closable": False},
                    }
                ],
            }
        )

        with self.assertRaises(ValueError):
            self.controller.load_document_from_json(broken_payload)

        self.assertIs(self.controller.active_document, self.baseline_document)
        self.assertEqual(id(self.controller.active_document), self.baseline_document_id)
        self.assertEqual(self.controller.get_snapshot(), self.baseline_snapshot)
        self.assertEqual(self.controller.active_document.get_root_entities()[0].id, self.baseline_entity_id)

    def test_invalid_python_import_does_not_replace_active_document(self) -> None:
        with managed_test_paths("tests\\_tmp_invalid_import.py") as (invalid_python,):
            invalid_python.write_text(
                "\n".join(
                    [
                        "from PySide6.QtWidgets import QWidget, QTabWidget",
                        "",
                        "class GeneratedWidget(QWidget):",
                        "    def __init__(self):",
                        "        super().__init__()",
                        "        self.setup_ui()",
                        "",
                        "    def setup_ui(self):",
                        "        self.setObjectName('generated_widget')",
                        "        self.resize(800, 600)",
                        "        self.tab_widget_1 = QTabWidget(self)",
                        "        self.tab_widget_1.setObjectName('tab_widget_1')",
                        "        self.tab_widget_1.setGeometry(20, 20, 300, 200)",
                        "        self.tab_widget_1.setCurrentIndex(0)",
                        "",
                        "if __name__ == '__main__':",
                        "    pass",
                    ]
                ),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                self.controller.load_document_from_python(str(invalid_python))

        self.assertIs(self.controller.active_document, self.baseline_document)
        self.assertEqual(id(self.controller.active_document), self.baseline_document_id)
        self.assertEqual(self.controller.get_snapshot(), self.baseline_snapshot)
        self.assertEqual(self.controller.active_document.get_root_entities()[0].id, self.baseline_entity_id)


if __name__ == "__main__":
    unittest.main()
