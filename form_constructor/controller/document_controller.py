from __future__ import annotations

from pathlib import Path
import re

from PySide6.QtCore import QObject, Signal

from form_constructor.controller.editor_state import EditorState
from form_constructor.conversion.exporter import PythonExporter
from form_constructor.conversion.importer import PythonImporter
from form_constructor.document.form_document import FormDocument
from form_constructor.document.models import FormRootModel
from form_constructor.document.validator import DocumentValidator
from form_constructor.registry.widget_registry import WidgetRegistry
from form_constructor.serialization.form_serializer import FormSerializer


class DocumentController(QObject):
    document_created = Signal(object)
    document_changed = Signal(object)
    document_closed = Signal()
    snapshot_changed = Signal(str)
    selection_changed = Signal(object)
    entity_added = Signal(object)
    entity_updated = Signal(object)
    entity_removed = Signal(str)
    status_message = Signal(str)
    error_message = Signal(str)

    def __init__(self, widget_registry: WidgetRegistry) -> None:
        super().__init__()
        self._widget_registry = widget_registry
        self._validator = DocumentValidator()
        self._serializer = FormSerializer(widget_registry=widget_registry, validator=self._validator)
        self._python_exporter = PythonExporter()
        self._python_importer = PythonImporter(widget_registry=widget_registry, validator=self._validator)
        self._editor_state = EditorState()
        self._active_document: FormDocument | None = None

    @property
    def active_document(self) -> FormDocument | None:
        return self._active_document

    @property
    def widget_registry(self) -> WidgetRegistry:
        return self._widget_registry

    @property
    def editor_state(self) -> EditorState:
        return self._editor_state

    @property
    def selected_entity(self):
        if self._active_document is None or self._editor_state.selected_entity_id is None:
            return None
        return self._active_document.get_entity(self._editor_state.selected_entity_id)

    def create_new_document(self, width: int = 1200, height: int = 800) -> FormDocument:
        form_root = FormRootModel(
            id="form_root",
            type="FormRoot",
            name="form_root",
            root_widget_type="QWidget",
            width=width,
            height=height,
            window_title="Untitled Form",
        )
        document = FormDocument(form_root=form_root, widget_registry=self._widget_registry)
        self._activate_document(document, current_json_path=None)
        self.notify_status("Form created.")
        return document

    def new_document(self, width: int = 1200, height: int = 800) -> FormDocument:
        return self.create_new_document(width=width, height=height)

    def load_document_from_json(self, payload: str) -> FormDocument:
        document = self._serializer.deserialize_from_json(payload)
        self._activate_document(document, current_json_path=None)
        self.notify_status("Form loaded from JSON.")
        return document

    def load_document_from_json_path(self, path: str) -> FormDocument:
        document = self._serializer.load_json(path)
        self._activate_document(document, current_json_path=path)
        self.notify_status("Form loaded.")
        return document

    def load_document_from_python(self, path: str) -> FormDocument:
        document = self._python_importer.import_from_file(path)
        self._activate_document(document, current_json_path=None)
        self._editor_state.current_python_path = path
        self.notify_status("Python imported.")
        return document

    def load_document(self, path: str) -> FormDocument:
        lowered = str(path).lower()
        if lowered.endswith(".json"):
            return self.load_document_from_json_path(path)
        if lowered.endswith(".py"):
            return self.load_document_from_python(path)
        raise ValueError(f"Unsupported document format for '{path}'.")

    def save_document_to_json(self, path: str | None = None) -> str:
        document = self._require_document()
        target_path = path or self._editor_state.current_json_path
        if not target_path:
            raise ValueError("No target JSON path provided.")
        self._serializer.save_json(document, target_path)
        self._editor_state.current_json_path = target_path
        document.clear_dirty()
        self.flush_json_snapshot()
        self.notify_status("JSON saved.")
        return target_path

    def export_document_to_python(self, path: str) -> str:
        document = self._require_document()
        self._validator.validate_document(document)
        self.flush_json_snapshot()
        target_path = self._normalize_python_export_path(path)
        self._python_exporter.export_to_file(document, target_path)
        self._editor_state.current_python_path = target_path
        self.notify_status("Python exported.")
        return target_path

    def export_document_to_python_source(self) -> str:
        document = self._require_document()
        self._validator.validate_document(document)
        self.flush_json_snapshot()
        self._python_exporter.validate_export(document)
        return self._python_exporter.export(document)

    def save_python(self, path: str) -> str:
        return self.export_document_to_python(path)

    def suggest_python_export_path(self) -> str:
        if self._editor_state.current_python_path:
            return self._editor_state.current_python_path
        if self._editor_state.current_json_path:
            return str(Path(self._editor_state.current_json_path).with_suffix(".py"))
        if self._active_document is None:
            return ""
        base_name = self._python_export_base_name(self._active_document.form_root.name)
        return f"{base_name}.py"

    @staticmethod
    def _python_export_base_name(value: str) -> str:
        normalized = re.sub(r"\W+", "_", str(value).strip().lower()).strip("_")
        return normalized or "generated_form"

    @staticmethod
    def _normalize_python_export_path(path: str) -> str:
        normalized_path = Path(path)
        if normalized_path.suffix:
            return str(normalized_path)
        return str(normalized_path.with_suffix(".py"))

    def close_document(self) -> None:
        self._active_document = None
        self._editor_state.active_document_id = None
        self._editor_state.selected_entity_id = None
        self._editor_state.current_json_path = None
        self._editor_state.current_python_path = None
        self.document_closed.emit()
        self.selection_changed.emit(None)
        self.snapshot_changed.emit("")

    def update_form_root(
        self,
        *,
        name: str | None = None,
        root_widget_type: str | None = None,
        width: int | None = None,
        height: int | None = None,
        window_title: str | None = None,
    ) -> None:
        document = self._require_document()
        form_root = document.get_form_root()
        if name is not None:
            form_root.name = str(name)
        if root_widget_type is not None:
            form_root.root_widget_type = str(root_widget_type)
        if width is not None:
            form_root.width = max(240, int(width))
        if height is not None:
            form_root.height = max(180, int(height))
        if window_title is not None:
            form_root.window_title = str(window_title)
        document.mark_dirty()
        self._commit_document_change(document, clear_selection=True)

    def get_snapshot(self) -> str:
        if self._active_document is None:
            return ""
        return self._serializer.serialize_to_json(self._active_document)

    def select_entity(self, entity_id: str | None) -> None:
        self._editor_state.selected_entity_id = entity_id
        entity = None
        if entity_id and self._active_document is not None:
            entity = self._active_document.get_entity(entity_id)
        self.selection_changed.emit(entity)

    def clear_selection(self) -> None:
        self.select_entity(None)

    def notify_status(self, message: str) -> None:
        self.status_message.emit(str(message))

    def notify_error(self, message: str) -> None:
        self.error_message.emit(str(message))

    def create_entity_from_drop(self, type_name: str, x: int, y: int, parent_id: str) -> object:
        document = self._require_document()
        definition = self._widget_registry.get_type(type_name)
        if definition is None:
            raise ValueError(f"Unknown widget type: {type_name}")
        if not definition.creatable_by_user:
            raise ValueError(f"Type '{type_name}' cannot be created by user drop.")
        width, height = self._widget_registry.get_default_size(type_name)
        geometry = {"x": x, "y": y, "width": width, "height": height}
        entity = self._create_entity_via_document(
            document=document,
            type_name=type_name,
            parent_id=parent_id,
            geometry=geometry,
        )
        self._commit_document_change(
            document,
            added_entity=entity,
            selected_entity_id=entity.id,
        )
        return entity

    def reparent_entity(
        self,
        entity_id: str,
        new_parent_id: str,
        x: int | None = None,
        y: int | None = None,
    ) -> None:
        document = self._require_document()
        document.reparent_entity(entity_id, new_parent_id, x=x, y=y)
        entity = document.get_entity(entity_id)
        self._commit_document_change(
            document,
            updated_entity=entity,
            selected_entity_id=entity_id,
        )

    def set_entity_order(self, entity_id: str, new_order: int) -> None:
        document = self._require_document()
        document.set_order(entity_id, new_order)
        entity = document.get_entity(entity_id)
        self._commit_document_change(
            document,
            updated_entity=entity,
            selected_entity_id=entity_id,
        )

    def validate_active_document(self) -> None:
        document = self._require_document()
        self._validator.validate_document(document)

    def rename_entity(self, entity_id: str, new_name: str) -> None:
        document = self._require_document()
        document.rename_entity(entity_id, new_name)
        entity = document.get_entity(entity_id)
        self._commit_document_change(
            document,
            updated_entity=entity,
            selected_entity_id=entity_id,
        )

    def update_entity_property(self, entity_id: str, property_name: str, value: object) -> None:
        document = self._require_document()
        document.update_property(entity_id, property_name, value)
        entity = document.get_entity(entity_id)
        self._commit_document_change(
            document,
            updated_entity=entity,
            selected_entity_id=entity_id,
        )

    def move_entity(self, entity_id: str, x: int, y: int) -> None:
        document = self._require_document()
        document.move_entity(entity_id, x, y)
        entity = document.get_entity(entity_id)
        self._commit_document_change(
            document,
            updated_entity=entity,
            selected_entity_id=entity_id,
        )

    def resize_entity(self, entity_id: str, width: int, height: int) -> None:
        document = self._require_document()
        document.resize_entity(entity_id, width, height)
        entity = document.get_entity(entity_id)
        self._commit_document_change(
            document,
            updated_entity=entity,
            selected_entity_id=entity_id,
        )

    def update_entity_geometry(
        self,
        entity_id: str,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> None:
        document = self._require_document()
        document.update_geometry(entity_id, x, y, width, height)
        entity = document.get_entity(entity_id)
        self._commit_document_change(
            document,
            updated_entity=entity,
            selected_entity_id=entity_id,
        )

    def delete_entity(self, entity_id: str) -> None:
        document = self._require_document()
        if not document.has_entity(entity_id):
            return
        removed_entity_ids = {entity_id, *(entity.id for entity in document.get_descendants(entity_id))}
        document.delete_entity(entity_id)
        should_clear_selection = self._editor_state.selected_entity_id in removed_entity_ids
        self._commit_document_change(
            document,
            removed_entity_id=entity_id,
            clear_selection=should_clear_selection,
        )

    def delete_selected_entity(self) -> None:
        entity_id = self._editor_state.selected_entity_id
        if not entity_id:
            return
        self.delete_entity(entity_id)

    def add_tab_page(self, tab_widget_id: str) -> None:
        document = self._require_document()
        document.add_tab_page(tab_widget_id)
        tab_widget = document.get_entity(tab_widget_id)
        self._commit_document_change(
            document,
            updated_entity=tab_widget,
            selected_entity_id=tab_widget_id,
        )

    def get_scroll_content(self, scroll_area_id: str) -> object:
        document = self._require_document()
        return document.get_scroll_content(scroll_area_id)

    def remove_tab_page(self, tab_widget_id: str, tab_page_id: str) -> None:
        document = self._require_document()
        document.remove_tab_page(tab_widget_id, tab_page_id)
        tab_widget = document.get_entity(tab_widget_id)
        self._commit_document_change(
            document,
            updated_entity=tab_widget,
            selected_entity_id=tab_widget_id,
        )

    def rename_tab_page(self, tab_page_id: str, new_title: str) -> None:
        document = self._require_document()
        document.rename_tab_page(tab_page_id, new_title)
        tab_page = document.get_entity(tab_page_id)
        if tab_page is None:
            return
        tab_widget_id = tab_page.parent_id
        tab_widget = document.get_entity(tab_widget_id)
        self._commit_document_change(
            document,
            updated_entity=tab_widget if tab_widget is not None else tab_page,
            selected_entity_id=tab_widget_id if tab_widget is not None else tab_page_id,
        )

    def set_current_tab(self, tab_widget_id: str, index: int) -> None:
        document = self._require_document()
        document.set_current_tab(tab_widget_id, index)
        tab_widget = document.get_entity(tab_widget_id)
        self._commit_document_change(
            document,
            updated_entity=tab_widget,
            selected_entity_id=tab_widget_id,
        )

    def set_splitter_orientation(self, splitter_id: str, orientation: str) -> None:
        document = self._require_document()
        document.set_splitter_orientation(splitter_id, orientation)
        splitter = document.get_entity(splitter_id)
        self._commit_document_change(
            document,
            updated_entity=splitter,
            selected_entity_id=splitter_id,
        )

    def set_splitter_sizes(self, splitter_id: str, sizes: list[int]) -> None:
        document = self._require_document()
        document.set_splitter_sizes(splitter_id, sizes)
        splitter = document.get_entity(splitter_id)
        self._commit_document_change(
            document,
            updated_entity=splitter,
            selected_entity_id=splitter_id,
        )

    def add_wizard_page(self, wizard_id: str) -> None:
        document = self._require_document()
        document.add_wizard_page(wizard_id)
        wizard = document.get_entity(wizard_id)
        self._commit_document_change(
            document,
            updated_entity=wizard,
            selected_entity_id=wizard_id,
        )

    def remove_wizard_page(self, wizard_id: str, wizard_page_id: str) -> None:
        document = self._require_document()
        document.remove_wizard_page(wizard_id, wizard_page_id)
        wizard = document.get_entity(wizard_id)
        self._commit_document_change(
            document,
            updated_entity=wizard,
            selected_entity_id=wizard_id,
        )

    def rename_wizard_page(
        self,
        wizard_page_id: str,
        new_title: str,
        new_subtitle: str | None = None,
    ) -> None:
        document = self._require_document()
        document.rename_wizard_page(wizard_page_id, new_title, new_subtitle)
        page = document.get_entity(wizard_page_id)
        if page is None:
            return
        wizard_id = page.parent_id
        wizard = document.get_entity(wizard_id)
        self._commit_document_change(
            document,
            updated_entity=wizard if wizard is not None else page,
            selected_entity_id=wizard_id if wizard is not None else wizard_page_id,
        )

    def set_current_wizard_page(self, wizard_id: str, index: int) -> None:
        document = self._require_document()
        document.set_current_wizard_page(wizard_id, index)
        wizard = document.get_entity(wizard_id)
        self._commit_document_change(
            document,
            updated_entity=wizard,
            selected_entity_id=wizard_id,
        )

    def flush_json_snapshot(self) -> None:
        if self._active_document is not None:
            self.snapshot_changed.emit(self._serializer.serialize_to_json(self._active_document))

    def _create_entity_via_document(
        self,
        *,
        document: FormDocument,
        type_name: str,
        parent_id: str,
        geometry: dict,
    ):
        special_creators = {
            "QTabWidget": document.create_tab_widget,
            "QScrollArea": document.create_scroll_area,
            "QSplitter": document.create_splitter,
            "QWizard": document.create_wizard,
        }
        creator = special_creators.get(type_name)
        if creator is not None:
            return creator(parent_id=parent_id, geometry=geometry)
        return document.create_entity(
            type_name=type_name,
            parent_id=parent_id,
            geometry=geometry,
        )

    def _activate_document(self, document: FormDocument, current_json_path: str | None) -> None:
        self._validator.validate_document(document)
        self._active_document = document
        self._editor_state.active_document_id = document.form_root.id
        self._editor_state.selected_entity_id = None
        self._editor_state.current_json_path = current_json_path
        self._editor_state.current_python_path = None
        self.document_created.emit(document)
        self.document_changed.emit(document)
        self.selection_changed.emit(None)
        self.flush_json_snapshot()

    def _commit_document_change(
        self,
        document: FormDocument,
        *,
        added_entity: object | None = None,
        updated_entity: object | None = None,
        removed_entity_id: str | None = None,
        selected_entity_id: str | None = None,
        clear_selection: bool = False,
    ) -> None:
        self._validator.validate_document(document)
        self.document_changed.emit(document)
        if added_entity is not None:
            self.entity_added.emit(added_entity)
        if updated_entity is not None:
            self.entity_updated.emit(updated_entity)
        if removed_entity_id is not None:
            self.entity_removed.emit(removed_entity_id)
        self.flush_json_snapshot()
        if clear_selection:
            self.clear_selection()
            return
        if selected_entity_id is not None:
            self.select_entity(selected_entity_id)

    def _require_document(self) -> FormDocument:
        if self._active_document is None:
            raise RuntimeError("No active document.")
        return self._active_document
