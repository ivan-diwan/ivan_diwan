from __future__ import annotations

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QGuiApplication, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from form_constructor.controller.document_controller import DocumentController
from form_constructor.document.form_document import FormDocument
from form_constructor.ui.form_window.form_window import FormWindow
from form_constructor.ui.palette.palette_panel import PalettePanel
from form_constructor.ui.properties.property_panel import PropertyPanel


class MainEditorWindow(QMainWindow):
    def __init__(self, controller: DocumentController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._controller = controller
        self._form_window: FormWindow | None = None
        self._property_panel = PropertyPanel()
        self._palette_panel = PalettePanel(widget_registry=self._controller.widget_registry)
        self._delete_button = QPushButton("Delete Object")
        self._save_button = QPushButton("Save")
        self._export_python_button = QPushButton("Export Py")
        self._load_button = QPushButton("Load")
        self._message_log = QPlainTextEdit()
        self._delete_shortcut = QShortcut(QKeySequence("Del"), self)
        self._delete_shortcut.activated.connect(self._controller.delete_selected_entity)

        self.setWindowTitle("Form Constructor")
        self.resize(420, 900)
        self._build_ui()
        self._bind_events()
        self._property_panel.clear()

    def _build_ui(self) -> None:
        create_button = QPushButton("Create")
        create_button.clicked.connect(self._create_document)
        self._create_button = create_button

        self._load_button.setEnabled(False)
        self._save_button.setEnabled(False)
        self._export_python_button.setEnabled(False)
        self._delete_button.setEnabled(False)
        self._message_log.setReadOnly(True)
        self._message_log.setFixedHeight(120)
        self._message_log.setPlaceholderText("Status and errors will appear here.")

        toolbar_layout = QHBoxLayout()
        toolbar_layout.addWidget(self._create_button)
        toolbar_layout.addWidget(self._load_button)
        toolbar_layout.addWidget(self._save_button)
        toolbar_layout.addWidget(self._export_python_button)

        splitter = QSplitter()
        splitter.setOrientation(Qt.Orientation.Vertical)
        splitter.addWidget(self._palette_panel)
        splitter.addWidget(self._property_panel)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([320, 220])
        self._main_splitter = splitter

        layout = QVBoxLayout()
        layout.addLayout(toolbar_layout)
        layout.addWidget(self._main_splitter, 1)
        message_box = QGroupBox("Messages")
        message_layout = QVBoxLayout(message_box)
        message_layout.addWidget(self._message_log)
        layout.addWidget(message_box)
        layout.addWidget(self._delete_button)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def _bind_events(self) -> None:
        self._controller.document_created.connect(self._open_form_window)
        self._controller.document_changed.connect(self._sync_form_window)
        self._controller.document_closed.connect(self._handle_document_closed)
        self._controller.document_created.connect(lambda _: self._update_toolbar_state())
        self._controller.document_changed.connect(lambda _: self._update_toolbar_state())
        self._controller.snapshot_changed.connect(lambda _: self._update_toolbar_state())
        self._controller.selection_changed.connect(self._handle_selection_changed)
        self._controller.entity_added.connect(self._handle_entity_added)
        self._controller.entity_updated.connect(self._handle_entity_updated)
        self._controller.entity_removed.connect(self._handle_entity_removed)
        self._controller.status_message.connect(self._show_status_message)
        self._controller.error_message.connect(self._show_error_message)
        self._delete_button.clicked.connect(self._controller.delete_selected_entity)
        self._save_button.clicked.connect(self._save_document)
        self._export_python_button.clicked.connect(self._export_python)
        self._load_button.clicked.connect(self._load_document)
        self._property_panel.name_changed.connect(self._controller.rename_entity)
        self._property_panel.validation_error.connect(self._show_error_message)
        self._property_panel.property_changed.connect(self._controller.update_entity_property)
        self._property_panel.geometry_changed.connect(self._controller.update_entity_geometry)
        self._property_panel.form_root_changed.connect(self._handle_form_root_changed)
        self._property_panel.tab_add_requested.connect(self._controller.add_tab_page)
        self._property_panel.tab_remove_requested.connect(self._controller.remove_tab_page)
        self._property_panel.tab_rename_requested.connect(self._controller.rename_tab_page)
        self._property_panel.current_tab_changed.connect(self._controller.set_current_tab)
        self._property_panel.splitter_orientation_changed.connect(self._controller.set_splitter_orientation)
        self._property_panel.splitter_sizes_changed.connect(self._controller.set_splitter_sizes)
        self._property_panel.wizard_add_requested.connect(self._controller.add_wizard_page)
        self._property_panel.wizard_remove_requested.connect(self._controller.remove_wizard_page)
        self._property_panel.wizard_rename_requested.connect(self._controller.rename_wizard_page)
        self._property_panel.current_wizard_page_changed.connect(self._controller.set_current_wizard_page)
        self._update_toolbar_state()

    def apply_screen_layout(self) -> None:
        screen_geometry = self._current_screen_geometry()
        editor_outer_width = self._editor_width_for(screen_geometry)
        self._set_outer_geometry(
            QRect(
                screen_geometry.x(),
                screen_geometry.y(),
                editor_outer_width,
                screen_geometry.height(),
            )
        )

    def _create_document(self) -> None:
        screen_geometry = self._current_screen_geometry()
        editor_outer_width = self._editor_width_for(screen_geometry)
        form_outer_width = max(480, screen_geometry.width() - editor_outer_width)
        frame_width_extra, frame_height_extra = self._frame_extra()
        try:
            self._controller.new_document(
                width=max(320, form_outer_width - frame_width_extra),
                height=max(240, screen_geometry.height() - frame_height_extra),
            )
        except Exception as error:
            self._show_error_message(self._format_exception_message(error))

    def _save_document(self) -> None:
        if self._controller.active_document is None:
            return
        if not self._validate_active_document_for_action("save JSON"):
            return
        current_path = self._controller.editor_state.current_json_path or ""
        target_path = current_path
        if not target_path:
            target_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Form JSON",
                "",
                "JSON Files (*.json);;All Files (*)",
            )
        if not target_path:
            return
        try:
            self._controller.save_document_to_json(target_path)
        except Exception as error:
            self._show_error_message(self._format_exception_message(error))
        self._update_toolbar_state()

    def _load_document(self) -> None:
        source_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Form",
            "",
            "Form Files (*.json *.py);;JSON Files (*.json);;Python Files (*.py);;All Files (*)",
        )
        if not source_path:
            return
        try:
            self._controller.load_document(source_path)
        except Exception as error:
            self._show_error_message(self._format_exception_message(error))
        self._update_toolbar_state()

    def _export_python(self) -> None:
        if self._controller.active_document is None:
            return
        if not self._validate_active_document_for_action("export Python"):
            return
        current_path = self._controller.suggest_python_export_path()
        target_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Python",
            current_path,
            "Python Files (*.py);;All Files (*)",
        )
        if not target_path:
            return
        try:
            self._controller.export_document_to_python(target_path)
        except Exception as error:
            self._show_error_message(self._format_exception_message(error))

    def _open_form_window(self, document: FormDocument) -> None:
        if self._form_window is not None:
            self._form_window.close()
        self._form_window = FormWindow(document=document, controller=self._controller)
        self._form_window.show()
        QApplication.processEvents()
        self._form_window.apply_screen_layout(self._current_screen_geometry())
        self._rebuild_property_panel()

    def _handle_selection_changed(self, entity) -> None:
        document = self._controller.active_document
        if document is None:
            self._delete_button.setEnabled(False)
            self._property_panel.clear()
            return
        if self._form_window is not None:
            self._form_window.select_entity(entity.id if entity else None)
        self._delete_button.setEnabled(entity is not None)
        self._rebuild_property_panel()

    def _handle_entity_added(self, entity) -> None:
        if self._form_window is not None:
            self._form_window.rebuild_canvas()

    def _handle_entity_updated(self, entity) -> None:
        if self._form_window is not None and entity is not None:
            self._form_window.handle_entity_update(entity)

    def _handle_entity_removed(self, entity_id: str) -> None:
        if self._form_window is not None:
            self._form_window.rebuild_canvas()

    def _sync_form_window(self, document: FormDocument) -> None:
        if self._form_window is not None:
            self._form_window.set_document(document)

    def _handle_document_closed(self) -> None:
        if self._form_window is not None:
            self._form_window.close()
            self._form_window = None
        self._property_panel.clear()
        self._delete_button.setEnabled(False)
        self._update_toolbar_state()

    def _handle_form_root_changed(
        self,
        name: str,
        root_widget_type: str,
        width: int,
        height: int,
        window_title: str,
    ) -> None:
        self._controller.update_form_root(
            name=name,
            root_widget_type=root_widget_type,
            width=width,
            height=height,
            window_title=window_title,
        )

    def _update_toolbar_state(self) -> None:
        has_document = self._controller.active_document is not None
        self._load_button.setEnabled(True)
        self._save_button.setEnabled(has_document)
        self._export_python_button.setEnabled(has_document)

    def _rebuild_property_panel(self) -> None:
        self._property_panel.rebuild(
            self._controller.active_document,
            self._controller.selected_entity,
        )

    def _show_status_message(self, message: str) -> None:
        self.statusBar().showMessage(message, 5000)
        self._append_message_log("INFO", message)

    def _show_error_message(self, message: str) -> None:
        self.statusBar().showMessage(message, 8000)
        self._append_message_log("ERROR", message)

    def _append_message_log(self, level: str, message: str) -> None:
        prefix = f"[{level}] "
        existing = self._message_log.toPlainText()
        next_line = f"{prefix}{message}".strip()
        if existing:
            self._message_log.setPlainText(f"{existing}\n{next_line}")
        else:
            self._message_log.setPlainText(next_line)

    def _format_exception_message(self, error: Exception) -> str:
        diagnostic = getattr(error, "diagnostic", None)
        if diagnostic is None:
            return str(error)

        return self._format_diagnostic_message(diagnostic, fallback_message=str(error))

    def _format_diagnostic_message(self, diagnostic, *, fallback_message: str) -> str:
        details = getattr(diagnostic, "details", {})
        if not isinstance(details, dict):
            details = {}

        message = str(getattr(diagnostic, "message", "")).strip() or fallback_message
        parts = [message]

        filename = details.get("filename")
        if filename:
            parts.append(f"filename: {filename}")

        line = getattr(diagnostic, "line", None)
        if line is not None:
            parts.append(f"line {line}")

        pattern = getattr(diagnostic, "pattern", None)
        if pattern:
            parts.append(f"pattern: {pattern}")

        entity_ref = getattr(diagnostic, "entity_ref", None)
        if entity_ref:
            parts.append(f"entity_ref: {entity_ref}")

        entity_id = getattr(diagnostic, "entity_id", None)
        if entity_id:
            parts.append(f"entity_id: {entity_id}")

        entity_type = getattr(diagnostic, "entity_type", None)
        if entity_type:
            parts.append(f"entity_type: {entity_type}")

        if bool(getattr(diagnostic, "unsupported", False)):
            parts.append("unsupported case")

        stage = getattr(diagnostic, "stage", None)
        if stage:
            parts.append(f"stage: {stage}")

        return " | ".join(str(part) for part in parts if str(part).strip())

    def _validate_active_document_for_action(self, action_label: str) -> bool:
        try:
            self._controller.validate_active_document()
            return True
        except Exception as error:
            self._show_error_message(f"Cannot {action_label}: {self._format_exception_message(error)}")
            return False

    def _current_screen_geometry(self) -> QRect:
        screen = self.screen()
        if screen is None:
            screen = self.windowHandle().screen() if self.windowHandle() is not None else None
        if screen is None:
            screen = QGuiApplication.primaryScreen()
        if screen is not None:
            return screen.availableGeometry()
        return self.geometry()

    def _editor_width_for(self, screen_geometry: QRect) -> int:
        return max(360, screen_geometry.width() // 4)

    def _set_outer_geometry(self, target_geometry: QRect) -> None:
        left, top, right, bottom = self._frame_margins()
        self.setGeometry(
            target_geometry.x() + left,
            target_geometry.y() + top,
            max(200, target_geometry.width() - left - right),
            max(200, target_geometry.height() - top - bottom),
        )

    def _frame_extra(self) -> tuple[int, int]:
        frame = self.frameGeometry()
        client = self.geometry()
        return (
            max(0, frame.width() - client.width()),
            max(0, frame.height() - client.height()),
        )

    def _frame_margins(self) -> tuple[int, int, int, int]:
        frame = self.frameGeometry()
        client = self.geometry()
        left = max(0, client.x() - frame.x())
        top = max(0, client.y() - frame.y())
        right = max(0, frame.right() - client.right())
        bottom = max(0, frame.bottom() - client.bottom())
        return left, top, right, bottom
