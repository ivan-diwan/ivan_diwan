from __future__ import annotations

from typing import Any


def normalized_document_payload(document: Any, serializer: Any) -> dict:
    payload = serializer.serialize_to_dict(document)
    form = dict(payload["form"])
    objects = []
    for entity in payload["objects"]:
        entity_payload = {
            "id": entity["id"],
            "type": entity["type"],
            "parent_id": entity["parent_id"],
            "name": entity["name"],
            "order": entity["order"],
            "geometry": dict(entity["geometry"]),
            "properties": {
                key: value
                for key, value in entity["properties"].items()
                if key != "geometry_locked"
            },
        }
        objects.append(entity_payload)
    return {"form": form, "objects": objects}


def structure_signature(payload: dict, *, parent_reference: str = "id") -> dict:
    if parent_reference not in {"id", "name"}:
        raise ValueError(f"Unsupported parent_reference: {parent_reference}")

    parent_name_by_id = {"form_root": "form_root"}
    for entity in payload["objects"]:
        parent_name_by_id[entity["id"]] = entity["name"]

    objects = []
    for entity in payload["objects"]:
        parent_value = entity["parent_id"]
        if parent_reference == "name":
            parent_value = parent_name_by_id.get(entity["parent_id"], entity["parent_id"])
        objects.append(
            {
                "type": entity["type"],
                "name": entity["name"],
                "parent_ref": parent_value,
                "order": entity["order"],
                "geometry": dict(entity["geometry"]),
                "properties": {
                    key: value
                    for key, value in entity["properties"].items()
                    if key != "geometry_locked"
                },
            }
        )
    objects.sort(
        key=lambda entity: (
            entity["parent_ref"],
            entity["order"],
            entity["type"],
            entity["name"],
        )
    )
    return {"form": dict(payload["form"]), "objects": objects}


def compare_document_payloads(left_document: Any, right_document: Any, serializer: Any) -> bool:
    return normalized_document_payload(left_document, serializer) == normalized_document_payload(
        right_document,
        serializer,
    )


def compare_document_structure(
    left_document: Any,
    right_document: Any,
    serializer: Any,
    *,
    parent_reference: str = "id",
) -> bool:
    left_payload = normalized_document_payload(left_document, serializer)
    right_payload = normalized_document_payload(right_document, serializer)
    return structure_signature(left_payload, parent_reference=parent_reference) == structure_signature(
        right_payload,
        parent_reference=parent_reference,
    )
