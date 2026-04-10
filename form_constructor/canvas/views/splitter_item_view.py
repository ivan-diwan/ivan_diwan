from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPen
from PySide6.QtWidgets import QSplitter, QSplitterHandle, QWidget

from form_constructor.canvas.views.base_item_view import BaseFormItemView
from form_constructor.document.form_document import FormDocument
from form_constructor.document.models import EntityModel


class SplitterPaneContentWidget(QWidget):
    def __init__(self, owner: "SplitterItemView", pane_id: str) -> None:
        super().__init__()
        self._owner = owner
        self._pane_id = pane_id
        self.setAutoFillBackground(True)
        self.setStyleSheet("background: #fbfbfb; border: 1px solid #d4d4d4;")

    @property
    def pane_id(self) -> str:
        return self._pane_id

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self._owner.handle_pane_mouse_press(self, event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        self._owner.handle_pane_mouse_move(self, event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._owner.handle_pane_mouse_release(self, event)


class CanvasSplitterHandle(QSplitterHandle):
    def __init__(self, orientation: Qt.Orientation, owner: "SplitterItemView") -> None:
        super().__init__(orientation, owner.splitter_widget)
        self._owner = owner

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self._owner.handle_splitter_handle_press(event)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        super().mouseReleaseEvent(event)
        self._owner.handle_splitter_handle_release(event)


class CanvasSplitter(QSplitter):
    def __init__(self, owner: "SplitterItemView", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._owner = owner

    def createHandle(self) -> QSplitterHandle:
        return CanvasSplitterHandle(self.orientation(), self._owner)


class SplitterItemView(BaseFormItemView):
    RESIZE_HANDLE = 12
    SPLITTER_HANDLE_WIDTH = 8

    def __init__(self, canvas, parent: QWidget | None = None) -> None:
        super().__init__(canvas=canvas, parent=parent)
        self._splitter: QSplitter | None = None
        self._pane_widgets_by_id: dict[str, SplitterPaneContentWidget] = {}
        self._syncing_sizes = False
        self._handle_drag_active = False
        self._drag_origin_global: QPoint | None = None
        self._origin_geometry: QRect | None = None

    @property
    def splitter_widget(self) -> QSplitter | None:
        return self._splitter

    def bind_entity(
        self,
        entity: EntityModel,
        inner_widget: QWidget,
        document: FormDocument,
    ) -> None:
        self.entity_id = entity.id
        self.entity_type = entity.type
        inner_widget.deleteLater()
        self._splitter = CanvasSplitter(self, self)
        self.inner_widget = self._splitter
        self._splitter.setHandleWidth(self.SPLITTER_HANDLE_WIDTH)
        self._splitter.setStyleSheet(
            """
            QSplitter::handle {
                background: #b8b8b8;
                border: 1px solid #979797;
            }
            QSplitter::handle:hover {
                background: #9f9f9f;
            }
            """
        )
        self._splitter.show()
        self._rebuild_panes(document, entity.id)
        self.refresh_from_document(entity)

    def refresh_from_document(self, entity: EntityModel) -> None:
        super().refresh_from_document(entity)
        if self._splitter is None:
            return
        orientation = str(entity.properties.get("orientation", "horizontal")).lower()
        self._splitter.setGeometry(0, 0, self.width(), self.height())
        self._splitter.setOrientation(
            Qt.Orientation.Vertical if orientation == "vertical" else Qt.Orientation.Horizontal
        )
        sizes = entity.properties.get("sizes", [1, 1])
        if isinstance(sizes, list) and len(sizes) == 2:
            self._syncing_sizes = True
            self._splitter.setSizes([max(1, int(size)) for size in sizes])
            self._syncing_sizes = False

    def get_pane_ids(self) -> list[str]:
        return list(self._pane_widgets_by_id.keys())

    def get_pane_content_widget(self, pane_id: str) -> QWidget:
        return self._pane_widgets_by_id[pane_id]

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self._begin_interaction(event.button(), event.position().toPoint(), event.globalPosition().toPoint())
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        self._update_interaction(event.globalPosition().toPoint())
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._finish_interaction(event.button())
        event.accept()

    def handle_pane_mouse_press(self, pane_widget: SplitterPaneContentWidget, event: QMouseEvent) -> None:
        local_pos = pane_widget.mapTo(self, event.position().toPoint())
        self._begin_interaction(event.button(), local_pos, event.globalPosition().toPoint())
        event.accept()

    def handle_pane_mouse_move(self, pane_widget: SplitterPaneContentWidget, event: QMouseEvent) -> None:
        self._update_interaction(event.globalPosition().toPoint())
        event.accept()

    def handle_pane_mouse_release(self, pane_widget: SplitterPaneContentWidget, event: QMouseEvent) -> None:
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

    def _rebuild_panes(self, document: FormDocument, splitter_id: str) -> None:
        if self._splitter is None:
            return
        self._pane_widgets_by_id.clear()
        while self._splitter.count():
            widget = self._splitter.widget(0)
            widget.setParent(None)
            widget.deleteLater()
        for pane in document.get_splitter_panes(splitter_id):
            pane_widget = SplitterPaneContentWidget(self, pane.id)
            pane_widget.setObjectName(pane.name)
            self._pane_widgets_by_id[pane.id] = pane_widget
            self._splitter.addWidget(pane_widget)

    def handle_splitter_handle_press(self, event: QMouseEvent) -> None:
        if self.entity_id is None:
            return
        self.canvas.request_select(self.entity_id)
        self._handle_drag_active = self.can_edit_geometry()

    def handle_splitter_handle_release(self, event: QMouseEvent) -> None:
        if not self._handle_drag_active or self.entity_id is None or self._splitter is None:
            self._handle_drag_active = False
            return
        self._handle_drag_active = False
        self.canvas.request_select(self.entity_id)
        self.canvas.controller.set_splitter_sizes(self.entity_id, self._splitter.sizes())

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
            width = max(140, self._origin_geometry.width() + delta.x())
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
