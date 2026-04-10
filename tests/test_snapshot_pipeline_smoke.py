from __future__ import annotations

from pathlib import Path
import unittest

from PySide6.QtWidgets import QApplication

from form_constructor.controller.document_controller import DocumentController
from form_constructor.registry.builtins import build_builtin_registry
from form_constructor.serialization.form_serializer import FormSerializer
from tests.support import managed_test_paths


class SnapshotPipelineSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.registry = build_builtin_registry()
        self.controller = DocumentController(self.registry)
        self.serializer = FormSerializer(widget_registry=self.registry)
        self.controller.new_document(width=900, height=700)
        self._assert_snapshot_matches_document()

    def test_snapshot_matches_document_after_supported_completed_operations(self) -> None:
        label = self.controller.create_entity_from_drop("QLabel", 20, 22, "form_root")
        self._assert_snapshot_matches_document()

        self.controller.update_entity_property(label.id, "text", "Updated")
        self._assert_snapshot_matches_document()

        self.controller.move_entity(label.id, 60, 80)
        self._assert_snapshot_matches_document()

        self.controller.resize_entity(label.id, 140, 36)
        self._assert_snapshot_matches_document()

        tab_widget = self.controller.create_entity_from_drop("QTabWidget", 220, 20, "form_root")
        self._assert_snapshot_matches_document()
        tab_pages = self.controller.active_document.get_tab_pages(tab_widget.id)
        self.controller.rename_tab_page(tab_pages[0].id, "First")
        self._assert_snapshot_matches_document()
        self.controller.add_tab_page(tab_widget.id)
        self._assert_snapshot_matches_document()
        self.controller.set_current_tab(tab_widget.id, 2)
        self._assert_snapshot_matches_document()
        third_page = self.controller.active_document.get_tab_pages(tab_widget.id)[2]
        self.controller.remove_tab_page(tab_widget.id, third_page.id)
        self._assert_snapshot_matches_document()

        splitter = self.controller.create_entity_from_drop("QSplitter", 20, 220, "form_root")
        self._assert_snapshot_matches_document()
        self.controller.set_splitter_orientation(splitter.id, "vertical")
        self._assert_snapshot_matches_document()
        self.controller.set_splitter_sizes(splitter.id, [120, 240])
        self._assert_snapshot_matches_document()

        wizard = self.controller.create_entity_from_drop("QWizard", 420, 220, "form_root")
        self._assert_snapshot_matches_document()
        pages = self.controller.active_document.get_wizard_pages(wizard.id)
        self.controller.rename_wizard_page(pages[0].id, "Intro", "Welcome")
        self._assert_snapshot_matches_document()
        self.controller.add_wizard_page(wizard.id)
        self._assert_snapshot_matches_document()
        self.controller.set_current_wizard_page(wizard.id, 2)
        self._assert_snapshot_matches_document()
        third_wizard_page = self.controller.active_document.get_wizard_pages(wizard.id)[2]
        self.controller.remove_wizard_page(wizard.id, third_wizard_page.id)
        self._assert_snapshot_matches_document()

        self.controller.delete_entity(label.id)
        self._assert_snapshot_matches_document()

    def test_snapshot_matches_document_after_load_and_import(self) -> None:
        self.controller.create_entity_from_drop("QPushButton", 30, 40, "form_root")
        with managed_test_paths("tests\\_tmp_snapshot_load.json", "tests\\_tmp_snapshot_load.py") as (
            json_path,
            py_path,
        ):
            self.controller.save_document_to_json(str(json_path))
            self._assert_snapshot_matches_document()

            self.controller.load_document(str(json_path))
            self._assert_snapshot_matches_document()

            self.controller.export_document_to_python(str(py_path))
            self._assert_snapshot_matches_document()

            self.controller.load_document(str(py_path))
            self._assert_snapshot_matches_document()

    def _assert_snapshot_matches_document(self) -> None:
        self.assertEqual(
            self.controller.get_snapshot(),
            self.serializer.serialize_to_json(self.controller.active_document),
        )


if __name__ == "__main__":
    unittest.main()
