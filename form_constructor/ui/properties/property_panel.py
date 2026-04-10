from __future__ import annotations

from PySide6.QtCore import QSignalBlocker, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from form_constructor.document.form_document import FormDocument
from form_constructor.document.models import EntityModel
from form_constructor.registry.definitions import PropertyDefinition, WidgetTypeDefinition
from form_constructor.ui.properties.property_editor_factory import (
    PlainTextPropertyEditor,
    PropertyEditorFactory,
)


class PropertyPanel(QWidget):
    name_changed = Signal(str, str)
    property_changed = Signal(str, str, object)
    validation_error = Signal(str)
    geometry_changed = Signal(str, int, int, int, int)
    form_root_changed = Signal(str, str, int, int, str)
    tab_add_requested = Signal(str)
    tab_remove_requested = Signal(str, str)
    tab_rename_requested = Signal(str, str)
    current_tab_changed = Signal(str, int)
    splitter_orientation_changed = Signal(str, str)
    splitter_sizes_changed = Signal(str, list)
    wizard_add_requested = Signal(str)
    wizard_remove_requested = Signal(str, str)
    wizard_rename_requested = Signal(str, str, str)
    current_wizard_page_changed = Signal(str, int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._active_document: FormDocument | None = None
        self._active_entity_id: str | None = None
        self._active_entity_type: str | None = None
        self._active_definition: WidgetTypeDefinition | None = None
        self._selected_tab_page_id: str | None = None
        self._selected_wizard_page_id: str | None = None
        self._form_value_labels: dict[str, QLabel] = {}
        self._property_schema_map: dict[str, PropertyDefinition] = {}
        self._property_widgets: dict[str, QWidget] = {}
        self._property_row_labels: dict[str, QLabel] = {}
        self._editor_factory = PropertyEditorFactory()

        self._mode_stack = QStackedWidget()
        self._form_box = self._build_form_mode()
        self._entity_box = self._build_entity_mode()
        self._mode_stack.addWidget(self._form_box)
        self._mode_stack.addWidget(self._entity_box)

        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        self._scroll_area.setWidget(self._mode_stack)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._scroll_area, 1)
        self.clear()

    def _make_readonly_line_edit(self, initial_text: str = "") -> QLineEdit:
        line_edit = QLineEdit(initial_text)
        line_edit.setReadOnly(True)
        return line_edit

    def _build_form_mode(self) -> QWidget:
        box = QGroupBox("Form Properties")
        form_layout = QFormLayout(box)
        self._form_id_edit = self._make_readonly_line_edit("No active form")
        self._form_type_edit = self._make_readonly_line_edit("No active form")
        self._form_root_widget_type_edit = QComboBox()
        self._form_root_widget_type_edit.addItems(["QWidget", "QDialog"])
        self._form_name_edit = QLineEdit()
        self._form_window_title_edit = QLineEdit()
        self._form_width_spin = self._make_geometry_spin(minimum=240, maximum=10000)
        self._form_height_spin = self._make_geometry_spin(minimum=180, maximum=10000)

        self._form_name_edit.editingFinished.connect(self._emit_form_root_change)
        self._form_root_widget_type_edit.currentTextChanged.connect(lambda _: self._emit_form_root_change())
        self._form_window_title_edit.editingFinished.connect(self._emit_form_root_change)
        self._form_width_spin.editingFinished.connect(self._emit_form_root_change)
        self._form_height_spin.editingFinished.connect(self._emit_form_root_change)

        self._form_value_labels["id"] = self._form_id_edit
        self._form_value_labels["type"] = self._form_type_edit

        form_layout.addRow("ID", self._form_id_edit)
        form_layout.addRow("Type", self._form_type_edit)
        form_layout.addRow("Root Widget", self._form_root_widget_type_edit)
        form_layout.addRow("Name", self._form_name_edit)
        form_layout.addRow("Width", self._form_width_spin)
        form_layout.addRow("Height", self._form_height_spin)
        form_layout.addRow("Window Title", self._form_window_title_edit)
        return box

    def _build_entity_mode(self) -> QWidget:
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)

        info_box = QGroupBox("Object")
        info_layout = QFormLayout(info_box)
        self._entity_type_edit = self._make_readonly_line_edit()
        self._entity_id_edit = self._make_readonly_line_edit()
        self._entity_parent_edit = self._make_readonly_line_edit()
        self._entity_name_edit = QLineEdit()
        self._entity_name_edit.editingFinished.connect(self._emit_name_change)
        info_layout.addRow("Type", self._entity_type_edit)
        info_layout.addRow("ID", self._entity_id_edit)
        info_layout.addRow("Parent", self._entity_parent_edit)
        info_layout.addRow("Name", self._entity_name_edit)

        geometry_box = QGroupBox("Geometry")
        self._geometry_box = geometry_box
        geometry_layout = QFormLayout(geometry_box)
        self._x_spin = self._make_geometry_spin()
        self._y_spin = self._make_geometry_spin()
        self._width_spin = self._make_geometry_spin(minimum=1)
        self._height_spin = self._make_geometry_spin(minimum=1)
        for spin in (self._x_spin, self._y_spin, self._width_spin, self._height_spin):
            spin.editingFinished.connect(self._emit_geometry_change)
        geometry_layout.addRow("X", self._x_spin)
        geometry_layout.addRow("Y", self._y_spin)
        geometry_layout.addRow("Width", self._width_spin)
        geometry_layout.addRow("Height", self._height_spin)

        properties_box = QGroupBox("Properties")
        self._properties_box = properties_box
        self._properties_layout = QFormLayout(properties_box)

        self._tabs_box = self._build_tab_widget_section()
        self._splitter_box = self._build_splitter_section()
        self._wizard_box = self._build_wizard_section()

        layout.addWidget(info_box)
        layout.addWidget(self._geometry_box)
        layout.addWidget(properties_box)
        layout.addWidget(self._tabs_box)
        layout.addWidget(self._splitter_box)
        layout.addWidget(self._wizard_box)
        layout.addStretch(1)
        return wrapper

    def _build_tab_widget_section(self) -> QGroupBox:
        tabs_box = QGroupBox("Tabs")
        tabs_layout = QVBoxLayout(tabs_box)
        self._tabs_list = QListWidget()
        self._tab_title_edit = QLineEdit()
        self._add_tab_button = QPushButton("Add Tab")
        self._remove_tab_button = QPushButton("Remove Tab")
        self._tabs_list.currentRowChanged.connect(self._handle_tab_row_changed)
        self._tab_title_edit.editingFinished.connect(self._emit_tab_rename)
        self._add_tab_button.clicked.connect(self._emit_add_tab)
        self._remove_tab_button.clicked.connect(self._emit_remove_tab)
        tabs_layout.addWidget(self._tabs_list)
        tabs_form = QFormLayout()
        tabs_form.addRow("Tab Title", self._tab_title_edit)
        tabs_layout.addLayout(tabs_form)
        tabs_layout.addWidget(self._add_tab_button)
        tabs_layout.addWidget(self._remove_tab_button)
        return tabs_box

    def _build_splitter_section(self) -> QGroupBox:
        splitter_box = QGroupBox("Splitter")
        splitter_layout = QFormLayout(splitter_box)
        self._splitter_orientation_edit = QComboBox()
        self._splitter_orientation_edit.addItems(["horizontal", "vertical"])
        self._splitter_primary_size_spin = self._make_geometry_spin(minimum=1, maximum=9999)
        self._splitter_secondary_size_spin = self._make_geometry_spin(minimum=1, maximum=9999)
        splitter_sizes_widget = QWidget()
        splitter_sizes_layout = QHBoxLayout(splitter_sizes_widget)
        splitter_sizes_layout.setContentsMargins(0, 0, 0, 0)
        splitter_sizes_layout.addWidget(self._splitter_primary_size_spin)
        splitter_sizes_layout.addWidget(self._splitter_secondary_size_spin)
        self._splitter_orientation_edit.currentTextChanged.connect(
            self._emit_splitter_orientation_change
        )
        self._splitter_primary_size_spin.editingFinished.connect(self._emit_splitter_sizes_change)
        self._splitter_secondary_size_spin.editingFinished.connect(self._emit_splitter_sizes_change)
        splitter_layout.addRow("Orientation", self._splitter_orientation_edit)
        splitter_layout.addRow("Pane Sizes", splitter_sizes_widget)
        return splitter_box

    def _build_wizard_section(self) -> QGroupBox:
        wizard_box = QGroupBox("Wizard")
        wizard_layout = QVBoxLayout(wizard_box)
        self._wizard_pages_list = QListWidget()
        self._wizard_page_title_edit = QLineEdit()
        self._wizard_page_subtitle_edit = PlainTextPropertyEditor()
        self._wizard_page_subtitle_edit.setFixedHeight(72)
        self._add_wizard_page_button = QPushButton("Add Page")
        self._remove_wizard_page_button = QPushButton("Remove Page")
        self._wizard_pages_list.currentRowChanged.connect(self._handle_wizard_row_changed)
        self._wizard_page_title_edit.editingFinished.connect(self._emit_wizard_page_rename)
        self._wizard_page_subtitle_edit.editingFinished.connect(self._emit_wizard_page_rename)
        self._add_wizard_page_button.clicked.connect(self._emit_add_wizard_page)
        self._remove_wizard_page_button.clicked.connect(self._emit_remove_wizard_page)
        wizard_layout.addWidget(self._wizard_pages_list)
        wizard_form = QFormLayout()
        wizard_form.addRow("Page Title", self._wizard_page_title_edit)
        wizard_form.addRow("Page Subtitle", self._wizard_page_subtitle_edit)
        wizard_layout.addLayout(wizard_form)
        wizard_layout.addWidget(self._add_wizard_page_button)
        wizard_layout.addWidget(self._remove_wizard_page_button)
        return wizard_box

    def _make_geometry_spin(self, minimum: int = -9999, maximum: int = 9999) -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(minimum, maximum)
        return spin

    @staticmethod
    def _set_blocked_text(widget: QLineEdit, value: str) -> None:
        with QSignalBlocker(widget):
            widget.setText(value)

    @staticmethod
    def _set_blocked_plain_text(widget: PlainTextPropertyEditor, value: str) -> None:
        with QSignalBlocker(widget):
            widget.setPlainText(value)

    @staticmethod
    def _set_blocked_spin_value(widget: QSpinBox, value: int) -> None:
        with QSignalBlocker(widget):
            widget.setValue(value)

    @staticmethod
    def _set_blocked_combo_text(widget: QComboBox, value: str) -> None:
        with QSignalBlocker(widget):
            index = widget.findText(value)
            widget.setCurrentIndex(max(0, index))

    @staticmethod
    def _clear_blocked_list(widget: QListWidget) -> None:
        with QSignalBlocker(widget):
            widget.clear()

    def clear(self) -> None:
        self._active_document = None
        self._active_entity_id = None
        self._active_entity_type = None
        self._active_definition = None
        self._selected_tab_page_id = None
        self._selected_wizard_page_id = None
        for field in self._form_value_labels.values():
            field.setText("No active form")
        self._set_blocked_text(self._form_name_edit, "")
        self._set_blocked_combo_text(self._form_root_widget_type_edit, "QWidget")
        self._set_blocked_text(self._form_window_title_edit, "")
        self._set_blocked_spin_value(self._form_width_spin, self._form_width_spin.minimum())
        self._set_blocked_spin_value(self._form_height_spin, self._form_height_spin.minimum())
        self._clear_tabs_ui()
        self._clear_splitter_ui()
        self._clear_wizard_ui()
        self._mode_stack.setCurrentWidget(self._form_box)

    def set_document(self, document: FormDocument) -> None:
        self._active_document = document
        form_root = document.get_form_root()
        values = form_root.to_dict()
        for key, label in self._form_value_labels.items():
            label.setText(str(values.get(key, "")))
        self._set_blocked_combo_text(
            self._form_root_widget_type_edit,
            str(values.get("root_widget_type", "QWidget")),
        )
        self._set_blocked_text(self._form_name_edit, str(values.get("name", "")))
        self._set_blocked_text(self._form_window_title_edit, str(values.get("window_title", "")))
        self._set_blocked_spin_value(
            self._form_width_spin,
            int(values.get("width", self._form_width_spin.minimum())),
        )
        self._set_blocked_spin_value(
            self._form_height_spin,
            int(values.get("height", self._form_height_spin.minimum())),
        )

    def set_form_mode(self, document: FormDocument | None) -> None:
        self._active_entity_id = None
        self._active_entity_type = None
        self._active_definition = None
        self._selected_tab_page_id = None
        self._selected_wizard_page_id = None
        if document is not None:
            self.set_document(document)
        self._clear_tabs_ui()
        self._clear_splitter_ui()
        self._clear_wizard_ui()
        self._mode_stack.setCurrentWidget(self._form_box)

    def rebuild(self, document: FormDocument | None, entity: EntityModel | None = None) -> None:
        if document is None:
            self.clear()
            return
        if entity is None:
            self.set_form_mode(document)
            return
        self.set_entity_mode(document, self._display_entity_for(document, entity))

    def set_entity_mode(
        self,
        document: FormDocument,
        entity: EntityModel,
    ) -> None:
        entity = self._display_entity_for(document, entity)
        definition = document.widget_registry.get_type(entity.type)
        self._active_document = document
        self._active_entity_id = entity.id
        self._active_entity_type = entity.type
        self._active_definition = definition
        self._set_blocked_text(self._entity_type_edit, definition.type_name)
        self._set_blocked_text(self._entity_id_edit, entity.id)
        self._set_blocked_text(self._entity_parent_edit, entity.parent_id)
        self._set_blocked_text(self._entity_name_edit, entity.name)
        self._set_blocked_spin_value(self._x_spin, int(entity.geometry["x"]))
        self._set_blocked_spin_value(self._y_spin, int(entity.geometry["y"]))
        self._set_blocked_spin_value(self._width_spin, int(entity.geometry["width"]))
        self._set_blocked_spin_value(self._height_spin, int(entity.geometry["height"]))
        self._apply_schema_to_property_fields(entity, definition)
        self._apply_contextual_property_constraints(document, entity)
        self._apply_schema_to_basic_fields(definition)
        self._apply_geometry_mode(self._geometry_edit_mode_for(entity.type))

        self._apply_special_sections(document, entity)

        self._mode_stack.setCurrentWidget(self._entity_box)

    def _populate_tabs(self, document: FormDocument, entity: EntityModel) -> None:
        tab_pages = document.get_tab_pages(entity.id)
        current_index = int(entity.properties.get("current_index", 0))
        selected_row = self._resolve_selected_row(
            [tab_page.id for tab_page in tab_pages],
            self._selected_tab_page_id,
            current_index,
        )
        with QSignalBlocker(self._tabs_list):
            self._tabs_list.clear()
            for index, tab_page in enumerate(tab_pages):
                title = str(tab_page.properties.get("title", f"Tab {index + 1}"))
                self._tabs_list.addItem(title)
            if tab_pages:
                self._tabs_list.setCurrentRow(selected_row)
        self._update_tab_title_editor()
        self._add_tab_button.setEnabled(True)
        self._remove_tab_button.setEnabled(len(tab_pages) > 1)

    def _clear_tabs_ui(self) -> None:
        self._clear_blocked_list(self._tabs_list)
        self._set_blocked_text(self._tab_title_edit, "")
        self._selected_tab_page_id = None
        self._tab_title_edit.setEnabled(False)
        self._add_tab_button.setEnabled(False)
        self._tabs_box.hide()
        self._remove_tab_button.setEnabled(False)

    def _populate_splitter(self, entity: EntityModel) -> None:
        orientation = str(entity.properties.get("orientation", "horizontal"))
        with QSignalBlocker(self._splitter_orientation_edit):
            index = self._splitter_orientation_edit.findText(orientation)
            self._splitter_orientation_edit.setCurrentIndex(max(0, index))
        sizes = entity.properties.get("sizes", [1, 1])
        normalized_sizes = [1, 1]
        if isinstance(sizes, list) and len(sizes) >= 2:
            normalized_sizes = [max(1, int(sizes[0])), max(1, int(sizes[1]))]
        with QSignalBlocker(self._splitter_primary_size_spin):
            self._splitter_primary_size_spin.setValue(normalized_sizes[0])
        with QSignalBlocker(self._splitter_secondary_size_spin):
            self._splitter_secondary_size_spin.setValue(normalized_sizes[1])

    def _clear_splitter_ui(self) -> None:
        self._set_blocked_combo_text(self._splitter_orientation_edit, "horizontal")
        self._set_blocked_spin_value(self._splitter_primary_size_spin, 1)
        self._set_blocked_spin_value(self._splitter_secondary_size_spin, 1)
        self._splitter_box.hide()

    def _populate_wizard(self, document: FormDocument, entity: EntityModel) -> None:
        pages = document.get_wizard_pages(entity.id)
        current_index = int(entity.properties.get("current_index", 0))
        selected_row = self._resolve_selected_row(
            [page.id for page in pages],
            self._selected_wizard_page_id,
            current_index,
        )
        with QSignalBlocker(self._wizard_pages_list):
            self._wizard_pages_list.clear()
            for index, page in enumerate(pages):
                title = str(page.properties.get("title", f"Page {index + 1}"))
                self._wizard_pages_list.addItem(title)
            if pages:
                self._wizard_pages_list.setCurrentRow(selected_row)
        self._update_wizard_page_editors()
        self._add_wizard_page_button.setEnabled(True)
        self._remove_wizard_page_button.setEnabled(len(pages) > 1)

    def _clear_wizard_ui(self) -> None:
        self._clear_blocked_list(self._wizard_pages_list)
        self._set_blocked_text(self._wizard_page_title_edit, "")
        self._set_blocked_plain_text(self._wizard_page_subtitle_edit, "")
        self._selected_wizard_page_id = None
        self._wizard_page_title_edit.setEnabled(False)
        self._wizard_page_subtitle_edit.setEnabled(False)
        self._add_wizard_page_button.setEnabled(False)
        self._remove_wizard_page_button.setEnabled(False)
        self._wizard_box.hide()

    def _emit_name_change(self) -> None:
        if self._active_entity_id:
            self.name_changed.emit(self._active_entity_id, self._entity_name_edit.text())

    def _apply_special_sections(
        self,
        document: FormDocument,
        entity: EntityModel,
    ) -> None:
        self._refresh_special_section(
            document=document,
            entity=entity,
            action_name="add_tab_page",
            populate=self._populate_tabs,
            clear=self._clear_tabs_ui,
            box=self._tabs_box,
        )
        self._refresh_special_section(
            document=document,
            entity=entity,
            action_name="set_splitter_orientation",
            populate=lambda _document, current_entity: self._populate_splitter(current_entity),
            clear=self._clear_splitter_ui,
            box=self._splitter_box,
        )
        self._refresh_special_section(
            document=document,
            entity=entity,
            action_name="add_wizard_page",
            populate=self._populate_wizard,
            clear=self._clear_wizard_ui,
            box=self._wizard_box,
        )

    def _refresh_special_section(
        self,
        *,
        document: FormDocument,
        entity: EntityModel,
        action_name: str,
        populate,
        clear,
        box: QGroupBox,
    ) -> None:
        supports_action = document.widget_registry.supports_special_action(entity.type, action_name)
        if supports_action:
            populate(document, entity)
            box.show()
            return
        clear()
        box.hide()

    def _apply_schema_to_basic_fields(self, definition: WidgetTypeDefinition) -> None:
        available_properties = {prop.name for prop in self._basic_schema_properties(definition)}
        self._properties_box.setVisible(bool(available_properties))
        for property_name in self._property_widgets:
            self._set_property_row_visible(property_name, property_name in available_properties)

    def _apply_geometry_mode(self, geometry_edit_mode: str) -> None:
        active_entity = None
        if self._active_document is not None and self._active_entity_id is not None:
            active_entity = self._active_document.get_entity(self._active_entity_id)
        geometry_locked = bool(active_entity and active_entity.properties.get("geometry_locked", False))
        editable = geometry_edit_mode == "full" and not geometry_locked
        visible = geometry_edit_mode != "hidden"
        self._geometry_box.setVisible(visible)
        for spin in (self._x_spin, self._y_spin, self._width_spin, self._height_spin):
            spin.setEnabled(editable)

    def _emit_property_change(self, property_name: str, value: object) -> None:
        if self._active_entity_id:
            self.property_changed.emit(self._active_entity_id, property_name, value)

    def _emit_geometry_change(self) -> None:
        if self._active_entity_id:
            self.geometry_changed.emit(
                self._active_entity_id,
                self._x_spin.value(),
                self._y_spin.value(),
                self._width_spin.value(),
                self._height_spin.value(),
            )

    def _emit_form_root_change(self) -> None:
        self.form_root_changed.emit(
            self._form_name_edit.text(),
            self._form_root_widget_type_edit.currentText(),
            self._form_width_spin.value(),
            self._form_height_spin.value(),
            self._form_window_title_edit.text(),
        )

    def _handle_tab_row_changed(self, index: int) -> None:
        current_tab_page = self._current_tab_page()
        self._selected_tab_page_id = None if current_tab_page is None else current_tab_page.id
        self._update_tab_title_editor()
        if self._supports_special_action("set_current_tab") and self._active_entity_id and index >= 0:
            self.current_tab_changed.emit(self._active_entity_id, index)

    def _update_tab_title_editor(self) -> None:
        current_tab_page = self._current_tab_page()
        self._set_blocked_text(
            self._tab_title_edit,
            "" if current_tab_page is None else str(current_tab_page.properties.get("title", "")),
        )
        self._tab_title_edit.setEnabled(current_tab_page is not None)

    def _emit_add_tab(self) -> None:
        if self._supports_special_action("add_tab_page") and self._active_entity_id:
            self._selected_tab_page_id = None
            self.tab_add_requested.emit(self._active_entity_id)

    def _emit_remove_tab(self) -> None:
        if not self._supports_special_action("remove_tab_page") or not self._active_entity_id:
            return
        current_tab_page = self._current_tab_page()
        if current_tab_page is not None:
            self._selected_tab_page_id = None
            self.tab_remove_requested.emit(self._active_entity_id, current_tab_page.id)

    def _emit_tab_rename(self) -> None:
        current_tab_page = self._current_tab_page()
        if current_tab_page is not None:
            self.tab_rename_requested.emit(current_tab_page.id, self._tab_title_edit.text())

    def _emit_splitter_orientation_change(self, value: str) -> None:
        if self._supports_special_action("set_splitter_orientation") and self._active_entity_id:
            self.splitter_orientation_changed.emit(
                self._active_entity_id,
                str(value).strip().lower(),
            )

    def _emit_splitter_sizes_change(self) -> None:
        if self._supports_special_action("set_splitter_sizes") and self._active_entity_id:
            self.splitter_sizes_changed.emit(
                self._active_entity_id,
                [
                    self._splitter_primary_size_spin.value(),
                    self._splitter_secondary_size_spin.value(),
                ],
            )

    def _handle_wizard_row_changed(self, index: int) -> None:
        current_page = self._current_wizard_page()
        self._selected_wizard_page_id = None if current_page is None else current_page.id
        self._update_wizard_page_editors()
        if self._supports_special_action("set_current_wizard_page") and self._active_entity_id and index >= 0:
            self.current_wizard_page_changed.emit(self._active_entity_id, index)

    def _update_wizard_page_editors(self) -> None:
        current_page = self._current_wizard_page()
        self._set_blocked_text(
            self._wizard_page_title_edit,
            "" if current_page is None else str(current_page.properties.get("title", "")),
        )
        self._set_blocked_plain_text(
            self._wizard_page_subtitle_edit,
            "" if current_page is None else str(current_page.properties.get("subtitle", "")),
        )
        enabled = current_page is not None
        self._wizard_page_title_edit.setEnabled(enabled)
        self._wizard_page_subtitle_edit.setEnabled(enabled)

    def _emit_add_wizard_page(self) -> None:
        if self._supports_special_action("add_wizard_page") and self._active_entity_id:
            self._selected_wizard_page_id = None
            self.wizard_add_requested.emit(self._active_entity_id)

    def _emit_remove_wizard_page(self) -> None:
        if not self._supports_special_action("remove_wizard_page") or not self._active_entity_id:
            return
        current_page = self._current_wizard_page()
        if current_page is not None:
            self._selected_wizard_page_id = None
            self.wizard_remove_requested.emit(self._active_entity_id, current_page.id)

    def _emit_wizard_page_rename(self) -> None:
        current_page = self._current_wizard_page()
        if current_page is not None:
            self.wizard_rename_requested.emit(
                current_page.id,
                self._wizard_page_title_edit.text(),
                self._wizard_page_subtitle_edit.toPlainText(),
            )

    def _current_tab_page(self) -> EntityModel | None:
        if self._active_document is None or not self._supports_special_action("add_tab_page") or not self._active_entity_id:
            return None
        tab_pages = self._active_document.get_tab_pages(self._active_entity_id)
        current_index = self._tabs_list.currentRow()
        if not 0 <= current_index < len(tab_pages):
            return None
        return tab_pages[current_index]

    def _current_wizard_page(self) -> EntityModel | None:
        if self._active_document is None or not self._supports_special_action("add_wizard_page") or not self._active_entity_id:
            return None
        wizard_pages = self._active_document.get_wizard_pages(self._active_entity_id)
        current_index = self._wizard_pages_list.currentRow()
        if not 0 <= current_index < len(wizard_pages):
            return None
        return wizard_pages[current_index]

    def _supports_special_action(self, action_name: str) -> bool:
        if self._active_definition is None or self._active_document is None:
            return False
        return self._active_document.widget_registry.supports_special_action(
            self._active_definition.type_name,
            action_name,
        )

    def _basic_schema_properties(self, definition: WidgetTypeDefinition) -> list[object]:
        special_property_names = set()
        registry = self._active_document.widget_registry if self._active_document is not None else None
        type_name = definition.type_name
        if registry is not None and registry.supports_special_action(type_name, "set_splitter_orientation"):
            special_property_names.update({"orientation", "sizes"})
        schema = (
            registry.get_property_schema(type_name)
            if registry is not None
            else list(definition.property_schema)
        )
        return [
            prop for prop in schema if prop.name not in special_property_names
        ]

    def _apply_schema_to_property_fields(
        self,
        entity: EntityModel,
        definition: WidgetTypeDefinition,
    ) -> None:
        schema_properties = self._basic_schema_properties(definition)
        self._property_schema_map = {prop.name: prop for prop in schema_properties}
        schema_names = set(self._property_schema_map)
        for prop in schema_properties:
            self._ensure_property_widget(prop)
            self._set_property_widget_value(prop.name, entity.properties.get(prop.name, prop.default))
        for property_name in self._property_widgets:
            self._set_property_row_visible(property_name, property_name in schema_names)

    def _apply_contextual_property_constraints(
        self,
        document: FormDocument,
        entity: EntityModel,
    ) -> None:
        current_index_widget = self._property_widgets.get("current_index")
        if isinstance(current_index_widget, QSpinBox):
            current_index_widget.setRange(0, self._max_current_index(document, entity))
        current_row_widget = self._property_widgets.get("current_row")
        if isinstance(current_row_widget, QSpinBox):
            current_row_widget.setRange(-1, self._max_current_row(document, entity))
        row_count_widget = self._property_widgets.get("row_count")
        if isinstance(row_count_widget, QSpinBox):
            row_count_widget.setRange(0, 9999)
        column_count_widget = self._property_widgets.get("column_count")
        if isinstance(column_count_widget, QSpinBox):
            column_count_widget.setRange(0, 9999)

    def _ensure_property_widget(self, prop: PropertyDefinition) -> QWidget:
        existing_widget = self._property_widgets.get(prop.name)
        if existing_widget is not None:
            return existing_widget

        label_text = self._format_property_label(prop.name)
        label_widget = QLabel(label_text)
        widget = self._create_property_widget(prop)
        self._property_widgets[prop.name] = widget
        self._property_row_labels[prop.name] = label_widget
        self._properties_layout.addRow(label_widget, widget)
        return widget

    def _create_property_widget(self, prop: PropertyDefinition) -> QWidget:
        widget = self._editor_factory.create_editor(prop)
        self._editor_factory.connect_change(
            widget,
            prop,
            lambda property_name=prop.name: self._emit_schema_property_change(property_name),
        )
        return widget

    def _set_property_widget_value(self, property_name: str, value: object) -> None:
        widget = self._property_widgets[property_name]
        prop = self._property_schema_map[property_name]
        with QSignalBlocker(widget):
            self._editor_factory.set_value(widget, prop, value)

    def _emit_schema_property_change(self, property_name: str) -> None:
        prop = self._property_schema_map.get(property_name)
        if prop is None:
            return
        widget = self._property_widgets.get(property_name)
        if widget is None:
            return
        try:
            value = self._editor_factory.get_value(widget, prop)
        except Exception as error:
            self.validation_error.emit(
                f"Invalid value for '{self._format_property_label(property_name)}': {error}"
            )
            self._set_property_widget_value(property_name, self._active_entity_property_value(property_name, prop))
            return
        if property_name == "current_index":
            self._reset_special_selection_tracking()
            if (
                self._supports_special_action("set_current_tab")
                and self._active_entity_id is not None
            ):
                self.current_tab_changed.emit(self._active_entity_id, int(value))
                return
            if (
                self._supports_special_action("set_current_wizard_page")
                and self._active_entity_id is not None
            ):
                self.current_wizard_page_changed.emit(self._active_entity_id, int(value))
                return
        self._emit_property_change(property_name, value)
        if property_name == "geometry_locked":
            self._apply_geometry_mode(
                "full"
                if self._active_definition is None
                else self._geometry_edit_mode_for(self._active_definition.type_name)
            )

    def _active_entity_property_value(self, property_name: str, prop: PropertyDefinition) -> object:
        if self._active_document is None or self._active_entity_id is None:
            return prop.default
        entity = self._active_document.get_entity(self._active_entity_id)
        if entity is None:
            return prop.default
        return entity.properties.get(property_name, prop.default)

    def _format_property_label(self, property_name: str) -> str:
        return property_name.replace("_", " ").title()

    def _geometry_edit_mode_for(self, type_name: str) -> str:
        if self._active_document is None:
            return "full"
        return self._active_document.widget_registry.get_geometry_edit_mode(type_name)

    def _set_property_row_visible(self, property_name: str, visible: bool) -> None:
        widget = self._property_widgets.get(property_name)
        label = self._property_row_labels.get(property_name)
        if widget is not None:
            widget.setVisible(visible)
        if label is not None:
            label.setVisible(visible)

    def _reset_special_selection_tracking(self) -> None:
        self._selected_tab_page_id = None
        self._selected_wizard_page_id = None

    def _resolve_selected_row(
        self,
        item_ids: list[str],
        selected_item_id: str | None,
        fallback_index: int,
    ) -> int:
        if not item_ids:
            return -1
        if selected_item_id in item_ids:
            return item_ids.index(selected_item_id)
        return max(0, min(fallback_index, len(item_ids) - 1))

    def _display_entity_for(self, document: FormDocument, entity: EntityModel) -> EntityModel:
        current_entity = entity
        while document.widget_registry.get_editor_kind(current_entity.type) == "internal":
            parent_entity = document.get_entity(current_entity.parent_id)
            if parent_entity is None:
                break
            current_entity = parent_entity
        return current_entity

    def _max_current_index(self, document: FormDocument, entity: EntityModel) -> int:
        if entity.type == "QTabWidget":
            return max(0, len(document.get_tab_pages(entity.id)) - 1)
        if entity.type == "QWizard":
            return max(0, len(document.get_wizard_pages(entity.id)) - 1)
        if entity.type == "QComboBox":
            items = entity.properties.get("items", [])
            if isinstance(items, list):
                return max(0, len(items) - 1)
        return 9999

    def _max_current_row(self, document: FormDocument, entity: EntityModel) -> int:
        if entity.type == "QListWidget":
            items = entity.properties.get("items", [])
            if isinstance(items, list):
                return max(-1, len(items) - 1)
        return 9999
