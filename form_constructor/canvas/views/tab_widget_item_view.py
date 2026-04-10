from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPen
from PySide6.QtWidgets import QTabWidget, QWidget

from form_constructor.canvas.views.base_item_view import BaseFormItemView
from form_constructor.document.form_document import FormDocument
from form_constructor.document.models import EntityModel


class TabPageContentWidget(QWidget):
    def __init__(self, owner: "TabWidgetItemView", tab_page_id: str) -> None:
        super().__init__()
        self._owner = owner
        self._tab_page_id = tab_page_id

    @property
    def tab_page_id(self) -> str:
        return self._tab_page_id

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self._owner.handle_page_mouse_press(self, event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        self._owner.handle_page_mouse_move(self, event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._owner.handle_page_mouse_release(self, event)


class TabWidgetItemView(BaseFormItemView):
    RESIZE_HANDLE = 12

    def __init__(self, canvas, parent: QWidget | None = None) -> None:
        super().__init__(canvas=canvas, parent=parent)
        self._tab_widget: QTabWidget | None = None
        self._page_widgets_by_id: dict[str, TabPageContentWidget] = {}
        self._syncing_current_index = False
        self._drag_origin_global: QPoint | None = None
        self._origin_geometry: QRect | None = None

    def bind_entity(
        self,
        entity: EntityModel,
        inner_widget: QWidget,
        document: FormDocument,
    ) -> None:
        self.entity_id = entity.id
        self.entity_type = entity.type
        self.inner_widget = inner_widget
        self._tab_widget = inner_widget
        inner_widget.setParent(self)
        inner_widget.show()
        self._rebuild_tabs(document, entity.id)
        self.refresh_from_document(entity)
        self._tab_widget.currentChanged.connect(self._handle_current_changed)
        self._tab_widget.tabBar().installEventFilter(self)

    def eventFilter(self, watched, event) -> bool:
        if (
            self._tab_widget is not None
            and watched is self._tab_widget.tabBar()
            and event.type() == event.Type.MouseButtonPress
            and self.entity_id is not None
        ):
            self.canvas.request_select(self.entity_id)
        return super().eventFilter(watched, event)

    def refresh_from_document(self, entity: EntityModel) -> None:
        super().refresh_from_document(entity)
        if self._tab_widget is None:
            return
        self._tab_widget.setGeometry(0, 0, self.width(), self.height())
        self._tab_widget.setTabsClosable(bool(entity.properties.get("tabs_closable", False)))
        current_index = int(entity.properties.get("current_index", 0))
        if 0 <= current_index < self._tab_widget.count():
            self._syncing_current_index = True
            self._tab_widget.setCurrentIndex(current_index)
            self._syncing_current_index = False

    def get_page_content_widget(self, tab_page_id: str) -> QWidget:
        return self._page_widgets_by_id[tab_page_id]

    def get_active_tab_page_id(self) -> str | None:
        if self._tab_widget is None:
            return None
        current_index = self._tab_widget.currentIndex()
        if current_index < 0:
            return None
        page_widget = self._tab_widget.widget(current_index)
        if isinstance(page_widget, TabPageContentWidget):
            return page_widget.tab_page_id
        return None

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self._begin_interaction(
            event.button(),
            event.position().toPoint(),
            event.globalPosition().toPoint(),
        )
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        self._update_interaction(event.globalPosition().toPoint())
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
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

    def handle_page_mouse_press(self, page_widget: TabPageContentWidget, event: QMouseEvent) -> None:
        local_pos = page_widget.mapTo(self, event.position().toPoint())
        self._begin_interaction(
            event.button(),
            local_pos,
            event.globalPosition().toPoint(),
        )
        event.accept()

    def handle_page_mouse_move(self, page_widget: TabPageContentWidget, event: QMouseEvent) -> None:
        self._update_interaction(event.globalPosition().toPoint())
        event.accept()

    def handle_page_mouse_release(
        self,
        page_widget: TabPageContentWidget,
        event: QMouseEvent,
    ) -> None:
        self._finish_interaction(event.button())
        event.accept()

    def _rebuild_tabs(self, document: FormDocument, tab_widget_id: str) -> None:
        if self._tab_widget is None:
            return
        self._syncing_current_index = True
        self._tab_widget.clear()
        self._page_widgets_by_id.clear()
        for tab_page in document.get_tab_pages(tab_widget_id):
            page_widget = TabPageContentWidget(self, tab_page.id)
            page_widget.setObjectName(tab_page.name)
            self._page_widgets_by_id[tab_page.id] = page_widget
            self._tab_widget.addTab(page_widget, str(tab_page.properties.get("title", tab_page.name)))
        self._syncing_current_index = False

    def _handle_current_changed(self, index: int) -> None:
        if self._syncing_current_index:
            return
        if self.entity_id is None or index < 0:
            return
        self.canvas.request_select(self.entity_id)
        self.canvas.controller.set_current_tab(self.entity_id, index)

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
