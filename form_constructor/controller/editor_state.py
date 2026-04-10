from dataclasses import dataclass


@dataclass
class EditorState:
    active_document_id: str | None = None
    selected_entity_id: str | None = None
    current_json_path: str | None = None
    current_python_path: str | None = None
