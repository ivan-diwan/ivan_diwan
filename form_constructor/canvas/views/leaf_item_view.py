from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPen

from form_constructor.canvas.views.base_item_view import BaseFormItemView


class LeafItemView(BaseFormItemView):
    RESIZE_HANDLE = 12

    def __init__(self, canvas, parent=None) -> None:
        super().__init__(canvas=canvas, parent=parent)
        self._drag_origin_global: QPoint | None = None
        self._origin_geometry: QRect | None = None

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton or self.entity_id is None:
            super().mousePressEvent(event)
            return
        self.canvas.request_select(self.entity_id)
        if not self.can_edit_geometry():
            event.accept()
            return
        self._drag_origin_global = event.globalPosition().toPoint()
        self._origin_geometry = self.geometry()
        if self._is_in_resize_zone(event.position().toPoint()):
            self._resize_active = True
        else:
            self._drag_active = True
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_origin_global is None or self._origin_geometry is None:
            super().mouseMoveEvent(event)
            return
        delta = event.globalPosition().toPoint() - self._drag_origin_global
        if self._resize_active:
            width = max(20, self._origin_geometry.width() + delta.x())
            height = max(20, self._origin_geometry.height() + delta.y())
            self.setGeometry(
                self._origin_geometry.x(),
                self._origin_geometry.y(),
                width,
                height,
            )
            if self.inner_widget is not None:
                self.inner_widget.setGeometry(0, 0, width, height)
        elif self._drag_active:
            self.move(
                max(0, self._origin_geometry.x() + delta.x()),
                max(0, self._origin_geometry.y() + delta.y()),
            )
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self.entity_id is not None:
            if self._drag_active:
                self.canvas.commit_move(self.entity_id, self.pos())
            elif self._resize_active:
                self.canvas.commit_resize(self.entity_id, self.width(), self.height())
        self._drag_active = False
        self._resize_active = False
        self._drag_origin_global = None
        self._origin_geometry = None
        event.accept()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if not self.is_selected:
            return
        painter = QPainter(self)
        painter.setPen(QPen(QColor("#2b7cff"), 2))
        painter.drawRect(self.rect().adjusted(1, 1, -2, -2))
        if self.can_edit_geometry():
            painter.fillRect(self._resize_rect(), QColor("#2b7cff"))

    def _is_in_resize_zone(self, pos: QPoint) -> bool:
        return self._resize_rect().contains(pos)

    def _resize_rect(self) -> QRect:
        return QRect(
            self.width() - self.RESIZE_HANDLE,
            self.height() - self.RESIZE_HANDLE,
            self.RESIZE_HANDLE,
            self.RESIZE_HANDLE,
        )
