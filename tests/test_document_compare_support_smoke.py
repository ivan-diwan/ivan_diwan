from __future__ import annotations

import unittest

from form_constructor.registry.builtins import build_builtin_registry
from form_constructor.serialization.form_serializer import FormSerializer
from tests.support import (
    compare_document_payloads,
    compare_document_structure,
    normalized_document_payload,
    structure_signature,
)


class DocumentCompareSupportSmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = build_builtin_registry()
        self.serializer = FormSerializer(widget_registry=self.registry)

    def test_normalized_payload_drops_editor_only_properties(self) -> None:
        document = self.serializer.load_json("tests/export_cases/basic_leafs.json")
        first_entity = next(iter(document.entities_by_id.values()))
        first_entity.properties["geometry_locked"] = True

        payload = normalized_document_payload(document, self.serializer)
        serialized_entity = next(item for item in payload["objects"] if item["id"] == first_entity.id)

        self.assertNotIn("geometry_locked", serialized_entity["properties"])

    def test_structure_signature_supports_both_parent_reference_modes(self) -> None:
        document = self.serializer.load_json("tests/export_cases/mixed_complex.json")
        payload = normalized_document_payload(document, self.serializer)

        by_id = structure_signature(payload, parent_reference="id")
        by_name = structure_signature(payload, parent_reference="name")

        self.assertEqual(len(by_id["objects"]), len(by_name["objects"]))
        self.assertEqual(by_id["form"], by_name["form"])
        self.assertTrue(all("parent_ref" in item for item in by_id["objects"]))
        self.assertTrue(all("parent_ref" in item for item in by_name["objects"]))

    def test_structure_signature_rejects_unsupported_parent_reference_mode(self) -> None:
        document = self.serializer.load_json("tests/export_cases/basic_leafs.json")
        payload = normalized_document_payload(document, self.serializer)

        with self.assertRaises(ValueError):
            structure_signature(payload, parent_reference="unsupported")

    def test_compare_helpers_match_equivalent_documents(self) -> None:
        left = self.serializer.load_json("tests/export_cases/mixed_complex.json")
        right = self.serializer.load_json("tests/export_cases/mixed_complex.json")

        self.assertTrue(compare_document_payloads(left, right, self.serializer))
        self.assertTrue(compare_document_structure(left, right, self.serializer, parent_reference="name"))


if __name__ == "__main__":
    unittest.main()
