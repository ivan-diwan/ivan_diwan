from __future__ import annotations

from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QFrame, QWidget

from form_constructor.document.models import EntityModel


class BaseFormItemView(QFrame):
    def __init__(self, canvas, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.canvas = canvas
        self.entity_id: str | None = None
        self.entity_type: str | None = None
        self.inner_widget: QWidget | None = None
        self.is_selected = False
        self.geometry_locked = False
        self._drag_active = False
        self._resize_active = False
        self.setFrameShape(QFrame.Shape.NoFrame)

    def bind_entity(self, entity: EntityModel, inner_widget: QWidget) -> None:
        self.entity_id = entity.id
        self.entity_type = entity.type
        self.inner_widget = inner_widget
        inner_widget.setParent(self)
        inner_widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        inner_widget.show()
        self.refresh_from_document(entity)

    def set_selected(self, value: bool) -> None:
        self.is_selected = value
        self.update()

    def refresh_from_document(self, entity: EntityModel) -> None:
        self.geometry_locked = bool(entity.properties.get("geometry_locked", False))
        geometry = entity.geometry
        self.setGeometry(
            int(geometry["x"]),
            int(geometry["y"]),
            int(geometry["width"]),
            int(geometry["height"]),
        )
        if self.inner_widget is not None:
            self.inner_widget.setGeometry(0, 0, self.width(), self.height())

    def get_geometry(self) -> dict:
        return {
            "x": self.x(),
            "y": self.y(),
            "width": self.width(),
            "height": self.height(),
        }

    def get_content_origin(self) -> QPoint:
        return QPoint(0, 0)

    def get_content_widget(self) -> QWidget:
        return self

    def can_edit_geometry(self) -> bool:
        return not self.geometry_locked
