from __future__ import annotations

import keyword
import re
from pathlib import Path

from form_constructor.conversion.export_validation import (
    ExportDiagnostic,
    ExportDiagnosticError,
    ExportValidator,
)
from form_constructor.document.form_document import FormDocument
from form_constructor.document.models import EntityModel
from form_constructor.utils.date_utils import parse_date_string
from form_constructor.utils.datetime_utils import parse_datetime_string
from form_constructor.utils.time_utils import parse_time_string


class PythonExporter:
    def __init__(self) -> None:
        self._document: FormDocument | None = None
        self._entity_refs: dict[str, str] = {}
        self._internal_refs: dict[str, str] = {}
        self._used_ref_names: set[str] = set()
        self._post_build_lines: list[str] = []
        self._export_validator = ExportValidator()
        self._last_diagnostic: ExportDiagnostic | None = None

    @property
    def last_diagnostic(self) -> ExportDiagnostic | None:
        return self._last_diagnostic

    def export(self, document: FormDocument) -> str:
        self._last_diagnostic = None
        try:
            self._reset(document)

            imports_block = self._build_imports(document)
            class_header = self._build_class_header(document)
            setup_method = self._build_setup_method(document)
            main_guard = self._build_main_guard(document)

            sections = [imports_block, "", class_header, setup_method, "", main_guard]
            return "\n".join(sections).rstrip() + "\n"
        except ExportDiagnosticError as error:
            self._last_diagnostic = error.diagnostic
            raise
        except ValueError as error:
            diagnostic = ExportDiagnostic(stage="export", message=str(error))
            self._last_diagnostic = diagnostic
            raise ExportDiagnosticError(diagnostic) from error

    def validate_export(self, document: FormDocument) -> None:
        try:
            source = self.export(document)
            self._export_validator.validate_python_syntax(source)
        except SyntaxError as error:
            diagnostic = ExportDiagnostic(
                stage="validate_export",
                message=str(error),
            )
            self._last_diagnostic = diagnostic
            raise ExportDiagnosticError(diagnostic) from error
        except ExportDiagnosticError as error:
            self._last_diagnostic = error.diagnostic
            raise

    def export_to_file(self, document: FormDocument, path: str) -> None:
        try:
            source = self.export(document)
            self._export_validator.validate_python_syntax(source, filename=path)
            Path(path).write_text(source, encoding="utf-8")
        except SyntaxError as error:
            diagnostic = ExportDiagnostic(
                stage="export_to_file",
                message=str(error),
                details={"filename": path},
            )
            self._last_diagnostic = diagnostic
            raise ExportDiagnosticError(diagnostic) from error
        except ExportDiagnosticError as error:
            self._last_diagnostic = error.diagnostic
            raise

    def _reset(self, document: FormDocument) -> None:
        self._document = document
        self._entity_refs = {}
        self._internal_refs = {}
        self._used_ref_names = set()
        self._post_build_lines = []

    def _build_imports(self, document: FormDocument) -> str:
        widget_imports = self._collect_required_widget_imports(document)
        lines = ["import sys"]
        lines.append(f"from PySide6.QtWidgets import {', '.join(sorted(widget_imports))}")
        core_imports: list[str] = []
        gui_imports: list[str] = []
        if any(entity.type == "QSplitter" for entity in document.entities_by_id.values()):
            core_imports.append("Qt")
        if any(entity.type in {"QDateEdit", "QCalendarWidget"} for entity in document.entities_by_id.values()):
            core_imports.append("QDate")
        if any(entity.type == "QDateTimeEdit" for entity in document.entities_by_id.values()):
            core_imports.extend(["QDate", "QDateTime", "QTime"])
        if any(entity.type == "QTimeEdit" for entity in document.entities_by_id.values()):
            core_imports.append("QTime")
        if any(entity.type == "QListView" for entity in document.entities_by_id.values()):
            core_imports.append("QStringListModel")
        if any(entity.type in {"QTreeView", "QTableView"} for entity in document.entities_by_id.values()):
            gui_imports.append("QStandardItemModel")
        if any(entity.type == "QFontComboBox" for entity in document.entities_by_id.values()):
            gui_imports.append("QFont")
        if any(entity.type == "QKeySequenceEdit" for entity in document.entities_by_id.values()):
            gui_imports.append("QKeySequence")
        if core_imports:
            lines.append(f"from PySide6.QtCore import {', '.join(sorted(core_imports))}")
        if gui_imports:
            lines.append(f"from PySide6.QtGui import {', '.join(sorted(gui_imports))}")
        return "\n".join(lines)

    def _collect_required_widget_imports(self, document: FormDocument) -> set[str]:
        imports = {"QApplication", document.form_root.root_widget_type}
        for entity in document.entities_by_id.values():
            imports.add(self._qt_class_name(entity.type))
            if entity.type in {"QTabWidget", "QScrollArea", "QSplitter"}:
                imports.add("QWidget")
            if entity.type == "QWizard":
                imports.add("QWizardPage")
            if entity.type == "QTableWidget":
                cell_values = entity.properties.get("cell_values", [])
                if isinstance(cell_values, list) and any(isinstance(row, list) and row for row in cell_values):
                    imports.add("QTableWidgetItem")
            if entity.type == "QTreeWidget":
                tree_items = entity.properties.get("tree_items", [])
                if isinstance(tree_items, list) and tree_items:
                    imports.add("QTreeWidgetItem")
        return imports

    def _build_class_header(self, document: FormDocument) -> str:
        root_widget_type = document.form_root.root_widget_type
        class_name = self._root_class_name(root_widget_type)
        return f"class {class_name}({root_widget_type}):"

    def _build_setup_method(self, document: FormDocument) -> str:
        setup_lines: list[str] = [
            "    def __init__(self):",
            "        super().__init__()",
            "        self.setup_ui()",
            "",
            "    def setup_ui(self):",
            f"        self.setObjectName({self._python_string(self._object_name(document.form_root.name))})",
            f"        self.resize({int(document.form_root.width)}, {int(document.form_root.height)})",
            f'        self.setWindowTitle({self._python_string(document.form_root.window_title)})',
        ]

        creation_lines: list[str] = []
        for entity in self._get_root_entities():
            creation_lines.extend(self._emit_creation_pass(entity))

        property_lines: list[str] = []
        for entity in self._get_root_entities():
            property_lines.extend(self._emit_property_pass(entity))

        if creation_lines:
            setup_lines.append("")
            setup_lines.extend(f"        {line}" for line in creation_lines)

        if property_lines:
            setup_lines.append("")
            setup_lines.extend(f"        {line}" for line in property_lines)

        if self._post_build_lines:
            setup_lines.append("")
            setup_lines.extend(f"        {line}" for line in self._post_build_lines)

        return "\n".join(setup_lines)

    def _emit_creation_pass(self, entity: EntityModel) -> list[str]:
        document = self._require_document()
        definition = document.widget_registry.get_type(entity.type)
        if definition.editor_kind == "internal":
            lines: list[str] = []
            for child in self._get_children(entity.id):
                lines.extend(self._emit_creation_pass(child))
            return lines

        lines = self._emit_entity_creation(entity)
        for child in self._get_children(entity.id):
            lines.extend(self._emit_creation_pass(child))
        return lines

    def _emit_property_pass(self, entity: EntityModel) -> list[str]:
        document = self._require_document()
        definition = document.widget_registry.get_type(entity.type)
        if definition.editor_kind == "internal":
            lines: list[str] = []
            for child in self._get_children(entity.id):
                lines.extend(self._emit_property_pass(child))
            return lines

        lines = self._emit_geometry(entity)
        lines.extend(self._emit_properties(entity))
        for child in self._get_children(entity.id):
            lines.extend(self._emit_property_pass(child))
        return lines

    def _emit_entity_creation(self, entity: EntityModel) -> list[str]:
        handlers = {
            "QTabWidget": self._emit_tab_widget_creation,
            "QScrollArea": self._emit_scroll_area_creation,
            "QSplitter": self._emit_splitter_creation,
            "QWizard": self._emit_wizard_creation,
        }
        handler = handlers.get(entity.type, self._emit_regular_entity_creation)
        return handler(entity)

    def _emit_regular_entity_creation(self, entity: EntityModel) -> list[str]:
        parent_ref = self._get_parent_ref(entity)
        ref_name = self._entity_ref(entity)
        qt_class_name = self._qt_class_name(entity.type)
        return [
            f"self.{ref_name} = {qt_class_name}({parent_ref})",
            f"self.{ref_name}.setObjectName({self._python_string(self._object_name(entity.name))})",
        ]

    def _emit_tab_widget_creation(self, entity: EntityModel) -> list[str]:
        document = self._require_document()
        lines = self._emit_regular_entity_creation(entity)
        for page in self._get_tab_pages(entity.id):
            page_ref = self._internal_ref(page)
            lines.extend(
                [
                    f"self.{page_ref} = QWidget()",
                    f"self.{page_ref}.setObjectName({self._python_string(self._object_name(page.name))})",
                    (
                        f"self.{self._entity_ref(entity)}.addTab("
                        f"self.{page_ref}, {self._python_string(page.properties.get('title', ''))})"
                    ),
                ]
            )
        current_index = int(entity.properties.get("current_index", 0))
        self._post_build_lines.append(
            f"self.{self._entity_ref(entity)}.setCurrentIndex({current_index})"
        )
        return lines

    def _emit_scroll_area_creation(self, entity: EntityModel) -> list[str]:
        document = self._require_document()
        lines = self._emit_regular_entity_creation(entity)
        content = document.get_scroll_content(entity.id)
        if content is not None:
            content_ref = self._internal_ref(content)
            lines.extend(
                [
                    f"self.{content_ref} = QWidget()",
                    f"self.{content_ref}.setObjectName({self._python_string(self._object_name(content.name))})",
                    f"self.{self._entity_ref(entity)}.setWidget(self.{content_ref})",
                ]
            )
        return lines

    def _emit_splitter_creation(self, entity: EntityModel) -> list[str]:
        document = self._require_document()
        lines = self._emit_regular_entity_creation(entity)
        for pane in self._get_splitter_panes(entity.id):
            pane_ref = self._internal_ref(pane)
            lines.extend(
                [
                    f"self.{pane_ref} = QWidget()",
                    f"self.{pane_ref}.setObjectName({self._python_string(self._object_name(pane.name))})",
                    f"self.{self._entity_ref(entity)}.addWidget(self.{pane_ref})",
                ]
            )
        sizes = entity.properties.get("sizes", [1, 1])
        if not isinstance(sizes, list) or len(sizes) < 2:
            sizes = [1, 1]
        normalized_sizes = [max(1, int(sizes[0])), max(1, int(sizes[1]))]
        self._post_build_lines.append(
            f"self.{self._entity_ref(entity)}.setSizes({normalized_sizes})"
        )
        return lines

    def _emit_wizard_creation(self, entity: EntityModel) -> list[str]:
        document = self._require_document()
        lines = self._emit_regular_entity_creation(entity)
        for index, page in enumerate(self._get_wizard_pages(entity.id)):
            page_ref = self._internal_ref(page)
            lines.extend(
                [
                    f"self.{page_ref} = QWizardPage()",
                    f"self.{page_ref}.setObjectName({self._python_string(self._object_name(page.name))})",
                    f"self.{self._entity_ref(entity)}.setPage({index}, self.{page_ref})",
                ]
            )
        current_index = int(entity.properties.get("current_index", 0))
        self._post_build_lines.append(
            f"self.{self._entity_ref(entity)}.setStartId({current_index})"
        )
        return lines

    def _emit_geometry(self, entity: EntityModel) -> list[str]:
        ref_name = self._entity_ref(entity)
        geometry = entity.geometry
        return [
            (
                f"self.{ref_name}.setGeometry("
                f"{int(geometry['x'])}, {int(geometry['y'])}, "
                f"{int(geometry['width'])}, {int(geometry['height'])})"
            )
        ]

    def _emit_properties(self, entity: EntityModel) -> list[str]:
        handlers = {
            "QLabel": self._emit_label_properties,
            "QPushButton": self._emit_push_button_properties,
            "QLineEdit": self._emit_line_edit_properties,
            "QPlainTextEdit": self._emit_plain_text_edit_properties,
            "QTextEdit": self._emit_text_edit_properties,
            "QCheckBox": self._emit_check_box_properties,
            "QRadioButton": self._emit_radio_button_properties,
            "QComboBox": self._emit_combo_box_properties,
            "QListView": self._emit_list_view_properties,
            "QListWidget": self._emit_list_widget_properties,
            "QTreeView": self._emit_tree_view_properties,
            "QTableView": self._emit_table_view_properties,
            "QTableWidget": self._emit_table_widget_properties,
            "QTreeWidget": self._emit_tree_widget_properties,
            "QDateEdit": self._emit_date_edit_properties,
            "QDateTimeEdit": self._emit_datetime_edit_properties,
            "QCalendarWidget": self._emit_calendar_widget_properties,
            "QFontComboBox": self._emit_font_combo_box_properties,
            "QKeySequenceEdit": self._emit_key_sequence_edit_properties,
            "QDial": self._emit_dial_properties,
            "QLCDNumber": self._emit_lcd_number_properties,
            "QTimeEdit": self._emit_time_edit_properties,
            "QProgressBar": self._emit_progress_bar_properties,
            "QSlider": self._emit_slider_properties,
            "QDoubleSpinBox": self._emit_double_spin_box_properties,
            "QSpinBox": self._emit_spin_box_properties,
            "QFrame": self._emit_frame_properties,
            "QGroupBox": self._emit_group_box_properties,
            "QTabWidget": self._emit_tab_widget_properties,
            "QScrollArea": self._emit_scroll_area_properties,
            "QSplitter": self._emit_splitter_properties,
            "QWizard": self._emit_wizard_properties,
        }
        handler = handlers.get(entity.type)
        return [] if handler is None else handler(entity)

    def _emit_label_properties(self, entity: EntityModel) -> list[str]:
        return [f"self.{self._entity_ref(entity)}.setText({self._python_string(entity.properties.get('text', ''))})"]

    def _emit_push_button_properties(self, entity: EntityModel) -> list[str]:
        return [f"self.{self._entity_ref(entity)}.setText({self._python_string(entity.properties.get('text', ''))})"]

    def _emit_line_edit_properties(self, entity: EntityModel) -> list[str]:
        ref = self._entity_ref(entity)
        return [
            f"self.{ref}.setText({self._python_string(entity.properties.get('text', ''))})",
            f"self.{ref}.setPlaceholderText({self._python_string(entity.properties.get('placeholder', ''))})",
        ]

    def _emit_text_edit_properties(self, entity: EntityModel) -> list[str]:
        ref = self._entity_ref(entity)
        lines = [f"self.{ref}.setReadOnly({bool(entity.properties.get('read_only', False))})"]
        placeholder = str(entity.properties.get("placeholder", ""))
        text = str(entity.properties.get("text", ""))
        if placeholder:
            lines.append(f"self.{ref}.setPlaceholderText({self._python_string(placeholder)})")
        if text:
            lines.append(f"self.{ref}.setPlainText({self._python_string(text)})")
        return lines

    def _emit_plain_text_edit_properties(self, entity: EntityModel) -> list[str]:
        ref = self._entity_ref(entity)
        lines = [f"self.{ref}.setReadOnly({bool(entity.properties.get('read_only', False))})"]
        placeholder = str(entity.properties.get("placeholder", ""))
        text = str(entity.properties.get("text", ""))
        if placeholder:
            lines.append(f"self.{ref}.setPlaceholderText({self._python_string(placeholder)})")
        if text:
            lines.append(f"self.{ref}.setPlainText({self._python_string(text)})")
        return lines

    def _emit_check_box_properties(self, entity: EntityModel) -> list[str]:
        ref = self._entity_ref(entity)
        return [
            f"self.{ref}.setText({self._python_string(entity.properties.get('text', ''))})",
            f"self.{ref}.setChecked({bool(entity.properties.get('checked', False))})",
        ]

    def _emit_radio_button_properties(self, entity: EntityModel) -> list[str]:
        ref = self._entity_ref(entity)
        return [
            f"self.{ref}.setText({self._python_string(entity.properties.get('text', ''))})",
            f"self.{ref}.setChecked({bool(entity.properties.get('checked', False))})",
        ]

    def _emit_combo_box_properties(self, entity: EntityModel) -> list[str]:
        ref = self._entity_ref(entity)
        items = entity.properties.get("items", [])
        if not isinstance(items, list):
            items = []
        lines = [
            f"self.{ref}.setEditable({bool(entity.properties.get('editable', False))})",
        ]
        for item in items:
            lines.append(f"self.{ref}.addItem({self._python_string(item)})")
        current_index = int(entity.properties.get("current_index", 0))
        if items:
            current_index = max(0, min(current_index, len(items) - 1))
        else:
            current_index = 0
        lines.append(f"self.{ref}.setCurrentIndex({current_index})")
        return lines

    def _emit_list_widget_properties(self, entity: EntityModel) -> list[str]:
        ref = self._entity_ref(entity)
        items = entity.properties.get("items", [])
        if not isinstance(items, list):
            items = []
        normalized_items = [str(item) for item in items]
        current_row = int(entity.properties.get("current_row", -1))
        lines: list[str] = []
        if normalized_items:
            rendered_items = ", ".join(self._python_string(item) for item in normalized_items)
            lines.append(f"self.{ref}.addItems([{rendered_items}])")
        if 0 <= current_row < len(normalized_items):
            lines.append(f"self.{ref}.setCurrentRow({current_row})")
        return lines

    def _emit_list_view_properties(self, entity: EntityModel) -> list[str]:
        ref = self._entity_ref(entity)
        model_ref = f"{ref}_model"
        model_items = entity.properties.get("model_items", [])
        if not isinstance(model_items, list):
            model_items = []
        rendered_items = ", ".join(self._python_string(str(item)) for item in model_items)
        return [
            f"{model_ref} = QStringListModel()",
            f"{model_ref}.setStringList([{rendered_items}])",
            f"self.{ref}.setModel({model_ref})",
        ]

    def _emit_tree_view_properties(self, entity: EntityModel) -> list[str]:
        ref = self._entity_ref(entity)
        model_ref = f"{ref}_model"
        header_labels = entity.properties.get("header_labels", [])
        if not isinstance(header_labels, list):
            header_labels = []
        rendered_headers = ", ".join(self._python_string(str(item)) for item in header_labels)
        return [
            f"{model_ref} = QStandardItemModel()",
            f"{model_ref}.setHorizontalHeaderLabels([{rendered_headers}])",
            f"self.{ref}.setModel({model_ref})",
        ]

    def _emit_table_view_properties(self, entity: EntityModel) -> list[str]:
        ref = self._entity_ref(entity)
        model_ref = f"{ref}_model"
        column_count = max(0, int(entity.properties.get("column_count", 3)))
        header_labels = entity.properties.get("header_labels", [])
        if not isinstance(header_labels, list):
            header_labels = []
        normalized_headers = [str(item) for item in header_labels][:column_count]
        rendered_headers = ", ".join(self._python_string(item) for item in normalized_headers)
        lines = [
            f"{model_ref} = QStandardItemModel()",
            f"{model_ref}.setColumnCount({column_count})",
        ]
        if normalized_headers:
            lines.append(f"{model_ref}.setHorizontalHeaderLabels([{rendered_headers}])")
        lines.append(f"self.{ref}.setModel({model_ref})")
        return lines

    def _emit_table_widget_properties(self, entity: EntityModel) -> list[str]:
        ref = self._entity_ref(entity)
        row_count = max(0, int(entity.properties.get("row_count", 3)))
        column_count = max(0, int(entity.properties.get("column_count", 3)))
        horizontal_headers = entity.properties.get("horizontal_headers", [])
        vertical_headers = entity.properties.get("vertical_headers", [])
        cell_values = entity.properties.get("cell_values", [])
        if not isinstance(horizontal_headers, list):
            horizontal_headers = []
        if not isinstance(vertical_headers, list):
            vertical_headers = []
        if not isinstance(cell_values, list):
            cell_values = []

        normalized_horizontal = [str(item) for item in horizontal_headers][:column_count]
        normalized_vertical = [str(item) for item in vertical_headers][:row_count]

        lines = [
            f"self.{ref}.setRowCount({row_count})",
            f"self.{ref}.setColumnCount({column_count})",
        ]
        if normalized_horizontal:
            rendered_horizontal = ", ".join(self._python_string(item) for item in normalized_horizontal)
            lines.append(f"self.{ref}.setHorizontalHeaderLabels([{rendered_horizontal}])")
        if normalized_vertical:
            rendered_vertical = ", ".join(self._python_string(item) for item in normalized_vertical)
            lines.append(f"self.{ref}.setVerticalHeaderLabels([{rendered_vertical}])")
        for row_index, row_values in enumerate(cell_values[:row_count]):
            if not isinstance(row_values, list):
                continue
            for column_index, cell_value in enumerate(row_values[:column_count]):
                lines.append(
                    f"self.{ref}.setItem({row_index}, {column_index}, QTableWidgetItem({self._python_string(str(cell_value))}))"
                )
        return lines

    def _emit_tree_widget_properties(self, entity: EntityModel) -> list[str]:
        ref = self._entity_ref(entity)
        column_count = max(0, int(entity.properties.get("column_count", 1)))
        header_labels = entity.properties.get("header_labels", [])
        tree_items = entity.properties.get("tree_items", [])
        if not isinstance(header_labels, list):
            header_labels = []
        if not isinstance(tree_items, list):
            tree_items = []

        normalized_headers = [str(item) for item in header_labels][:column_count]
        lines = [f"self.{ref}.setColumnCount({column_count})"]
        if normalized_headers:
            rendered_headers = ", ".join(self._python_string(item) for item in normalized_headers)
            lines.append(f"self.{ref}.setHeaderLabels([{rendered_headers}])")
        for index, tree_item in enumerate(tree_items):
            item_ref = f"{ref}_item_{index}"
            lines.extend(
                self._emit_tree_widget_item_lines(
                    tree_item=tree_item,
                    item_ref=item_ref,
                    parent_ref=f"self.{ref}",
                    line_method="addTopLevelItem",
                    path=[index],
                )
            )
        return lines

    def _emit_date_edit_properties(self, entity: EntityModel) -> list[str]:
        ref = self._entity_ref(entity)
        return [
            f"self.{ref}.setMinimumDate({self._emit_qdate(str(entity.properties.get('minimum_date', '1900-01-01')))})",
            f"self.{ref}.setMaximumDate({self._emit_qdate(str(entity.properties.get('maximum_date', '2100-12-31')))})",
            f"self.{ref}.setDate({self._emit_qdate(str(entity.properties.get('date', '2026-01-01')))})",
        ]

    def _emit_time_edit_properties(self, entity: EntityModel) -> list[str]:
        ref = self._entity_ref(entity)
        return [
            f"self.{ref}.setMinimumTime({self._emit_qtime(str(entity.properties.get('minimum_time', '00:00:00')))})",
            f"self.{ref}.setMaximumTime({self._emit_qtime(str(entity.properties.get('maximum_time', '23:59:59')))})",
            f"self.{ref}.setTime({self._emit_qtime(str(entity.properties.get('time', '12:00:00')))})",
        ]

    def _emit_lcd_number_properties(self, entity: EntityModel) -> list[str]:
        ref = self._entity_ref(entity)
        return [
            f"self.{ref}.setDigitCount({int(entity.properties.get('digit_count', 5))})",
            f"self.{ref}.display({int(entity.properties.get('value', 0))})",
        ]

    def _emit_datetime_edit_properties(self, entity: EntityModel) -> list[str]:
        ref = self._entity_ref(entity)
        return [
            f"self.{ref}.setMinimumDateTime({self._emit_qdatetime(str(entity.properties.get('minimum_datetime', '1900-01-01 00:00:00')))})",
            f"self.{ref}.setMaximumDateTime({self._emit_qdatetime(str(entity.properties.get('maximum_datetime', '2100-12-31 23:59:59')))})",
            f"self.{ref}.setDateTime({self._emit_qdatetime(str(entity.properties.get('datetime', '2026-01-01 12:00:00')))})",
        ]

    def _emit_calendar_widget_properties(self, entity: EntityModel) -> list[str]:
        ref = self._entity_ref(entity)
        return [
            f"self.{ref}.setMinimumDate({self._emit_qdate(str(entity.properties.get('minimum_date', '1900-01-01')))})",
            f"self.{ref}.setMaximumDate({self._emit_qdate(str(entity.properties.get('maximum_date', '2100-12-31')))})",
            f"self.{ref}.setSelectedDate({self._emit_qdate(str(entity.properties.get('selected_date', '2026-01-01')))})",
        ]

    def _emit_font_combo_box_properties(self, entity: EntityModel) -> list[str]:
        ref = self._entity_ref(entity)
        family = str(entity.properties.get("current_font_family", ""))
        if not family:
            return []
        return [f"self.{ref}.setCurrentFont({self._emit_qfont(family)})"]

    def _emit_key_sequence_edit_properties(self, entity: EntityModel) -> list[str]:
        ref = self._entity_ref(entity)
        key_sequence = str(entity.properties.get("key_sequence", ""))
        if not key_sequence:
            return []
        return [f"self.{ref}.setKeySequence({self._emit_qkeysequence(key_sequence)})"]

    def _emit_dial_properties(self, entity: EntityModel) -> list[str]:
        ref = self._entity_ref(entity)
        return [
            f"self.{ref}.setMinimum({int(entity.properties.get('minimum', 0))})",
            f"self.{ref}.setMaximum({int(entity.properties.get('maximum', 100))})",
            f"self.{ref}.setSingleStep({int(entity.properties.get('step', 1))})",
            f"self.{ref}.setValue({int(entity.properties.get('value', 0))})",
        ]

    def _emit_spin_box_properties(self, entity: EntityModel) -> list[str]:
        ref = self._entity_ref(entity)
        lines = [
            f"self.{ref}.setMinimum({int(entity.properties.get('minimum', 0))})",
            f"self.{ref}.setMaximum({int(entity.properties.get('maximum', 99))})",
            f"self.{ref}.setSingleStep({int(entity.properties.get('step', 1))})",
        ]
        prefix = str(entity.properties.get("prefix", ""))
        suffix = str(entity.properties.get("suffix", ""))
        if prefix:
            lines.append(f"self.{ref}.setPrefix({self._python_string(prefix)})")
        if suffix:
            lines.append(f"self.{ref}.setSuffix({self._python_string(suffix)})")
        lines.append(f"self.{ref}.setValue({int(entity.properties.get('value', 0))})")
        return lines

    def _emit_double_spin_box_properties(self, entity: EntityModel) -> list[str]:
        ref = self._entity_ref(entity)
        lines = [
            f"self.{ref}.setMinimum({float(entity.properties.get('minimum', 0.0))})",
            f"self.{ref}.setMaximum({float(entity.properties.get('maximum', 99.0))})",
            f"self.{ref}.setSingleStep({float(entity.properties.get('step', 1.0))})",
            f"self.{ref}.setDecimals({int(entity.properties.get('decimals', 2))})",
        ]
        prefix = str(entity.properties.get("prefix", ""))
        suffix = str(entity.properties.get("suffix", ""))
        if prefix:
            lines.append(f"self.{ref}.setPrefix({self._python_string(prefix)})")
        if suffix:
            lines.append(f"self.{ref}.setSuffix({self._python_string(suffix)})")
        lines.append(f"self.{ref}.setValue({float(entity.properties.get('value', 0.0))})")
        return lines

    def _emit_slider_properties(self, entity: EntityModel) -> list[str]:
        ref = self._entity_ref(entity)
        return [
            f"self.{ref}.setOrientation({self._orientation_ref(str(entity.properties.get('orientation', 'horizontal')))})",
            f"self.{ref}.setMinimum({int(entity.properties.get('minimum', 0))})",
            f"self.{ref}.setMaximum({int(entity.properties.get('maximum', 100))})",
            f"self.{ref}.setSingleStep({int(entity.properties.get('step', 1))})",
            f"self.{ref}.setValue({int(entity.properties.get('value', 0))})",
        ]

    def _emit_progress_bar_properties(self, entity: EntityModel) -> list[str]:
        ref = self._entity_ref(entity)
        return [
            f"self.{ref}.setMinimum({int(entity.properties.get('minimum', 0))})",
            f"self.{ref}.setMaximum({int(entity.properties.get('maximum', 100))})",
            f"self.{ref}.setValue({int(entity.properties.get('value', 0))})",
            f"self.{ref}.setTextVisible({bool(entity.properties.get('text_visible', True))})",
        ]

    def _emit_frame_properties(self, entity: EntityModel) -> list[str]:
        ref = self._entity_ref(entity)
        frame_shape = self._frame_shape_ref(str(entity.properties.get("frame_shape", "StyledPanel")))
        frame_shadow = self._frame_shadow_ref(str(entity.properties.get("frame_shadow", "Raised")))
        return [
            f"self.{ref}.setFrameShape({frame_shape})",
            f"self.{ref}.setFrameShadow({frame_shadow})",
        ]

    def _emit_group_box_properties(self, entity: EntityModel) -> list[str]:
        ref = self._entity_ref(entity)
        return [
            f"self.{ref}.setTitle({self._python_string(entity.properties.get('title', ''))})",
            f"self.{ref}.setCheckable({bool(entity.properties.get('checkable', False))})",
            f"self.{ref}.setChecked({bool(entity.properties.get('checked', False))})",
        ]

    def _emit_tab_widget_properties(self, entity: EntityModel) -> list[str]:
        ref = self._entity_ref(entity)
        current_index = int(entity.properties.get("current_index", 0))
        return [
            f"self.{ref}.setTabsClosable({bool(entity.properties.get('tabs_closable', False))})",
        ]

    def _emit_scroll_area_properties(self, entity: EntityModel) -> list[str]:
        ref = self._entity_ref(entity)
        return [f"self.{ref}.setWidgetResizable({bool(entity.properties.get('widget_resizable', True))})"]

    def _emit_splitter_properties(self, entity: EntityModel) -> list[str]:
        ref = self._entity_ref(entity)
        sizes = entity.properties.get("sizes", [1, 1])
        if not isinstance(sizes, list) or len(sizes) < 2:
            sizes = [1, 1]
        normalized_sizes = [max(1, int(sizes[0])), max(1, int(sizes[1]))]
        return [
            f"self.{ref}.setOrientation({self._orientation_ref(str(entity.properties.get('orientation', 'horizontal')))})",
        ]

    def _emit_wizard_properties(self, entity: EntityModel) -> list[str]:
        document = self._require_document()
        ref = self._entity_ref(entity)
        lines = [f"self.{ref}.setWindowTitle({self._python_string(entity.properties.get('window_title', ''))})"]
        for page in self._get_wizard_pages(entity.id):
            page_ref = self._internal_ref(page)
            lines.extend(
                [
                    f"self.{page_ref}.setTitle({self._python_string(page.properties.get('title', ''))})",
                    f"self.{page_ref}.setSubTitle({self._python_string(page.properties.get('subtitle', ''))})",
                ]
            )
        return lines

    def _build_main_guard(self, document: FormDocument) -> str:
        class_name = self._root_class_name(document.form_root.root_widget_type)
        return "\n".join(
            [
                'if __name__ == "__main__":',
                "    app = QApplication(sys.argv)",
                f"    widget = {class_name}()",
                "    widget.show()",
                "    sys.exit(app.exec())",
            ]
        )

    def _entity_ref(self, entity: EntityModel) -> str:
        ref_name = self._entity_refs.get(entity.id)
        if ref_name is None:
            ref_name = self._make_unique_ref_name(entity.name)
            self._entity_refs[entity.id] = ref_name
        return ref_name

    def _internal_ref(self, entity: EntityModel) -> str:
        ref_name = self._internal_refs.get(entity.id)
        if ref_name is None:
            ref_name = self._make_unique_ref_name(entity.name)
            self._internal_refs[entity.id] = ref_name
        return ref_name

    def _get_parent_ref(self, entity: EntityModel) -> str:
        if entity.parent_id == self._require_document().form_root.id:
            return "self"
        if entity.parent_id in self._internal_refs:
            return f"self.{self._internal_refs[entity.parent_id]}"
        parent = self._require_document().get_entity(entity.parent_id)
        if parent is None:
            self._raise_diagnostic(
                f"Unknown parent entity '{entity.parent_id}' for '{entity.id}'.",
                stage="get_parent_ref",
                entity=entity,
                pattern="entity.parent_id -> existing parent entity",
            )
        return f"self.{self._entity_ref(parent)}"

    def _raise_diagnostic(
        self,
        message: str,
        *,
        stage: str,
        entity: EntityModel | None = None,
        pattern: str | None = None,
        details: dict[str, object] | None = None,
    ) -> None:
        diagnostic = ExportDiagnostic(
            stage=stage,
            message=message,
            pattern=pattern,
            entity_id=None if entity is None else entity.id,
            entity_type=None if entity is None else entity.type,
            details={} if details is None else dict(details),
        )
        raise ExportDiagnosticError(diagnostic)

    def _qt_class_name(self, type_name: str) -> str:
        return self._require_document().widget_registry.get_type(type_name).qt_class_name

    def _get_root_entities(self) -> list[EntityModel]:
        return self._sort_entities(self._require_document().get_root_entities())

    def _get_children(self, parent_id: str) -> list[EntityModel]:
        return self._sort_entities(self._require_document().get_children(parent_id))

    def _get_tab_pages(self, tab_widget_id: str) -> list[EntityModel]:
        return self._sort_entities(self._require_document().get_tab_pages(tab_widget_id))

    def _get_splitter_panes(self, splitter_id: str) -> list[EntityModel]:
        return self._sort_entities(self._require_document().get_splitter_panes(splitter_id))

    def _get_wizard_pages(self, wizard_id: str) -> list[EntityModel]:
        return self._sort_entities(self._require_document().get_wizard_pages(wizard_id))

    @staticmethod
    def _sort_entities(entities: list[EntityModel]) -> list[EntityModel]:
        return sorted(
            entities,
            key=lambda entity: (int(entity.order), str(entity.name), str(entity.id)),
        )

    def _root_class_name(self, root_widget_type: str) -> str:
        return "GeneratedDialog" if root_widget_type == "QDialog" else "GeneratedWidget"

    def _frame_shape_ref(self, value: str) -> str:
        mapping = {
            "NoFrame": "QFrame.Shape.NoFrame",
            "Box": "QFrame.Shape.Box",
            "Panel": "QFrame.Shape.Panel",
            "StyledPanel": "QFrame.Shape.StyledPanel",
            "HLine": "QFrame.Shape.HLine",
            "VLine": "QFrame.Shape.VLine",
            "WinPanel": "QFrame.Shape.WinPanel",
        }
        return mapping.get(value, "QFrame.Shape.StyledPanel")

    def _frame_shadow_ref(self, value: str) -> str:
        mapping = {
            "Plain": "QFrame.Shadow.Plain",
            "Raised": "QFrame.Shadow.Raised",
            "Sunken": "QFrame.Shadow.Sunken",
        }
        return mapping.get(value, "QFrame.Shadow.Raised")

    @staticmethod
    def _orientation_ref(value: str) -> str:
        return "Qt.Vertical" if str(value).lower() == "vertical" else "Qt.Horizontal"

    @staticmethod
    def _emit_qdate(date_string: str) -> str:
        parsed = parse_date_string(date_string)
        if parsed is None:
            diagnostic = ExportDiagnostic(
                stage="emit_qdate",
                message=f"Invalid date string for export: {date_string}",
                pattern="YYYY-MM-DD",
                details={"value": date_string},
            )
            raise ExportDiagnosticError(diagnostic)
        return f"QDate({parsed.year}, {parsed.month}, {parsed.day})"

    @staticmethod
    def _emit_qtime(time_string: str) -> str:
        parsed = parse_time_string(time_string)
        if parsed is None:
            diagnostic = ExportDiagnostic(
                stage="emit_qtime",
                message=f"Invalid time string for export: {time_string}",
                pattern="HH:MM:SS",
                details={"value": time_string},
            )
            raise ExportDiagnosticError(diagnostic)
        return f"QTime({parsed.hour}, {parsed.minute}, {parsed.second})"

    @staticmethod
    def _emit_qdatetime(datetime_string: str) -> str:
        parsed = parse_datetime_string(datetime_string)
        if parsed is None:
            diagnostic = ExportDiagnostic(
                stage="emit_qdatetime",
                message=f"Invalid datetime string for export: {datetime_string}",
                pattern="YYYY-MM-DD HH:MM:SS",
                details={"value": datetime_string},
            )
            raise ExportDiagnosticError(diagnostic)
        return (
            f"QDateTime(QDate({parsed.year}, {parsed.month}, {parsed.day}), "
            f"QTime({parsed.hour}, {parsed.minute}, {parsed.second}))"
        )

    @staticmethod
    def _emit_qfont(font_family: str) -> str:
        return f"QFont({PythonExporter._python_string(str(font_family))})"

    @staticmethod
    def _emit_qkeysequence(key_sequence: str) -> str:
        return f"QKeySequence({PythonExporter._python_string(str(key_sequence))})"

    def _emit_tree_widget_item_lines(
        self,
        *,
        tree_item: object,
        item_ref: str,
        parent_ref: str,
        line_method: str,
        path: list[int],
    ) -> list[str]:
        if not isinstance(tree_item, dict):
            return []
        raw_texts = tree_item.get("texts", [])
        texts = [str(item) for item in raw_texts] if isinstance(raw_texts, list) else []
        rendered_texts = ", ".join(self._python_string(text) for text in texts)
        lines = [
            f"{item_ref} = QTreeWidgetItem([{rendered_texts}])",
            f"{parent_ref}.{line_method}({item_ref})",
        ]
        raw_children = tree_item.get("children", [])
        if isinstance(raw_children, list):
            for child_index, child_item in enumerate(raw_children):
                child_ref = f"{item_ref}_{child_index}"
                lines.extend(
                    self._emit_tree_widget_item_lines(
                        tree_item=child_item,
                        item_ref=child_ref,
                        parent_ref=item_ref,
                        line_method="addChild",
                        path=[*path, child_index],
                    )
                )
        return lines

    def _make_unique_ref_name(self, base_name: str) -> str:
        candidate = self._sanitize_object_name(base_name)
        if candidate not in self._used_ref_names:
            self._used_ref_names.add(candidate)
            return candidate
        suffix = 2
        while f"{candidate}_{suffix}" in self._used_ref_names:
            suffix += 1
        unique_name = f"{candidate}_{suffix}"
        self._used_ref_names.add(unique_name)
        return unique_name

    def _sanitize_object_name(self, value: str) -> str:
        normalized = re.sub(r"\W+", "_", str(value).strip().lower())
        normalized = normalized.strip("_") or "widget"
        if normalized[0].isdigit():
            normalized = f"widget_{normalized}"
        if keyword.iskeyword(normalized):
            normalized = f"{normalized}_widget"
        return normalized

    @staticmethod
    def _object_name(value: str) -> str:
        return str(value).strip() or "widget"

    @staticmethod
    def _python_string(value: object) -> str:
        return repr("" if value is None else str(value))

    def _require_document(self) -> FormDocument:
        if self._document is None:
            raise RuntimeError("Exporter has no active document.")
        return self._document


Exporter = PythonExporter
