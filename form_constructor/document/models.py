from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class FormRootModel:
    id: str
    type: str
    name: str
    root_widget_type: str
    width: int
    height: int
    window_title: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "name": self.name,
            "root_widget_type": self.root_widget_type,
            "width": self.width,
            "height": self.height,
            "window_title": self.window_title,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FormRootModel":
        return cls(
            id=str(data["id"]),
            type=str(data["type"]),
            name=str(data["name"]),
            root_widget_type=str(data["root_widget_type"]),
            width=int(data["width"]),
            height=int(data["height"]),
            window_title=str(data["window_title"]),
        )


@dataclass
class EntityModel:
    id: str
    type: str
    parent_id: str
    name: str
    order: int
    geometry: dict = field(default_factory=dict)
    properties: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "parent_id": self.parent_id,
            "name": self.name,
            "order": self.order,
            "geometry": dict(self.geometry),
            "properties": dict(self.properties),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EntityModel":
        return cls(
            id=str(data["id"]),
            type=str(data["type"]),
            parent_id=str(data["parent_id"]),
            name=str(data["name"]),
            order=int(data["order"]),
            geometry=dict(data.get("geometry", {})),
            properties=dict(data.get("properties", {})),
        )
