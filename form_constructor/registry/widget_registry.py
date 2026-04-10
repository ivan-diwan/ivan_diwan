from __future__ import annotations

from form_constructor.registry.definitions import WidgetTypeDefinition


class WidgetRegistry:
    def __init__(self) -> None:
        self._definitions: dict[str, WidgetTypeDefinition] = {}

    def register_type(self, definition: WidgetTypeDefinition) -> None:
        self._definitions[definition.type_name] = definition

    def register(self, definition: WidgetTypeDefinition) -> None:
        self.register_type(definition)

    def get_type(self, type_name: str) -> WidgetTypeDefinition | None:
        return self._definitions.get(type_name)

    def get(self, type_name: str) -> WidgetTypeDefinition | None:
        return self.get_type(type_name)

    def has_type(self, type_name: str) -> bool:
        return type_name in self._definitions

    def list_palette_types(self) -> list[WidgetTypeDefinition]:
        return [
            definition
            for definition in self._definitions.values()
            if definition.palette_visible
        ]

    def list_palette_types_by_group(self) -> dict[str, list[WidgetTypeDefinition]]:
        grouped: dict[str, list[WidgetTypeDefinition]] = {}
        for definition in self.list_palette_types():
            grouped.setdefault(definition.palette_group, []).append(definition)
        for group_name in grouped:
            grouped[group_name] = sorted(
                grouped[group_name],
                key=lambda definition: definition.display_name,
            )
        return dict(sorted(grouped.items()))

    def list_palette_groups(self) -> list[str]:
        return list(self.list_palette_types_by_group())

    def list_creatable_types(self) -> list[WidgetTypeDefinition]:
        return [
            definition
            for definition in self._definitions.values()
            if definition.creatable_by_user
        ]

    def list_types_by_editor_kind(self, editor_kind: str) -> list[WidgetTypeDefinition]:
        return [
            definition
            for definition in self._definitions.values()
            if definition.editor_kind == editor_kind
        ]

    def get_default_size(self, type_name: str) -> tuple[int, int]:
        definition = self._require_definition(type_name)
        return definition.default_size

    def get_default_properties(self, type_name: str) -> dict:
        definition = self._require_definition(type_name)
        return definition.property_defaults()

    def get_name_prefix(self, type_name: str) -> str:
        definition = self._require_definition(type_name)
        return definition.name_prefix

    def get_property_schema(self, type_name: str):
        definition = self._require_definition(type_name)
        return list(definition.property_schema)

    def get_editor_kind(self, type_name: str) -> str:
        definition = self._require_definition(type_name)
        return definition.editor_kind

    def get_geometry_edit_mode(self, type_name: str) -> str:
        definition = self._require_definition(type_name)
        return definition.geometry_edit_mode

    def can_parent(self, parent_type: str, child_type: str) -> bool:
        child_definition = self._require_definition(child_type)
        if parent_type == "FormRoot":
            return self._matches_allowed_types(parent_type, child_definition.allowed_parent_types)
        parent_definition = self._require_definition(parent_type)
        return self._matches_allowed_types(parent_type, child_definition.allowed_parent_types) and self._matches_allowed_types(
            child_type,
            parent_definition.allowed_child_types,
        )

    def get_allowed_children(self, type_name: str) -> list[str]:
        definition = self._require_definition(type_name)
        return list(definition.allowed_child_types)

    def get_special_actions(self, type_name: str) -> list[str]:
        definition = self._require_definition(type_name)
        return list(definition.special_actions)

    def supports_special_action(self, type_name: str, action_name: str) -> bool:
        return action_name in self.get_special_actions(type_name)

    def get_auto_create_children(self, type_name: str) -> list[str]:
        definition = self._require_definition(type_name)
        return list(definition.auto_create_children)

    def all(self) -> list[WidgetTypeDefinition]:
        return list(self._definitions.values())

    def _require_definition(self, type_name: str) -> WidgetTypeDefinition:
        definition = self.get_type(type_name)
        if definition is None:
            raise ValueError(f"Unknown widget type: {type_name}")
        return definition

    @staticmethod
    def _matches_allowed_types(candidate_type: str, allowed_types: list[str]) -> bool:
        if not allowed_types:
            return True
        return candidate_type in allowed_types or "*" in allowed_types
