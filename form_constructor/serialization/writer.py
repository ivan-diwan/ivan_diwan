import json


def write_json_document(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def write_json_file(path: str, payload: dict) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(write_json_document(payload))
