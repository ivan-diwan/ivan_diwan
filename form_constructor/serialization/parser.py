import json


def parse_json_document(payload: str) -> dict:
    return json.loads(payload)


def parse_json_file(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        return parse_json_document(handle.read())
