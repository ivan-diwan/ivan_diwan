from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from form_constructor.canvas.views.base_item_view import BaseFormItemView
from form_constructor.document.form_document import FormDocument
from form_constructor.document.models import EntityModel


class WizardPageCanvasWidget(QFrame):
    def __init__(self, owner: "WizardItemView", page_id: str) -> None:
        super().__init__()
        self._owner = owner
        self._page_id = page_id
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setAutoFillBackground(True)
        self.setStyleSheet("background: #ffffff; border: 1px solid #d8d8d8;")

    @property
    def page_id(self) -> str:
        return self._page_id

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self._owner.handle_page_mouse_press(self, event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        self._owner.handle_page_mouse_move(self, event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._owner.handle_page_mouse_release(self, event)


class WizardItemView(BaseFormItemView):
    RESIZE_HANDLE = 12
    MIN_WIDTH = 500
    MIN_HEIGHT = 360

    def __init__(self, canvas, parent: QWidget | None = None) -> None:
        super().__init__(canvas=canvas, parent=parent)
        self._page_widgets_by_id: dict[str, WizardPageCanvasWidget] = {}
        self._page_ids_in_order: list[str] = []
        self._current_index = 0
        self._drag_origin_global: QPoint | None = None
        self._origin_geometry: QRect | None = None

        self._header_title = QLabel()
        self._header_subtitle = QLabel()
        self._header_subtitle.setWordWrap(True)
        self._back_button = QPushButton("Back")
        self._next_button = QPushButton("Next")
        self._page_counter = QLabel()
        self._page_stack = QStackedWidget()
        self._body_frame = QFrame()
        self._body_frame.setFrameShape(QFrame.Shape.NoFrame)
        self._body_frame.setStyleSheet("background: #f5f5f5; border: 1px solid #cfcfcf;")

        body_layout = QVBoxLayout(self._body_frame)
        body_layout.setContentsMargins(10, 10, 10, 10)
        body_layout.addWidget(self._page_stack, 1)

        header_layout = QVBoxLayout()
        header_layout.setContentsMargins(14, 14, 14, 0)
        header_layout.setSpacing(4)
        header_layout.addWidget(self._header_title)
        header_layout.addWidget(self._header_subtitle)

        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(14, 0, 14, 14)
        footer_layout.addWidget(self._page_counter)
        footer_layout.addStretch(1)
        footer_layout.addWidget(self._back_button)
        footer_layout.addWidget(self._next_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addLayout(header_layout)
        layout.addWidget(self._body_frame, 1)
        layout.addLayout(footer_layout)

        self._back_button.clicked.connect(self._go_back)
        self._next_button.clicked.connect(self._go_next)

    def bind_entity(
        self,
        entity: EntityModel,
        inner_widget: QWidget,
        document: FormDocument,
    ) -> None:
        self.entity_id = entity.id
        self.entity_type = entity.type
        self.inner_widget = inner_widget
        inner_widget.setParent(self)
        inner_widget.hide()
        self._rebuild_pages(document, entity.id)
        self.refresh_from_document(entity)

    def refresh_from_document(self, entity: EntityModel) -> None:
        super().refresh_from_document(entity)
        current_index = int(entity.properties.get("current_index", 0))
        if not self._page_ids_in_order:
            self._current_index = 0
            self._header_title.clear()
            self._header_subtitle.clear()
            self._page_counter.clear()
            self._back_button.setEnabled(False)
            self._next_button.setEnabled(False)
            return
        self._current_index = max(0, min(current_index, len(self._page_ids_in_order) - 1))
        self._page_stack.setCurrentIndex(self._current_index)
        current_page = self._page_model(self._current_index)
        self._header_title.setText(str(current_page.properties.get("title", current_page.name)))
        self._header_subtitle.setText(str(current_page.properties.get("subtitle", "")))
        self._page_counter.setText(f"Page {self._current_index + 1} of {len(self._page_ids_in_order)}")
        self._back_button.setEnabled(self._current_index > 0)
        self._next_button.setEnabled(self._current_index < len(self._page_ids_in_order) - 1)

    def get_page_content_widget(self, wizard_page_id: str) -> QWidget:
        return self._page_widgets_by_id[wizard_page_id]

    def get_active_wizard_page_id(self) -> str | None:
        if not self._page_ids_in_order:
            return None
        return self._page_ids_in_order[self._current_index]

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self._begin_interaction(event.button(), event.position().toPoint(), event.globalPosition().toPoint())
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        self._update_interaction(event.globalPosition().toPoint())
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._finish_interaction(event.button())
        event.accept()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        border_color = QColor("#2b7cff") if self.is_selected else QColor("#9d9d9d")
        painter = QPainter(self)
        painter.setPen(QPen(border_color, 2 if self.is_selected else 1, Qt.PenStyle.DashLine))
        painter.drawRect(self.rect().adjusted(1, 1, -2, -2))
        if self.is_selected and self.can_edit_geometry():
            painter.fillRect(self._resize_rect(), QColor("#2b7cff"))

    def handle_page_mouse_press(self, page_widget: WizardPageCanvasWidget, event: QMouseEvent) -> None:
        local_pos = page_widget.mapTo(self, event.position().toPoint())
        self._begin_interaction(event.button(), local_pos, event.globalPosition().toPoint())
        event.accept()

    def handle_page_mouse_move(self, page_widget: WizardPageCanvasWidget, event: QMouseEvent) -> None:
        self._update_interaction(event.globalPosition().toPoint())
        event.accept()

    def handle_page_mouse_release(self, page_widget: WizardPageCanvasWidget, event: QMouseEvent) -> None:
        self._finish_interaction(event.button())
        event.accept()

    def _rebuild_pages(self, document: FormDocument, wizard_id: str) -> None:
        self._page_widgets_by_id.clear()
        self._page_ids_in_order.clear()
        while self._page_stack.count():
            widget = self._page_stack.widget(0)
            self._page_stack.removeWidget(widget)
            widget.deleteLater()
        for page in document.get_wizard_pages(wizard_id):
            page_widget = WizardPageCanvasWidget(self, page.id)
            page_widget.setObjectName(page.name)
            self._page_widgets_by_id[page.id] = page_widget
            self._page_ids_in_order.append(page.id)
            self._page_stack.addWidget(page_widget)

    def _page_model(self, index: int) -> EntityModel:
        page_id = self._page_ids_in_order[index]
        return self.canvas._document.get_entity(page_id)

    def _go_back(self) -> None:
        if self.entity_id is None or self._current_index <= 0:
            return
        self.canvas.request_select(self.entity_id)
        self.canvas.controller.set_current_wizard_page(self.entity_id, self._current_index - 1)

    def _go_next(self) -> None:
        if self.entity_id is None or self._current_index >= len(self._page_ids_in_order) - 1:
            return
        self.canvas.request_select(self.entity_id)
        self.canvas.controller.set_current_wizard_page(self.entity_id, self._current_index + 1)

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
            width = max(self.MIN_WIDTH, self._origin_geometry.width() + delta.x())
            height = max(self.MIN_HEIGHT, self._origin_geometry.height() + delta.y())
            self.setGeometry(self._origin_geometry.x(), self._origin_geometry.y(), width, height)
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
