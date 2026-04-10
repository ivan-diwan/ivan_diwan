from __future__ import annotations

from PySide6.QtCore import QPoint
from PySide6.QtGui import QColor, QDragEnterEvent, QDropEvent, QMouseEvent, QPalette
from PySide6.QtWidgets import QFrame, QWidget

from form_constructor.canvas.drop_target_resolver import DropTargetResolver
from form_constructor.canvas.views.container_item_view import ContainerItemView
from form_constructor.canvas.views.leaf_item_view import LeafItemView
from form_constructor.canvas.views.scroll_area_item_view import ScrollAreaItemView
from form_constructor.canvas.views.splitter_item_view import SplitterItemView
from form_constructor.canvas.views.tab_widget_item_view import TabWidgetItemView
from form_constructor.canvas.views.wizard_item_view import WizardItemView
from form_constructor.controller.document_controller import DocumentController
from form_constructor.document.form_document import FormDocument
from form_constructor.document.models import EntityModel
from form_constructor.factory.widget_factory import WidgetFactory


class CanvasEditor(QFrame):
    def __init__(self, controller: DocumentController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._controller = controller
        self._document: FormDocument | None = None
        self._widget_factory = WidgetFactory()
        self._item_views_by_id: dict[str, QWidget] = {}
        self._selected_entity_id: str | None = None

        self.setFrameShape(QFrame.Shape.Box)
        self.setAcceptDrops(True)
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#ffffff"))
        self.setPalette(palette)
        self._special_subtree_builders = {
            "QTabWidget": self._build_tab_widget_subtree,
            "QScrollArea": self._build_scroll_area_subtree,
            "QSplitter": self._build_splitter_subtree,
            "QWizard": self._build_wizard_subtree,
        }
        self._special_view_builders = {
            "QTabWidget": self._create_tab_widget_view,
            "QScrollArea": self._create_scroll_area_view,
            "QSplitter": self._create_splitter_view,
            "QWizard": self._create_wizard_view,
        }
        self._special_refreshers = {
            "QScrollArea": self._refresh_scroll_area_view,
            "QSplitter": self._refresh_splitter_view,
            "QWizard": self._refresh_wizard_view,
        }

    @property
    def controller(self) -> DocumentController:
        return self._controller

    def set_document(self, document: FormDocument) -> None:
        self._document = document
        form_root = document.get_form_root()
        self.setFixedSize(form_root.width, form_root.height)
        self.rebuild_all()

    def rebuild_all(self) -> None:
        for view in list(self._item_views_by_id.values()):
            view.deleteLater()
        self._item_views_by_id.clear()
        if self._document is None:
            return
        for entity in self._document.get_root_entities():
            self._build_subtree(entity, self)
        self.select_entity(self._selected_entity_id)

    def _build_subtree(self, entity: EntityModel, visual_parent: QWidget) -> None:
        editor_kind = self._document.widget_registry.get_editor_kind(entity.type)
        if editor_kind == "internal":
            return
        special_builder = self._special_subtree_builders.get(entity.type)
        if special_builder is not None:
            special_builder(entity, visual_parent)
            return
        view = self._create_view_for_entity(entity, visual_parent)
        self._item_views_by_id[entity.id] = view
        view.show()
        for child in self._document.get_children(entity.id):
            self._build_subtree(child, view.get_content_widget())

    def get_visual_parent_for_entity(self, entity: EntityModel) -> QWidget:
        if self._document is None:
            return self
        if entity.parent_id == self._document.form_root.id:
            return self

        parent_entity = self._document.get_entity(entity.parent_id)
        if parent_entity is None:
            return self

        if parent_entity.type == "TabPage":
            tab_widget_view = self._item_views_by_id.get(parent_entity.parent_id)
            if tab_widget_view is not None:
                return tab_widget_view.get_page_content_widget(parent_entity.id)
            return self

        if parent_entity.type == "ContainerContent":
            scroll_area_view = self._item_views_by_id.get(parent_entity.parent_id)
            if scroll_area_view is not None:
                return scroll_area_view.get_content_widget()
            return self

        if parent_entity.type == "SplitterPane":
            splitter_view = self._item_views_by_id.get(parent_entity.parent_id)
            if splitter_view is not None:
                return splitter_view.get_pane_content_widget(parent_entity.id)
            return self

        if parent_entity.type == "WizardPage":
            wizard_view = self._item_views_by_id.get(parent_entity.parent_id)
            if wizard_view is not None:
                return wizard_view.get_page_content_widget(parent_entity.id)
            return self

        parent_view = self._item_views_by_id.get(entity.parent_id)
        if parent_view is not None:
            return parent_view.get_content_widget()
        return self

    def _build_tab_widget_subtree(self, entity: EntityModel, visual_parent: QWidget) -> None:
        view = self._create_view_for_entity(entity, visual_parent)
        self._item_views_by_id[entity.id] = view
        view.show()
        for tab_page in self._document.get_tab_pages(entity.id):
            page_widget = view.get_page_content_widget(tab_page.id)
            for child in self._document.get_children(tab_page.id):
                self._build_subtree(child, page_widget)

    def _build_scroll_area_subtree(self, entity: EntityModel, visual_parent: QWidget) -> None:
        view = self._create_view_for_entity(entity, visual_parent)
        self._item_views_by_id[entity.id] = view
        view.show()
        content_entity = self._document.get_scroll_content(entity.id)
        if content_entity is None:
            return
        for child in self._document.get_children(content_entity.id):
            self._build_subtree(child, view.get_content_widget())

    def _build_splitter_subtree(self, entity: EntityModel, visual_parent: QWidget) -> None:
        view = self._create_view_for_entity(entity, visual_parent)
        self._item_views_by_id[entity.id] = view
        view.show()
        for pane in self._document.get_splitter_panes(entity.id):
            pane_widget = view.get_pane_content_widget(pane.id)
            for child in self._document.get_children(pane.id):
                self._build_subtree(child, pane_widget)

    def _build_wizard_subtree(self, entity: EntityModel, visual_parent: QWidget) -> None:
        view = self._create_view_for_entity(entity, visual_parent)
        self._item_views_by_id[entity.id] = view
        view.show()
        for page in self._document.get_wizard_pages(entity.id):
            page_widget = view.get_page_content_widget(page.id)
            for child in self._document.get_children(page.id):
                self._build_subtree(child, page_widget)

    def _create_view_for_entity(self, entity: EntityModel, visual_parent: QWidget):
        inner_widget = self._widget_factory.create_widget(entity, parent=None)
        editor_kind = self._document.widget_registry.get_editor_kind(entity.type)
        if editor_kind == "container":
            view = ContainerItemView(canvas=self, parent=visual_parent)
            view.bind_entity(entity, inner_widget)
        else:
            special_builder = self._special_view_builders.get(entity.type)
            if special_builder is not None:
                view = special_builder(entity, visual_parent, inner_widget)
            else:
                view = LeafItemView(canvas=self, parent=visual_parent)
                view.bind_entity(entity, inner_widget)
        return view

    def refresh_view(self, entity: EntityModel) -> None:
        view = self._item_views_by_id.get(entity.id)
        if view is None:
            return
        refresher = self._special_refreshers.get(entity.type)
        if refresher is not None:
            refresher(view, entity)
            return
        view.refresh_from_document(entity)
        self._widget_factory.refresh_widget(view.inner_widget, entity)

    def handle_entity_update(self, entity: EntityModel | None) -> None:
        if entity is None or self._document is None:
            return
        editor_kind = self._document.widget_registry.get_editor_kind(entity.type)
        if editor_kind in {"special_container", "internal"}:
            self.rebuild_all()
            return
        self.refresh_view(entity)

    def remove_view(self, entity_id: str) -> None:
        self.rebuild_all()

    def select_entity(self, entity_id: str | None) -> None:
        self._selected_entity_id = entity_id
        for current_id, view in self._item_views_by_id.items():
            view.set_selected(current_id == entity_id)

    def request_select(self, entity_id: str) -> None:
        self._controller.select_entity(entity_id)

    def commit_move(self, entity_id: str, pos: QPoint) -> None:
        self._controller.move_entity(entity_id, pos.x(), pos.y())

    def commit_resize(self, entity_id: str, width: int, height: int) -> None:
        self._controller.resize_entity(entity_id, width, height)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        type_name = event.mimeData().text().strip()
        if not type_name:
            event.ignore()
            return
        pos = event.position().toPoint()
        try:
            parent_id = self.resolve_drop_parent(type_name, pos)
        except ValueError as error:
            self._controller.notify_error(f"Drop rejected: {error}")
            event.ignore()
            return
        if parent_id is None:
            self._controller.notify_error(f"Drop rejected: no valid parent for '{type_name}'.")
            event.ignore()
            return
        local_pos = self.to_local_drop_position(parent_id, pos)
        try:
            self._controller.create_entity_from_drop(
                type_name,
                local_pos.x(),
                local_pos.y(),
                parent_id,
            )
        except ValueError as error:
            self._controller.notify_error(f"Drop rejected: {error}")
            event.ignore()
            return
        event.acceptProposedAction()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == event.button().LeftButton:
            self._controller.clear_selection()
            event.accept()
            return
        super().mousePressEvent(event)

    def resolve_drop_parent(self, type_name: str, pos: QPoint) -> str | None:
        resolver = DropTargetResolver(self._document, self._item_views_by_id, self)
        return resolver.resolve_parent(type_name, pos)

    def find_container_candidates_at(self, pos: QPoint) -> list[str]:
        resolver = DropTargetResolver(self._document, self._item_views_by_id, self)
        return resolver.find_container_candidates(pos)

    def to_local_drop_position(self, parent_id: str, pos: QPoint) -> QPoint:
        resolver = DropTargetResolver(self._document, self._item_views_by_id, self)
        return resolver.to_local_position(parent_id, pos)

    def _create_tab_widget_view(self, entity: EntityModel, visual_parent: QWidget, inner_widget: QWidget):
        view = TabWidgetItemView(canvas=self, parent=visual_parent)
        view.bind_entity(entity, inner_widget, self._document)
        return view

    def _create_scroll_area_view(self, entity: EntityModel, visual_parent: QWidget, inner_widget: QWidget):
        content_entity = self._document.get_scroll_content(entity.id)
        if content_entity is None:
            raise RuntimeError(f"QScrollArea '{entity.id}' has no ContainerContent.")
        content_widget = self._widget_factory.create_widget(content_entity, parent=None)
        view = ScrollAreaItemView(canvas=self, parent=visual_parent)
        view.bind_entity(entity, inner_widget, content_entity, content_widget)
        return view

    def _create_splitter_view(self, entity: EntityModel, visual_parent: QWidget, inner_widget: QWidget):
        view = SplitterItemView(canvas=self, parent=visual_parent)
        view.bind_entity(entity, inner_widget, self._document)
        return view

    def _create_wizard_view(self, entity: EntityModel, visual_parent: QWidget, inner_widget: QWidget):
        view = WizardItemView(canvas=self, parent=visual_parent)
        view.bind_entity(entity, inner_widget, self._document)
        return view

    def _refresh_scroll_area_view(self, view, entity: EntityModel) -> None:
        content_entity = self._document.get_scroll_content(entity.id)
        view.refresh_from_document(entity, content_entity)
        self._widget_factory.refresh_widget(view.inner_widget, entity)

    def _refresh_splitter_view(self, view, entity: EntityModel) -> None:
        view.refresh_from_document(entity)
        self._widget_factory.refresh_widget(view.inner_widget, entity)

    def _refresh_wizard_view(self, view, entity: EntityModel) -> None:
        view.refresh_from_document(entity)
        self._widget_factory.refresh_widget(view.inner_widget, entity)
