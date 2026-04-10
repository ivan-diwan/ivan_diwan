from __future__ import annotations

from PySide6.QtCore import QPoint

from form_constructor.document.form_document import FormDocument


class DropTargetResolver:
    def __init__(self, document: FormDocument, item_views_by_id: dict[str, object], canvas) -> None:
        self._document = document
        self._item_views_by_id = item_views_by_id
        self._canvas = canvas
        self._candidate_extractors = {
            "QTabWidget": self._append_tab_widget_candidate,
            "QScrollArea": self._append_scroll_area_candidate,
            "QSplitter": self._append_splitter_candidates,
            "QWizard": self._append_wizard_candidate,
        }
        self._local_position_resolvers = {
            "TabPage": self._map_from_tab_page,
            "ContainerContent": self._map_from_scroll_content,
            "SplitterPane": self._map_from_splitter_pane,
            "WizardPage": self._map_from_wizard_page,
        }

    def resolve_parent(self, type_name: str, pos: QPoint) -> str | None:
        for candidate_parent_id in self.find_container_candidates(pos):
            if self._document.can_parent(candidate_parent_id, type_name):
                return candidate_parent_id
        if self._document.can_parent(self._document.form_root.id, type_name):
            return self._document.form_root.id
        return None

    def find_container_candidates(self, pos: QPoint) -> list[str]:
        container_views: list[tuple[int, str]] = []
        for entity_id, view in self._item_views_by_id.items():
            entity = self._document.get_entity(entity_id)
            if entity is None:
                continue
            if self._document.widget_registry.get_editor_kind(entity.type) == "container":
                self._append_if_contains(container_views, entity_id, view.get_content_widget(), pos)
                continue
            extractor = self._candidate_extractors.get(entity.type)
            if extractor is not None:
                extractor(container_views, view, pos)
        container_views.sort(key=lambda item: item[0])
        return [entity_id for _, entity_id in container_views]

    def to_local_position(self, parent_id: str, pos: QPoint) -> QPoint:
        if parent_id == self._document.form_root.id:
            return pos
        parent_entity = self._document.get_entity(parent_id)
        if parent_entity is None:
            return pos
        resolver = self._local_position_resolvers.get(parent_entity.type)
        if resolver is not None:
            return resolver(parent_entity, pos)
        parent_view = self._item_views_by_id[parent_id]
        return parent_view.get_content_widget().mapFrom(self._canvas, pos)

    def _append_if_contains(
        self,
        container_views: list[tuple[int, str]],
        entity_id: str,
        content_widget,
        pos: QPoint,
    ) -> None:
        top_left = content_widget.mapTo(self._canvas, QPoint(0, 0))
        rect = content_widget.rect().translated(top_left)
        if rect.contains(pos):
            container_views.append((rect.width() * rect.height(), entity_id))

    def _append_tab_widget_candidate(self, container_views, view, pos: QPoint) -> None:
        active_tab_page_id = view.get_active_tab_page_id()
        if active_tab_page_id is None:
            return
        self._append_if_contains(
            container_views,
            active_tab_page_id,
            view.get_page_content_widget(active_tab_page_id),
            pos,
        )

    def _append_scroll_area_candidate(self, container_views, view, pos: QPoint) -> None:
        content_entity_id = view.content_entity_id
        if content_entity_id is None:
            return
        self._append_if_contains(
            container_views,
            content_entity_id,
            view.get_content_widget(),
            pos,
        )

    def _append_splitter_candidates(self, container_views, view, pos: QPoint) -> None:
        for pane_id in view.get_pane_ids():
            self._append_if_contains(
                container_views,
                pane_id,
                view.get_pane_content_widget(pane_id),
                pos,
            )

    def _append_wizard_candidate(self, container_views, view, pos: QPoint) -> None:
        active_page_id = view.get_active_wizard_page_id()
        if active_page_id is None:
            return
        self._append_if_contains(
            container_views,
            active_page_id,
            view.get_page_content_widget(active_page_id),
            pos,
        )

    def _map_from_tab_page(self, parent_entity, pos: QPoint) -> QPoint:
        tab_widget_view = self._item_views_by_id[parent_entity.parent_id]
        return tab_widget_view.get_page_content_widget(parent_entity.id).mapFrom(self._canvas, pos)

    def _map_from_scroll_content(self, parent_entity, pos: QPoint) -> QPoint:
        scroll_area_view = self._item_views_by_id[parent_entity.parent_id]
        return scroll_area_view.get_content_widget().mapFrom(self._canvas, pos)

    def _map_from_splitter_pane(self, parent_entity, pos: QPoint) -> QPoint:
        splitter_view = self._item_views_by_id[parent_entity.parent_id]
        return splitter_view.get_pane_content_widget(parent_entity.id).mapFrom(self._canvas, pos)

    def _map_from_wizard_page(self, parent_entity, pos: QPoint) -> QPoint:
        wizard_view = self._item_views_by_id[parent_entity.parent_id]
        return wizard_view.get_page_content_widget(parent_entity.id).mapFrom(self._canvas, pos)
