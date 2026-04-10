from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPen
from PySide6.QtWidgets import QWidget

from form_constructor.canvas.views.base_item_view import BaseFormItemView


class ContainerContentWidget(QWidget):
    def __init__(self, owner: "ContainerItemView") -> None:
        super().__init__(owner)
        self._owner = owner

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self._owner.handle_content_mouse_press(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        self._owner.handle_content_mouse_move(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._owner.handle_content_mouse_release(event)


class ContainerItemView(BaseFormItemView):
    RESIZE_HANDLE = 12

    def __init__(self, canvas, parent=None) -> None:
        super().__init__(canvas=canvas, parent=parent)
        self._drag_origin_global: QPoint | None = None
        self._origin_geometry: QRect | None = None
        self._content_widget = ContainerContentWidget(self)
        self._content_widget.setMouseTracking(True)
        self._content_widget.show()

    def refresh_from_document(self, entity) -> None:
        super().refresh_from_document(entity)
        self._update_content_widget()

    def bind_entity(self, entity, inner_widget) -> None:
        super().bind_entity(entity, inner_widget)
        self._content_widget.raise_()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self._begin_interaction(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        self._update_interaction(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._finish_interaction(event)

    def handle_content_mouse_press(self, event: QMouseEvent) -> None:
        origin = self.get_content_origin()
        self._begin_interaction_from_points(
            event.button(),
            event.position().toPoint() + origin,
            event.globalPosition().toPoint(),
        )
        event.accept()

    def handle_content_mouse_move(self, event: QMouseEvent) -> None:
        self._update_interaction_from_global(event.globalPosition().toPoint())
        event.accept()

    def handle_content_mouse_release(self, event: QMouseEvent) -> None:
        self._finish_interaction_from_button(event.button())
        event.accept()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        border_color = QColor("#2b7cff") if self.is_selected else QColor("#8c8c8c")
        painter.setPen(QPen(border_color, 2 if self.is_selected else 1, Qt.PenStyle.DashLine))
        painter.drawRect(self.rect().adjusted(1, 1, -2, -2))
        if self.is_selected and self.can_edit_geometry():
            painter.fillRect(self._resize_rect(), QColor("#2b7cff"))

    def get_content_origin(self) -> QPoint:
        if self.entity_type == "QGroupBox":
            return QPoint(0, 24)
        return QPoint(0, 0)

    def get_content_widget(self) -> QWidget:
        return self._content_widget

    def _begin_interaction(self, event: QMouseEvent) -> None:
        self._begin_interaction_from_points(
            event.button(),
            event.position().toPoint(),
            event.globalPosition().toPoint(),
        )

    def _begin_interaction_from_points(
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

    def _update_interaction(self, event: QMouseEvent) -> None:
        self._update_interaction_from_global(event.globalPosition().toPoint())
        event.accept()

    def _update_interaction_from_global(self, global_pos: QPoint) -> None:
        if self._drag_origin_global is None or self._origin_geometry is None:
            return
        delta = global_pos - self._drag_origin_global
        if self._resize_active:
            width = max(40, self._origin_geometry.width() + delta.x())
            height = max(40, self._origin_geometry.height() + delta.y())
            self.setGeometry(
                self._origin_geometry.x(),
                self._origin_geometry.y(),
                width,
                height,
            )
            if self.inner_widget is not None:
                self.inner_widget.setGeometry(0, 0, width, height)
            self._update_content_widget()
        elif self._drag_active:
            self.move(
                max(0, self._origin_geometry.x() + delta.x()),
                max(0, self._origin_geometry.y() + delta.y()),
            )

    def _finish_interaction(self, event: QMouseEvent) -> None:
        self._finish_interaction_from_button(event.button())
        event.accept()

    def _finish_interaction_from_button(self, button: Qt.MouseButton) -> None:
        if button == Qt.MouseButton.LeftButton and self.entity_id is not None:
            if self._drag_active:
                self.canvas.commit_move(self.entity_id, self.pos())
            elif self._resize_active:
                self.canvas.commit_resize(self.entity_id, self.width(), self.height())
        self._drag_active = False
        self._resize_active = False
        self._drag_origin_global = None
        self._origin_geometry = None

    def _update_content_widget(self) -> None:
        origin = self.get_content_origin()
        self._content_widget.setGeometry(
            origin.x(),
            origin.y(),
            max(1, self.width() - origin.x()),
            max(1, self.height() - origin.y()),
        )

    def _is_in_resize_zone(self, pos: QPoint) -> bool:
        return self._resize_rect().contains(pos)

    def _resize_rect(self) -> QRect:
        return QRect(
            self.width() - self.RESIZE_HANDLE,
            self.height() - self.RESIZE_HANDLE,
            self.RESIZE_HANDLE,
            self.RESIZE_HANDLE,
        )
