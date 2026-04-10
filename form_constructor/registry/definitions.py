from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PropertyDefinition:
    name: str
    data_type: str
    required: bool
    default: object
    editor: str
    allowed_values: list | None = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "data_type": self.data_type,
            "required": self.required,
            "default": self.default,
            "editor": self.editor,
            "allowed_values": self.allowed_values,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PropertyDefinition":
        return cls(
            name=str(data["name"]),
            data_type=str(data["data_type"]),
            required=bool(data["required"]),
            default=data.get("default"),
            editor=str(data["editor"]),
            allowed_values=data.get("allowed_values"),
        )


@dataclass
class WidgetTypeDefinition:
    type_name: str
    display_name: str
    category: str
    editor_kind: str
    palette_visible: bool
    palette_group: str
    creatable_by_user: bool
    name_prefix: str
    default_size: tuple[int, int]
    property_schema: list[PropertyDefinition] = field(default_factory=list)
    allowed_parent_types: list[str] = field(default_factory=list)
    allowed_child_types: list[str] = field(default_factory=list)
    direct_children_only: bool = False
    special_actions: list[str] = field(default_factory=list)
    auto_create_children: list[str] = field(default_factory=list)
    qt_class_name: str = ""
    geometry_edit_mode: str = "full"
    movable: bool = True
    resizable: bool = True
    deletable_directly: bool = True
    description: str = ""

    def property_defaults(self) -> dict:
        return {prop.name: prop.default for prop in self.property_schema}
