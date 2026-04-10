from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPen
from PySide6.QtWidgets import QScrollArea, QWidget

from form_constructor.canvas.views.base_item_view import BaseFormItemView
from form_constructor.document.models import EntityModel


class ScrollContentWidget(QWidget):
    def __init__(self, owner: "ScrollAreaItemView", content_entity_id: str) -> None:
        super().__init__()
        self._owner = owner
        self._content_entity_id = content_entity_id

    @property
    def content_entity_id(self) -> str:
        return self._content_entity_id

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self._owner.handle_content_mouse_press(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        self._owner.handle_content_mouse_move(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._owner.handle_content_mouse_release(event)


class ScrollAreaItemView(BaseFormItemView):
    RESIZE_HANDLE = 12

    def __init__(self, canvas, parent: QWidget | None = None) -> None:
        super().__init__(canvas=canvas, parent=parent)
        self._scroll_area: QScrollArea | None = None
        self._content_widget: ScrollContentWidget | None = None
        self._content_entity_id: str | None = None
        self._drag_origin_global: QPoint | None = None
        self._origin_geometry: QRect | None = None

    @property
    def content_entity_id(self) -> str | None:
        return self._content_entity_id

    def bind_entity(
        self,
        entity: EntityModel,
        inner_widget: QWidget,
        content_entity: EntityModel,
        content_widget: QWidget,
    ) -> None:
        self.entity_id = entity.id
        self.entity_type = entity.type
        self.inner_widget = inner_widget
        self._scroll_area = inner_widget
        self._content_widget = content_widget
        self._content_entity_id = content_entity.id
        inner_widget.setParent(self)
        inner_widget.show()
        self._scroll_area.setWidget(content_widget)
        self.refresh_from_document(entity, content_entity)

    def refresh_from_document(
        self,
        entity: EntityModel,
        content_entity: EntityModel | None = None,
    ) -> None:
        super().refresh_from_document(entity)
        if self._scroll_area is None:
            return
        self._scroll_area.setGeometry(0, 0, self.width(), self.height())
        self._scroll_area.setWidgetResizable(bool(entity.properties.get("widget_resizable", True)))
        if content_entity is not None and self._content_widget is not None:
            self._content_widget.setGeometry(
                int(content_entity.geometry["x"]),
                int(content_entity.geometry["y"]),
                int(content_entity.geometry["width"]),
                int(content_entity.geometry["height"]),
            )

    def get_content_widget(self) -> QWidget:
        if self._content_widget is None:
            return self
        return self._content_widget

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self._begin_interaction(event.button(), event.position().toPoint(), event.globalPosition().toPoint())
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        self._update_interaction(event.globalPosition().toPoint())
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._finish_interaction(event.button())
        event.accept()

    def handle_content_mouse_press(self, event: QMouseEvent) -> None:
        if self._content_widget is None:
            return
        local_pos = self._content_widget.mapTo(self, event.position().toPoint())
        self._begin_interaction(event.button(), local_pos, event.globalPosition().toPoint())
        event.accept()

    def handle_content_mouse_move(self, event: QMouseEvent) -> None:
        self._update_interaction(event.globalPosition().toPoint())
        event.accept()

    def handle_content_mouse_release(self, event: QMouseEvent) -> None:
        self._finish_interaction(event.button())
        event.accept()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if not self.is_selected:
            return
        painter = QPainter(self)
        painter.setPen(QPen(QColor("#2b7cff"), 2, Qt.PenStyle.DashLine))
        painter.drawRect(self.rect().adjusted(1, 1, -2, -2))
        if self.can_edit_geometry():
            painter.fillRect(self._resize_rect(), QColor("#2b7cff"))

    def _begin_interaction(
        self,
        button: Qt.MouseButton,
        local_pos: QPoint,
        global_pos: QPoint,
    ) -> None:
        if button != Qt.MouseButton.LeftButton or self.entity_id is None:
            return
        self.canvas.request_select(self.entity_id)
        if not self.can_edit_geometry():
            return
        self._drag_origin_global = global_pos
        self._origin_geometry = self.geometry()
        if self._is_in_resize_zone(local_pos):
            self._resize_active = True
        else:
            self._drag_active = True

    def _update_interaction(self, global_pos: QPoint) -> None:
        if self._drag_origin_global is None or self._origin_geometry is None:
            return
        delta = global_pos - self._drag_origin_global
        if self._resize_active:
            width = max(120, self._origin_geometry.width() + delta.x())
            height = max(100, self._origin_geometry.height() + delta.y())
            self.setGeometry(self._origin_geometry.x(), self._origin_geometry.y(), width, height)
            if self.inner_widget is not None:
                self.inner_widget.setGeometry(0, 0, width, height)
        elif self._drag_active:
            self.move(
                max(0, self._origin_geometry.x() + delta.x()),
                max(0, self._origin_geometry.y() + delta.y()),
            )

    def _finish_interaction(self, button: Qt.MouseButton) -> None:
        if button == Qt.MouseButton.LeftButton and self.entity_id is not None:
            if self._drag_active:
                self.canvas.commit_move(self.entity_id, self.pos())
            elif self._resize_active:
                self.canvas.commit_resize(self.entity_id, self.width(), self.height())
        self._drag_active = False
        self._resize_active = False
        self._drag_origin_global = None
        self._origin_geometry = None

    def _is_in_resize_zone(self, pos: QPoint) -> bool:
        return self._resize_rect().contains(pos)

    def _resize_rect(self) -> QRect:
        return QRect(
            self.width() - self.RESIZE_HANDLE,
            self.height() - self.RESIZE_HANDLE,
            self.RESIZE_HANDLE,
            self.RESIZE_HANDLE,
        )
