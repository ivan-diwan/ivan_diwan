from __future__ import annotations

import unittest

from PySide6.QtWidgets import QApplication

from form_constructor.controller.document_controller import DocumentController
from form_constructor.registry.builtins import build_builtin_registry


class ControllerPipelineSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.controller = DocumentController(build_builtin_registry())
        self.events: dict[str, list] = {
            "document_created": [],
            "document_changed": [],
            "document_closed": [],
            "snapshot_changed": [],
            "selection_changed": [],
            "entity_added": [],
            "entity_updated": [],
            "entity_removed": [],
        }
        self.controller.document_created.connect(lambda document: self.events["document_created"].append(document))
        self.controller.document_changed.connect(lambda document: self.events["document_changed"].append(document))
        self.controller.document_closed.connect(lambda: self.events["document_closed"].append(True))
        self.controller.snapshot_changed.connect(lambda snapshot: self.events["snapshot_changed"].append(snapshot))
        self.controller.selection_changed.connect(lambda entity: self.events["selection_changed"].append(entity))
        self.controller.entity_added.connect(lambda entity: self.events["entity_added"].append(entity))
        self.controller.entity_updated.connect(lambda entity: self.events["entity_updated"].append(entity))
        self.controller.entity_removed.connect(lambda entity_id: self.events["entity_removed"].append(entity_id))

    def test_new_document_emits_single_activation_pipeline(self) -> None:
        self.controller.new_document(width=800, height=600)

        self.assertEqual(len(self.events["document_created"]), 1)
        self.assertEqual(len(self.events["document_changed"]), 1)
        self.assertEqual(len(self.events["selection_changed"]), 1)
        self.assertIsNone(self.events["selection_changed"][0])
        self.assertEqual(len(self.events["snapshot_changed"]), 1)
        self.assertEqual(len(self.events["entity_added"]), 0)
        self.assertEqual(len(self.events["entity_updated"]), 0)
        self.assertEqual(len(self.events["entity_removed"]), 0)

    def test_create_entity_emits_single_create_pipeline(self) -> None:
        self.controller.new_document(width=800, height=600)
        self._reset_events()

        entity = self.controller.create_entity_from_drop("QPushButton", 20, 20, "form_root")

        self.assertEqual(len(self.events["document_changed"]), 1)
        self.assertEqual(len(self.events["entity_added"]), 1)
        self.assertEqual(self.events["entity_added"][0].id, entity.id)
        self.assertEqual(len(self.events["snapshot_changed"]), 1)
        self.assertEqual(len(self.events["selection_changed"]), 1)
        self.assertEqual(self.events["selection_changed"][0].id, entity.id)
        self.assertEqual(len(self.events["entity_updated"]), 0)
        self.assertEqual(len(self.events["entity_removed"]), 0)

    def test_property_change_emits_single_update_pipeline(self) -> None:
        self.controller.new_document(width=800, height=600)
        entity = self.controller.create_entity_from_drop("QLabel", 20, 20, "form_root")
        self._reset_events()

        self.controller.update_entity_property(entity.id, "text", "Updated")

        self.assertEqual(len(self.events["document_changed"]), 1)
        self.assertEqual(len(self.events["entity_updated"]), 1)
        self.assertEqual(self.events["entity_updated"][0].id, entity.id)
        self.assertEqual(len(self.events["snapshot_changed"]), 1)
        self.assertEqual(len(self.events["selection_changed"]), 1)
        self.assertEqual(self.events["selection_changed"][0].id, entity.id)
        self.assertEqual(len(self.events["entity_added"]), 0)
        self.assertEqual(len(self.events["entity_removed"]), 0)

    def test_structural_special_container_change_emits_single_update_pipeline(self) -> None:
        self.controller.new_document(width=800, height=600)
        wizard = self.controller.create_entity_from_drop("QWizard", 40, 40, "form_root")
        self._reset_events()

        self.controller.add_wizard_page(wizard.id)

        self.assertEqual(len(self.events["document_changed"]), 1)
        self.assertEqual(len(self.events["entity_updated"]), 1)
        self.assertEqual(self.events["entity_updated"][0].id, wizard.id)
        self.assertEqual(len(self.events["snapshot_changed"]), 1)
        self.assertEqual(len(self.events["selection_changed"]), 1)
        self.assertEqual(self.events["selection_changed"][0].id, wizard.id)
        self.assertEqual(len(self.events["entity_added"]), 0)
        self.assertEqual(len(self.events["entity_removed"]), 0)

    def test_delete_selected_entity_emits_single_delete_pipeline(self) -> None:
        self.controller.new_document(width=800, height=600)
        entity = self.controller.create_entity_from_drop("QLabel", 20, 20, "form_root")
        self._reset_events()

        self.controller.delete_selected_entity()

        self.assertEqual(len(self.events["document_changed"]), 1)
        self.assertEqual(len(self.events["entity_removed"]), 1)
        self.assertEqual(self.events["entity_removed"][0], entity.id)
        self.assertEqual(len(self.events["snapshot_changed"]), 1)
        self.assertEqual(len(self.events["selection_changed"]), 1)
        self.assertIsNone(self.events["selection_changed"][0])
        self.assertEqual(len(self.events["entity_added"]), 0)
        self.assertEqual(len(self.events["entity_updated"]), 0)

    def test_load_json_emits_single_activation_pipeline(self) -> None:
        self.controller.new_document(width=800, height=600)
        self.controller.create_entity_from_drop("QPushButton", 20, 20, "form_root")
        payload = self.controller.get_snapshot()
        self._reset_events()

        self.controller.load_document_from_json(payload)

        self.assertEqual(len(self.events["document_created"]), 1)
        self.assertEqual(len(self.events["document_changed"]), 1)
        self.assertEqual(len(self.events["selection_changed"]), 1)
        self.assertIsNone(self.events["selection_changed"][0])
        self.assertEqual(len(self.events["snapshot_changed"]), 1)
        self.assertEqual(len(self.events["entity_added"]), 0)
        self.assertEqual(len(self.events["entity_updated"]), 0)
        self.assertEqual(len(self.events["entity_removed"]), 0)

    def test_close_document_emits_single_close_pipeline(self) -> None:
        self.controller.new_document(width=800, height=600)
        self.controller.create_entity_from_drop("QPushButton", 20, 20, "form_root")
        self._reset_events()

        self.controller.close_document()

        self.assertEqual(len(self.events["document_closed"]), 1)
        self.assertEqual(len(self.events["selection_changed"]), 1)
        self.assertIsNone(self.events["selection_changed"][0])
        self.assertEqual(len(self.events["snapshot_changed"]), 1)
        self.assertEqual(self.events["snapshot_changed"][0], "")
        self.assertEqual(len(self.events["document_created"]), 0)
        self.assertEqual(len(self.events["document_changed"]), 0)
        self.assertEqual(len(self.events["entity_added"]), 0)
        self.assertEqual(len(self.events["entity_updated"]), 0)
        self.assertEqual(len(self.events["entity_removed"]), 0)

    def _reset_events(self) -> None:
        for bucket in self.events.values():
            bucket.clear()


if __name__ == "__main__":
    unittest.main()
