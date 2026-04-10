from __future__ import annotations

from form_constructor.document.models import EntityModel, FormRootModel
from form_constructor.registry.widget_registry import WidgetRegistry
from form_constructor.utils.date_utils import format_date_string, normalize_date_string, parse_date_string
from form_constructor.utils.datetime_utils import format_datetime_string, normalize_datetime_string, parse_datetime_string
from form_constructor.utils.time_utils import format_time_string, normalize_time_string, parse_time_string
from form_constructor.utils.geometry import make_geometry, normalize_geometry
from form_constructor.utils.ids import IdGenerator
from form_constructor.utils.naming import make_unique_name


class FormDocument:
    def __init__(
        self,
        form_root: FormRootModel,
        widget_registry: WidgetRegistry,
        entities_by_id: dict[str, EntityModel] | None = None,
        id_generator: IdGenerator | None = None,
    ) -> None:
        self.form_root = form_root
        self.widget_registry = widget_registry
        self.entities_by_id: dict[str, EntityModel] = entities_by_id or {}
        self.id_generator = id_generator or IdGenerator()
        self.id_generator.seed_from_existing_ids(list(self.entities_by_id.keys()))
        self.is_dirty = False

    def get_form_root(self) -> FormRootModel:
        return self.form_root

    def get_entity(self, entity_id: str) -> EntityModel | None:
        return self.entities_by_id.get(entity_id)

    def has_entity(self, entity_id: str) -> bool:
        return entity_id in self.entities_by_id

    def get_children(self, parent_id: str) -> list[EntityModel]:
        children = [
            entity for entity in self.entities_by_id.values() if entity.parent_id == parent_id
        ]
        return sorted(children, key=lambda entity: entity.order)

    def get_descendants(self, parent_id: str) -> list[EntityModel]:
        descendants: list[EntityModel] = []
        for child in self.get_children(parent_id):
            descendants.append(child)
            descendants.extend(self.get_descendants(child.id))
        return descendants

    def get_root_entities(self) -> list[EntityModel]:
        return self.get_children(self.form_root.id)

    def get_tab_pages(self, tab_widget_id: str) -> list[EntityModel]:
        tab_widget = self._require_entity(tab_widget_id)
        if tab_widget.type != "QTabWidget":
            raise ValueError(f"Entity '{tab_widget_id}' is not a QTabWidget.")
        return self.get_children(tab_widget_id)

    def get_scroll_content(self, scroll_area_id: str) -> EntityModel | None:
        scroll_area = self._require_entity(scroll_area_id)
        if scroll_area.type != "QScrollArea":
            raise ValueError(f"Entity '{scroll_area_id}' is not a QScrollArea.")
        content_entities = [
            child for child in self.get_children(scroll_area_id) if child.type == "ContainerContent"
        ]
        if not content_entities:
            return None
        return content_entities[0]

    def get_splitter_panes(self, splitter_id: str) -> list[EntityModel]:
        splitter = self._require_entity(splitter_id)
        if splitter.type != "QSplitter":
            raise ValueError(f"Entity '{splitter_id}' is not a QSplitter.")
        return self.get_children(splitter_id)

    def get_wizard_pages(self, wizard_id: str) -> list[EntityModel]:
        wizard = self._require_entity(wizard_id)
        if wizard.type != "QWizard":
            raise ValueError(f"Entity '{wizard_id}' is not a QWizard.")
        return self.get_children(wizard_id)

    def create_entity(
        self,
        type_name: str,
        parent_id: str,
        geometry: dict | None = None,
        properties: dict | None = None,
        name: str | None = None,
    ) -> EntityModel:
        definition = self.widget_registry.get_type(type_name)
        if parent_id != self.form_root.id and parent_id not in self.entities_by_id:
            raise ValueError(f"Unknown parent_id: {parent_id}")
        if not self.can_parent(parent_id, type_name):
            raise ValueError(f"Parent '{parent_id}' is not allowed for '{type_name}'.")

        entity_id = self.id_generator.next(self.widget_registry.get_name_prefix(type_name))
        existing_names = {entity.name for entity in self.entities_by_id.values()}
        entity_name = name or make_unique_name(existing_names, definition.name_prefix)
        entity_properties = {**self.widget_registry.get_default_properties(type_name), **(properties or {})}
        if geometry is None:
            width, height = self.widget_registry.get_default_size(type_name)
            entity_geometry = make_geometry(0, 0, width, height)
        else:
            entity_geometry = normalize_geometry(geometry)

        entity = EntityModel(
            id=entity_id,
            type=type_name,
            parent_id=parent_id,
            name=entity_name,
            order=len(self.get_children(parent_id)),
            geometry=entity_geometry,
            properties=entity_properties,
        )
        self.entities_by_id[entity.id] = entity
        self.mark_dirty()
        return entity

    def can_parent(self, parent_id: str, child_type: str) -> bool:
        parent_type = self.get_parent_type(parent_id)
        return self.widget_registry.can_parent(parent_type, child_type)

    def get_parent_type(self, parent_id: str) -> str:
        if parent_id == self.form_root.id:
            return "FormRoot"
        return self._require_entity(parent_id).type

    def create_tab_widget(
        self,
        parent_id: str,
        geometry: dict | None = None,
        name: str | None = None,
    ) -> EntityModel:
        tab_widget = self.create_entity(
            type_name="QTabWidget",
            parent_id=parent_id,
            geometry=geometry,
            properties={"current_index": 0, "tabs_closable": False},
            name=name,
        )
        self.add_tab_page(tab_widget.id, "Tab 1")
        self.add_tab_page(tab_widget.id, "Tab 2")
        self.set_current_tab(tab_widget.id, 0)
        self.mark_dirty()
        return tab_widget

    def create_scroll_area(
        self,
        parent_id: str,
        geometry: dict | None = None,
        name: str | None = None,
    ) -> EntityModel:
        scroll_area = self.create_entity(
            type_name="QScrollArea",
            parent_id=parent_id,
            geometry=geometry,
            properties={"widget_resizable": True},
            name=name,
        )
        content_geometry = make_geometry(
            0,
            0,
            int(scroll_area.geometry["width"]),
            int(scroll_area.geometry["height"]),
        )
        self.create_entity(
            type_name="ContainerContent",
            parent_id=scroll_area.id,
            geometry=content_geometry,
        )
        self.mark_dirty()
        return scroll_area

    def create_splitter(
        self,
        parent_id: str,
        geometry: dict | None = None,
        orientation: str = "horizontal",
        name: str | None = None,
    ) -> EntityModel:
        splitter = self.create_entity(
            type_name="QSplitter",
            parent_id=parent_id,
            geometry=geometry,
            properties={"orientation": orientation, "sizes": [1, 1]},
            name=name,
        )
        self.create_entity(type_name="SplitterPane", parent_id=splitter.id)
        self.create_entity(type_name="SplitterPane", parent_id=splitter.id)
        self._sync_internal_children(splitter)
        self.mark_dirty()
        return splitter

    def create_wizard(
        self,
        parent_id: str,
        geometry: dict | None = None,
        name: str | None = None,
    ) -> EntityModel:
        normalized_geometry = geometry
        if geometry is not None:
            min_width, min_height = self._normalize_size_constraints("QWizard", geometry["width"], geometry["height"])
            normalized_geometry = {
                **geometry,
                "width": min_width,
                "height": min_height,
            }
        wizard = self.create_entity(
            type_name="QWizard",
            parent_id=parent_id,
            geometry=normalized_geometry,
            properties={"window_title": "Wizard", "current_index": 0},
            name=name,
        )
        self.add_wizard_page(wizard.id, "Page 1", "")
        self.add_wizard_page(wizard.id, "Page 2", "")
        self.set_current_wizard_page(wizard.id, 0)
        self.mark_dirty()
        return wizard

    def add_tab_page(self, tab_widget_id: str, title: str | None = None) -> EntityModel:
        tab_pages = self.get_tab_pages(tab_widget_id)
        next_index = len(tab_pages) + 1
        tab_page = self.create_entity(
            type_name="TabPage",
            parent_id=tab_widget_id,
            properties={"title": title or f"Tab {next_index}"},
        )
        self.set_current_tab(tab_widget_id, len(tab_pages))
        self.mark_dirty()
        return tab_page

    def remove_tab_page(self, tab_widget_id: str, tab_page_id: str) -> None:
        tab_pages = self.get_tab_pages(tab_widget_id)
        if len(tab_pages) <= 1:
            raise ValueError("QTabWidget must keep at least one TabPage.")
        if tab_page_id not in {page.id for page in tab_pages}:
            raise ValueError(f"TabPage '{tab_page_id}' does not belong to '{tab_widget_id}'.")

        tab_widget = self._require_entity(tab_widget_id)
        current_index = int(tab_widget.properties.get("current_index", 0))
        remove_index = next(index for index, page in enumerate(tab_pages) if page.id == tab_page_id)
        self.delete_subtree(tab_page_id)

        remaining_pages = self.get_tab_pages(tab_widget_id)
        for index, page in enumerate(remaining_pages):
            page.order = index

        if current_index >= len(remaining_pages):
            current_index = len(remaining_pages) - 1
        elif remove_index < current_index:
            current_index -= 1
        self.set_current_tab(tab_widget_id, max(0, current_index))
        self.mark_dirty()

    def rename_tab_page(self, tab_page_id: str, new_title: str) -> None:
        tab_page = self._require_entity(tab_page_id)
        if tab_page.type != "TabPage":
            raise ValueError(f"Entity '{tab_page_id}' is not a TabPage.")
        tab_page.properties["title"] = str(new_title)
        self.mark_dirty()

    def set_current_tab(self, tab_widget_id: str, index: int) -> None:
        tab_widget = self._require_entity(tab_widget_id)
        if tab_widget.type != "QTabWidget":
            raise ValueError(f"Entity '{tab_widget_id}' is not a QTabWidget.")
        tab_pages = self.get_tab_pages(tab_widget_id)
        if not 0 <= int(index) < len(tab_pages):
            raise ValueError("Tab index is out of range.")
        tab_widget.properties["current_index"] = int(index)
        self.mark_dirty()

    def set_splitter_orientation(self, splitter_id: str, orientation: str) -> None:
        splitter = self._require_entity(splitter_id)
        if splitter.type != "QSplitter":
            raise ValueError(f"Entity '{splitter_id}' is not a QSplitter.")
        normalized_orientation = str(orientation).strip().lower()
        if normalized_orientation not in {"horizontal", "vertical"}:
            raise ValueError("Splitter orientation must be 'horizontal' or 'vertical'.")
        splitter.properties["orientation"] = normalized_orientation
        self._sync_internal_children(splitter)
        self.mark_dirty()

    def set_splitter_sizes(self, splitter_id: str, sizes: list[int]) -> None:
        splitter = self._require_entity(splitter_id)
        if splitter.type != "QSplitter":
            raise ValueError(f"Entity '{splitter_id}' is not a QSplitter.")
        if len(sizes) != 2:
            raise ValueError("QSplitter must have exactly two pane sizes.")
        splitter.properties["sizes"] = [max(1, int(size)) for size in sizes]
        self._sync_internal_children(splitter)
        self.mark_dirty()

    def add_wizard_page(
        self,
        wizard_id: str,
        title: str | None = None,
        subtitle: str | None = None,
    ) -> EntityModel:
        wizard_pages = self.get_wizard_pages(wizard_id)
        next_index = len(wizard_pages) + 1
        page = self.create_entity(
            type_name="WizardPage",
            parent_id=wizard_id,
            properties={
                "title": title or f"Page {next_index}",
                "subtitle": subtitle or "",
            },
        )
        self.set_current_wizard_page(wizard_id, len(wizard_pages))
        self.mark_dirty()
        return page

    def remove_wizard_page(self, wizard_id: str, wizard_page_id: str) -> None:
        wizard_pages = self.get_wizard_pages(wizard_id)
        if len(wizard_pages) <= 1:
            raise ValueError("QWizard must keep at least one WizardPage.")
        if wizard_page_id not in {page.id for page in wizard_pages}:
            raise ValueError(f"WizardPage '{wizard_page_id}' does not belong to '{wizard_id}'.")
        wizard = self._require_entity(wizard_id)
        current_index = int(wizard.properties.get("current_index", 0))
        remove_index = next(index for index, page in enumerate(wizard_pages) if page.id == wizard_page_id)
        self.delete_subtree(wizard_page_id)
        remaining_pages = self.get_wizard_pages(wizard_id)
        for index, page in enumerate(remaining_pages):
            page.order = index
        if current_index >= len(remaining_pages):
            current_index = len(remaining_pages) - 1
        elif remove_index < current_index:
            current_index -= 1
        self.set_current_wizard_page(wizard_id, max(0, current_index))
        self.mark_dirty()

    def rename_wizard_page(
        self,
        wizard_page_id: str,
        new_title: str,
        new_subtitle: str | None = None,
    ) -> None:
        page = self._require_entity(wizard_page_id)
        if page.type != "WizardPage":
            raise ValueError(f"Entity '{wizard_page_id}' is not a WizardPage.")
        page.properties["title"] = str(new_title)
        if new_subtitle is not None:
            page.properties["subtitle"] = str(new_subtitle)
        self.mark_dirty()

    def set_current_wizard_page(self, wizard_id: str, index: int) -> None:
        wizard = self._require_entity(wizard_id)
        if wizard.type != "QWizard":
            raise ValueError(f"Entity '{wizard_id}' is not a QWizard.")
        pages = self.get_wizard_pages(wizard_id)
        if not 0 <= int(index) < len(pages):
            raise ValueError("Wizard page index is out of range.")
        wizard.properties["current_index"] = int(index)
        self.mark_dirty()

    def rename_entity(self, entity_id: str, new_name: str) -> None:
        entity = self._require_entity(entity_id)
        entity.name = str(new_name)
        self.mark_dirty()

    def update_property(self, entity_id: str, property_name: str, value: object) -> None:
        entity = self._require_entity(entity_id)
        entity.properties[property_name] = value
        self._normalize_entity_properties(entity, changed_property=property_name)
        self.mark_dirty()

    def update_properties(self, entity_id: str, values: dict) -> None:
        entity = self._require_entity(entity_id)
        entity.properties.update(values)
        self._normalize_entity_properties(entity)
        self.mark_dirty()

    def update_geometry(self, entity_id: str, x: int, y: int, width: int, height: int) -> None:
        entity = self._require_entity(entity_id)
        width, height = self._normalize_size_constraints(entity.type, width, height)
        entity.geometry = make_geometry(x, y, width, height)
        self._sync_internal_children(entity)
        self.mark_dirty()

    def move_entity(self, entity_id: str, x: int, y: int) -> None:
        entity = self._require_entity(entity_id)
        entity.geometry["x"] = int(x)
        entity.geometry["y"] = int(y)
        self.mark_dirty()

    def resize_entity(self, entity_id: str, width: int, height: int) -> None:
        entity = self._require_entity(entity_id)
        width, height = self._normalize_size_constraints(entity.type, width, height)
        entity.geometry["width"] = int(width)
        entity.geometry["height"] = int(height)
        self._sync_internal_children(entity)
        self.mark_dirty()

    def reparent_entity(
        self,
        entity_id: str,
        new_parent_id: str,
        x: int | None = None,
        y: int | None = None,
    ) -> None:
        entity = self._require_entity(entity_id)
        if new_parent_id != self.form_root.id:
            self._require_entity(new_parent_id)
        if not self.can_parent(new_parent_id, entity.type):
            raise ValueError(f"Parent '{new_parent_id}' is not allowed for '{entity.type}'.")
        old_parent_id = entity.parent_id
        new_order = len([child for child in self.get_children(new_parent_id) if child.id != entity_id])
        entity.parent_id = new_parent_id
        entity.order = new_order
        if x is not None:
            entity.geometry["x"] = int(x)
        if y is not None:
            entity.geometry["y"] = int(y)
        self._reindex_children(old_parent_id)
        self._reindex_children(new_parent_id)
        self.mark_dirty()

    def set_order(self, entity_id: str, new_order: int) -> None:
        entity = self._require_entity(entity_id)
        siblings = [child for child in self.get_children(entity.parent_id) if child.id != entity_id]
        target_index = max(0, min(int(new_order), len(siblings)))
        siblings.insert(target_index, entity)
        for index, sibling in enumerate(siblings):
            sibling.order = index
        self.mark_dirty()

    def delete_entity(self, entity_id: str) -> None:
        entity = self._require_entity(entity_id)
        parent_id = entity.parent_id
        if self.get_children(entity.id):
            self.delete_subtree(entity.id)
            self._reindex_children(parent_id)
            return
        del self.entities_by_id[entity_id]
        self._reindex_children(parent_id)
        self.mark_dirty()

    def delete_subtree(self, entity_id: str) -> None:
        entity = self._require_entity(entity_id)
        parent_id = entity.parent_id
        descendants = self.get_descendants(entity_id)
        for descendant in reversed(descendants):
            self.entities_by_id.pop(descendant.id, None)
        self.entities_by_id.pop(entity_id, None)
        self._reindex_children(parent_id)
        self.mark_dirty()

    def mark_dirty(self) -> None:
        self.is_dirty = True

    def clear_dirty(self) -> None:
        self.is_dirty = False

    def _require_entity(self, entity_id: str) -> EntityModel:
        entity = self.get_entity(entity_id)
        if entity is None:
            raise ValueError(f"Unknown entity_id: {entity_id}")
        return entity

    def _sync_internal_children(self, entity: EntityModel) -> None:
        if entity.type == "QScrollArea":
            content = self.get_scroll_content(entity.id)
            if content is not None:
                content.geometry = make_geometry(
                    0,
                    0,
                    int(entity.geometry["width"]),
                    int(entity.geometry["height"]),
                )
        elif entity.type == "QSplitter":
            panes = self.get_splitter_panes(entity.id)
            if len(panes) != 2:
                return
            orientation = str(entity.properties.get("orientation", "horizontal")).lower()
            sizes = entity.properties.get("sizes", [1, 1])
            if not isinstance(sizes, list) or len(sizes) != 2:
                sizes = [1, 1]
            first_size = max(1, int(sizes[0]))
            second_size = max(1, int(sizes[1]))
            total = first_size + second_size
            width = max(1, int(entity.geometry["width"]))
            height = max(1, int(entity.geometry["height"]))
            if orientation == "vertical":
                first_height = max(1, round(height * first_size / total))
                second_height = max(1, height - first_height)
                panes[0].geometry = make_geometry(0, 0, width, first_height)
                panes[1].geometry = make_geometry(0, first_height, width, second_height)
            else:
                first_width = max(1, round(width * first_size / total))
                second_width = max(1, width - first_width)
                panes[0].geometry = make_geometry(0, 0, first_width, height)
                panes[1].geometry = make_geometry(first_width, 0, second_width, height)

    def _normalize_size_constraints(
        self,
        type_name: str,
        width: int,
        height: int,
    ) -> tuple[int, int]:
        normalized_width = int(width)
        normalized_height = int(height)
        if type_name == "QWizard":
            definition = self.widget_registry.get_type(type_name)
            if definition is not None:
                min_width, min_height = definition.default_size
                normalized_width = max(int(min_width), normalized_width)
                normalized_height = max(int(min_height), normalized_height)
        return normalized_width, normalized_height

    def _reindex_children(self, parent_id: str) -> None:
        for index, child in enumerate(self.get_children(parent_id)):
            child.order = index

    def _normalize_entity_properties(
        self,
        entity: EntityModel,
        changed_property: str | None = None,
    ) -> None:
        if entity.type == "QComboBox":
            self._normalize_combo_box_properties(entity)
        elif entity.type == "QListView":
            self._normalize_list_view_properties(entity)
        elif entity.type == "QListWidget":
            self._normalize_list_widget_properties(entity, changed_property=changed_property)
        elif entity.type == "QTreeView":
            self._normalize_tree_view_properties(entity)
        elif entity.type == "QTableView":
            self._normalize_table_view_properties(entity)
        elif entity.type == "QTableWidget":
            self._normalize_table_widget_properties(entity)
        elif entity.type == "QTreeWidget":
            self._normalize_tree_widget_properties(entity)
        elif entity.type == "QDateEdit":
            self._normalize_date_edit_properties(entity, changed_property=changed_property)
        elif entity.type == "QCalendarWidget":
            self._normalize_calendar_widget_properties(entity, changed_property=changed_property)
        elif entity.type == "QFontComboBox":
            self._normalize_font_combo_box_properties(entity)
        elif entity.type == "QKeySequenceEdit":
            self._normalize_key_sequence_edit_properties(entity)
        elif entity.type == "QDial":
            self._normalize_dial_properties(entity, changed_property=changed_property)
        elif entity.type == "QLCDNumber":
            self._normalize_lcd_number_properties(entity)
        elif entity.type == "QDateTimeEdit":
            self._normalize_datetime_edit_properties(entity, changed_property=changed_property)
        elif entity.type == "QTimeEdit":
            self._normalize_time_edit_properties(entity, changed_property=changed_property)
        elif entity.type == "QPlainTextEdit":
            self._normalize_plain_text_edit_properties(entity)
        elif entity.type == "QTextEdit":
            self._normalize_text_edit_properties(entity)
        elif entity.type == "QProgressBar":
            self._normalize_progress_bar_properties(entity, changed_property=changed_property)
        elif entity.type == "QSlider":
            self._normalize_slider_properties(entity, changed_property=changed_property)
        elif entity.type == "QSpinBox":
            self._normalize_spin_box_properties(entity, changed_property=changed_property)
        elif entity.type == "QDoubleSpinBox":
            self._normalize_double_spin_box_properties(entity, changed_property=changed_property)

    def _normalize_combo_box_properties(self, entity: EntityModel) -> None:
        items = entity.properties.get("items", [])
        if not isinstance(items, list):
            return

        current_index = entity.properties.get("current_index", 0)
        if not isinstance(current_index, int):
            return

        if not items:
            entity.properties["current_index"] = 0
            return

        entity.properties["current_index"] = max(0, min(current_index, len(items) - 1))

    def _normalize_list_view_properties(self, entity: EntityModel) -> None:
        raw_items = entity.properties.get("model_items", [])
        if isinstance(raw_items, (list, tuple)):
            items = [str(item) for item in raw_items]
        elif raw_items in {None, ""}:
            items = []
        else:
            items = [str(raw_items)]
        entity.properties["model_items"] = items

    def _normalize_tree_view_properties(self, entity: EntityModel) -> None:
        raw_headers = entity.properties.get("header_labels", [])
        if isinstance(raw_headers, (list, tuple)):
            header_labels = [str(item) for item in raw_headers]
        elif raw_headers in {None, ""}:
            header_labels = []
        else:
            header_labels = [str(raw_headers)]
        entity.properties["header_labels"] = header_labels

    def _normalize_table_view_properties(self, entity: EntityModel) -> None:
        column_count = int(entity.properties.get("column_count", 3))
        if column_count < 0:
            column_count = 0

        raw_headers = entity.properties.get("header_labels", [])
        if isinstance(raw_headers, (list, tuple)):
            header_labels = [str(item) for item in raw_headers]
        elif raw_headers in {None, ""}:
            header_labels = []
        else:
            header_labels = [str(raw_headers)]

        entity.properties["column_count"] = column_count
        entity.properties["header_labels"] = header_labels[:column_count]

    def _normalize_list_widget_properties(
        self,
        entity: EntityModel,
        changed_property: str | None = None,
    ) -> None:
        raw_items = entity.properties.get("items", [])
        if isinstance(raw_items, list):
            items = [str(item) for item in raw_items]
        elif isinstance(raw_items, tuple):
            items = [str(item) for item in raw_items]
        elif raw_items in {None, ""}:
            items = []
        else:
            items = [str(raw_items)]

        current_row = int(entity.properties.get("current_row", -1))
        current_text = str(entity.properties.get("current_text", ""))
        if current_row < -1:
            current_row = -1
        if not items:
            current_row = -1
            current_text = ""
        elif changed_property == "current_text":
            if current_text in items:
                current_row = items.index(current_text)
            else:
                current_row = -1
                current_text = ""
        elif current_text and current_text in items:
            current_row = items.index(current_text)
        elif current_row >= len(items):
            current_row = -1
            current_text = ""
        elif current_row >= 0:
            current_text = items[current_row]
        else:
            current_text = ""

        entity.properties["items"] = items
        entity.properties["current_row"] = current_row
        entity.properties["current_text"] = current_text

    def _normalize_table_widget_properties(self, entity: EntityModel) -> None:
        row_count = int(entity.properties.get("row_count", 3))
        column_count = int(entity.properties.get("column_count", 3))
        if row_count < 0:
            row_count = 0
        if column_count < 0:
            column_count = 0

        raw_horizontal = entity.properties.get("horizontal_headers", [])
        if isinstance(raw_horizontal, (list, tuple)):
            horizontal_headers = [str(item) for item in raw_horizontal]
        elif raw_horizontal in {None, ""}:
            horizontal_headers = []
        else:
            horizontal_headers = [str(raw_horizontal)]

        raw_vertical = entity.properties.get("vertical_headers", [])
        if isinstance(raw_vertical, (list, tuple)):
            vertical_headers = [str(item) for item in raw_vertical]
        elif raw_vertical in {None, ""}:
            vertical_headers = []
        else:
            vertical_headers = [str(raw_vertical)]

        raw_cell_values = entity.properties.get("cell_values", [])
        cell_values: list[list[str]] = []
        if isinstance(raw_cell_values, (list, tuple)):
            for raw_row in raw_cell_values[:row_count]:
                if isinstance(raw_row, (list, tuple)):
                    normalized_row = [str(item) for item in list(raw_row)[:column_count]]
                elif raw_row in {None, ""}:
                    normalized_row = []
                else:
                    normalized_row = [str(raw_row)][:column_count]
                cell_values.append(normalized_row)

        entity.properties["row_count"] = row_count
        entity.properties["column_count"] = column_count
        entity.properties["horizontal_headers"] = horizontal_headers[:column_count]
        entity.properties["vertical_headers"] = vertical_headers[:row_count]
        entity.properties["cell_values"] = cell_values

    def _normalize_tree_widget_properties(self, entity: EntityModel) -> None:
        column_count = int(entity.properties.get("column_count", 1))
        if column_count < 0:
            column_count = 0

        raw_headers = entity.properties.get("header_labels", [])
        if isinstance(raw_headers, (list, tuple)):
            header_labels = [str(item) for item in raw_headers]
        elif raw_headers in {None, ""}:
            header_labels = []
        else:
            header_labels = [str(raw_headers)]

        raw_tree_items = entity.properties.get("tree_items", [])

        entity.properties["column_count"] = column_count
        entity.properties["header_labels"] = [] if column_count == 0 else header_labels[:column_count]
        entity.properties["tree_items"] = self._normalize_tree_widget_items(raw_tree_items, column_count)

    def _normalize_tree_widget_items(
        self,
        raw_items: object,
        column_count: int,
    ) -> list[dict[str, object]]:
        if not isinstance(raw_items, (list, tuple)):
            return []
        normalized_items: list[dict[str, object]] = []
        for raw_item in raw_items:
            if not isinstance(raw_item, dict):
                continue
            raw_texts = raw_item.get("texts", [])
            if isinstance(raw_texts, (list, tuple)):
                texts = [str(item) for item in list(raw_texts)[:column_count]]
            elif raw_texts in {None, ""}:
                texts = []
            else:
                texts = [str(raw_texts)][:column_count]
            raw_children = raw_item.get("children", [])
            children = self._normalize_tree_widget_items(raw_children, column_count)
            normalized_items.append(
                {
                    "texts": texts,
                    "children": children,
                }
            )
        return normalized_items

    def _normalize_date_edit_properties(
        self,
        entity: EntityModel,
        changed_property: str | None = None,
    ) -> None:
        minimum_date = normalize_date_string(str(entity.properties.get("minimum_date", "1900-01-01")), "1900-01-01")
        maximum_date = normalize_date_string(str(entity.properties.get("maximum_date", "2100-12-31")), "2100-12-31")
        minimum_parsed = parse_date_string(minimum_date)
        maximum_parsed = parse_date_string(maximum_date)
        if minimum_parsed is None or maximum_parsed is None:
            raise ValueError("Date edit normalization requires valid fallback dates.")

        if minimum_parsed > maximum_parsed:
            if changed_property == "maximum_date":
                minimum_parsed = maximum_parsed
            else:
                maximum_parsed = minimum_parsed

        current_date = normalize_date_string(str(entity.properties.get("date", "2026-01-01")), "2026-01-01")
        current_parsed = parse_date_string(current_date)
        if current_parsed is None:
            current_parsed = minimum_parsed

        if current_parsed < minimum_parsed:
            current_parsed = minimum_parsed
        if current_parsed > maximum_parsed:
            current_parsed = maximum_parsed

        entity.properties["minimum_date"] = format_date_string(minimum_parsed)
        entity.properties["maximum_date"] = format_date_string(maximum_parsed)
        entity.properties["date"] = format_date_string(current_parsed)

    def _normalize_time_edit_properties(
        self,
        entity: EntityModel,
        changed_property: str | None = None,
    ) -> None:
        minimum_time = normalize_time_string(str(entity.properties.get("minimum_time", "00:00:00")), "00:00:00")
        maximum_time = normalize_time_string(str(entity.properties.get("maximum_time", "23:59:59")), "23:59:59")
        minimum_parsed = parse_time_string(minimum_time)
        maximum_parsed = parse_time_string(maximum_time)
        if minimum_parsed is None or maximum_parsed is None:
            raise ValueError("Time edit normalization requires valid fallback times.")

        if minimum_parsed > maximum_parsed:
            if changed_property == "maximum_time":
                minimum_parsed = maximum_parsed
            else:
                maximum_parsed = minimum_parsed

        current_time = normalize_time_string(str(entity.properties.get("time", "12:00:00")), "12:00:00")
        current_parsed = parse_time_string(current_time)
        if current_parsed is None:
            current_parsed = minimum_parsed

        if current_parsed < minimum_parsed:
            current_parsed = minimum_parsed
        if current_parsed > maximum_parsed:
            current_parsed = maximum_parsed

        entity.properties["minimum_time"] = format_time_string(minimum_parsed)
        entity.properties["maximum_time"] = format_time_string(maximum_parsed)
        entity.properties["time"] = format_time_string(current_parsed)

    def _normalize_datetime_edit_properties(
        self,
        entity: EntityModel,
        changed_property: str | None = None,
    ) -> None:
        minimum_datetime = normalize_datetime_string(
            str(entity.properties.get("minimum_datetime", "1900-01-01 00:00:00")),
            "1900-01-01 00:00:00",
        )
        maximum_datetime = normalize_datetime_string(
            str(entity.properties.get("maximum_datetime", "2100-12-31 23:59:59")),
            "2100-12-31 23:59:59",
        )
        minimum_parsed = parse_datetime_string(minimum_datetime)
        maximum_parsed = parse_datetime_string(maximum_datetime)
        if minimum_parsed is None or maximum_parsed is None:
            raise ValueError("DateTime edit normalization requires valid fallback datetimes.")

        if minimum_parsed > maximum_parsed:
            if changed_property == "maximum_datetime":
                minimum_parsed = maximum_parsed
            else:
                maximum_parsed = minimum_parsed

        current_datetime = normalize_datetime_string(
            str(entity.properties.get("datetime", "2026-01-01 12:00:00")),
            "2026-01-01 12:00:00",
        )
        current_parsed = parse_datetime_string(current_datetime)
        if current_parsed is None:
            current_parsed = minimum_parsed

        if current_parsed < minimum_parsed:
            current_parsed = minimum_parsed
        if current_parsed > maximum_parsed:
            current_parsed = maximum_parsed

        entity.properties["minimum_datetime"] = format_datetime_string(minimum_parsed)
        entity.properties["maximum_datetime"] = format_datetime_string(maximum_parsed)
        entity.properties["datetime"] = format_datetime_string(current_parsed)

    def _normalize_calendar_widget_properties(
        self,
        entity: EntityModel,
        changed_property: str | None = None,
    ) -> None:
        minimum_date = normalize_date_string(str(entity.properties.get("minimum_date", "1900-01-01")), "1900-01-01")
        maximum_date = normalize_date_string(str(entity.properties.get("maximum_date", "2100-12-31")), "2100-12-31")
        minimum_parsed = parse_date_string(minimum_date)
        maximum_parsed = parse_date_string(maximum_date)
        if minimum_parsed is None or maximum_parsed is None:
            raise ValueError("Calendar widget normalization requires valid fallback dates.")

        if minimum_parsed > maximum_parsed:
            if changed_property == "maximum_date":
                minimum_parsed = maximum_parsed
            else:
                maximum_parsed = minimum_parsed

        selected_date = normalize_date_string(str(entity.properties.get("selected_date", "2026-01-01")), "2026-01-01")
        selected_parsed = parse_date_string(selected_date)
        if selected_parsed is None:
            selected_parsed = minimum_parsed

        if selected_parsed < minimum_parsed:
            selected_parsed = minimum_parsed
        if selected_parsed > maximum_parsed:
            selected_parsed = maximum_parsed

        entity.properties["minimum_date"] = format_date_string(minimum_parsed)
        entity.properties["maximum_date"] = format_date_string(maximum_parsed)
        entity.properties["selected_date"] = format_date_string(selected_parsed)

    def _normalize_font_combo_box_properties(self, entity: EntityModel) -> None:
        entity.properties["current_font_family"] = str(entity.properties.get("current_font_family", ""))

    def _normalize_key_sequence_edit_properties(self, entity: EntityModel) -> None:
        entity.properties["key_sequence"] = str(entity.properties.get("key_sequence", ""))

    def _normalize_dial_properties(
        self,
        entity: EntityModel,
        changed_property: str | None = None,
    ) -> None:
        minimum = int(entity.properties.get("minimum", 0))
        maximum = int(entity.properties.get("maximum", 100))
        if minimum > maximum:
            if changed_property == "maximum":
                minimum = maximum
            else:
                maximum = minimum
        step = int(entity.properties.get("step", 1))
        if step < 1:
            step = 1
        value = int(entity.properties.get("value", 0))
        if value < minimum:
            value = minimum
        if value > maximum:
            value = maximum
        entity.properties["minimum"] = minimum
        entity.properties["maximum"] = maximum
        entity.properties["step"] = step
        entity.properties["value"] = value

    def _normalize_lcd_number_properties(self, entity: EntityModel) -> None:
        digit_count = int(entity.properties.get("digit_count", 5))
        if digit_count < 1:
            digit_count = 1
        entity.properties["digit_count"] = digit_count
        entity.properties["value"] = int(entity.properties.get("value", 0))

    def _normalize_spin_box_properties(
        self,
        entity: EntityModel,
        changed_property: str | None = None,
    ) -> None:
        minimum = int(entity.properties.get("minimum", 0))
        maximum = int(entity.properties.get("maximum", 99))
        if minimum > maximum:
            if changed_property == "maximum":
                minimum = maximum
            else:
                maximum = minimum

        step = int(entity.properties.get("step", 1))
        if step <= 0:
            step = 1

        value = int(entity.properties.get("value", 0))
        value = max(minimum, min(value, maximum))

        entity.properties["minimum"] = minimum
        entity.properties["maximum"] = maximum
        entity.properties["step"] = step
        entity.properties["value"] = value
        entity.properties["prefix"] = str(entity.properties.get("prefix", ""))
        entity.properties["suffix"] = str(entity.properties.get("suffix", ""))

    def _normalize_slider_properties(
        self,
        entity: EntityModel,
        changed_property: str | None = None,
    ) -> None:
        orientation = str(entity.properties.get("orientation", "horizontal")).strip().lower()
        if orientation not in {"horizontal", "vertical"}:
            orientation = "horizontal"

        minimum = int(entity.properties.get("minimum", 0))
        maximum = int(entity.properties.get("maximum", 100))
        if minimum > maximum:
            if changed_property == "maximum":
                minimum = maximum
            else:
                maximum = minimum

        step = int(entity.properties.get("step", 1))
        if step <= 0:
            step = 1

        value = int(entity.properties.get("value", 0))
        value = max(minimum, min(value, maximum))

        entity.properties["orientation"] = orientation
        entity.properties["minimum"] = minimum
        entity.properties["maximum"] = maximum
        entity.properties["step"] = step
        entity.properties["value"] = value

    def _normalize_progress_bar_properties(
        self,
        entity: EntityModel,
        changed_property: str | None = None,
    ) -> None:
        minimum = int(entity.properties.get("minimum", 0))
        maximum = int(entity.properties.get("maximum", 100))
        if minimum > maximum:
            if changed_property == "maximum":
                minimum = maximum
            else:
                maximum = minimum

        value = int(entity.properties.get("value", 0))
        value = max(minimum, min(value, maximum))
        text_visible = bool(entity.properties.get("text_visible", True))

        entity.properties["minimum"] = minimum
        entity.properties["maximum"] = maximum
        entity.properties["value"] = value
        entity.properties["text_visible"] = text_visible

    def _normalize_text_edit_properties(self, entity: EntityModel) -> None:
        entity.properties["text"] = str(entity.properties.get("text", ""))
        entity.properties["placeholder"] = str(entity.properties.get("placeholder", ""))
        entity.properties["read_only"] = bool(entity.properties.get("read_only", False))

    def _normalize_plain_text_edit_properties(self, entity: EntityModel) -> None:
        entity.properties["text"] = str(entity.properties.get("text", ""))
        entity.properties["placeholder"] = str(entity.properties.get("placeholder", ""))
        entity.properties["read_only"] = bool(entity.properties.get("read_only", False))

    def _normalize_double_spin_box_properties(
        self,
        entity: EntityModel,
        changed_property: str | None = None,
    ) -> None:
        minimum = float(entity.properties.get("minimum", 0.0))
        maximum = float(entity.properties.get("maximum", 99.0))
        if minimum > maximum:
            if changed_property == "maximum":
                minimum = maximum
            else:
                maximum = minimum

        step = float(entity.properties.get("step", 1.0))
        if step <= 0:
            step = 1.0

        decimals = int(entity.properties.get("decimals", 2))
        if decimals < 0:
            decimals = 0
        if decimals > 10:
            decimals = 10

        value = float(entity.properties.get("value", 0.0))
        value = max(minimum, min(value, maximum))

        entity.properties["minimum"] = minimum
        entity.properties["maximum"] = maximum
        entity.properties["step"] = step
        entity.properties["decimals"] = decimals
        entity.properties["value"] = value
        entity.properties["prefix"] = str(entity.properties.get("prefix", ""))
        entity.properties["suffix"] = str(entity.properties.get("suffix", ""))
