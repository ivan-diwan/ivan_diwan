from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path

from form_constructor.document.form_document import FormDocument
from form_constructor.document.models import EntityModel, FormRootModel
from form_constructor.document.validator import DocumentValidator
from form_constructor.registry.widget_registry import WidgetRegistry
from form_constructor.utils.date_utils import format_date_string, normalize_date_string, parse_date_string
from form_constructor.utils.datetime_utils import format_datetime_string, normalize_datetime_string, parse_datetime_string
from form_constructor.utils.time_utils import format_time_string, normalize_time_string, parse_time_string
from form_constructor.utils.geometry import make_geometry


@dataclass
class ParsedRoot:
    root_widget_type: str = "QWidget"
    name: str = "Form"
    width: int = 800
    height: int = 600
    window_title: str = ""


@dataclass
class ParsedEntity:
    ref_name: str
    type_name: str
    parent_ref: str | None
    creation_order: int
    object_name: str | None = None
    geometry: dict | None = None
    properties: dict = field(default_factory=dict)
    internal_role: str | None = None
    special_parent_ref: str | None = None
    special_order: int | None = None


@dataclass
class ImportDiagnostic:
    stage: str
    message: str
    line: int | None = None
    pattern: str | None = None
    entity_ref: str | None = None
    entity_type: str | None = None
    unsupported: bool = False
    details: dict[str, object] = field(default_factory=dict)

    def format_message(self) -> str:
        parts = [self.message]
        if self.line is not None:
            parts.append(f"line {self.line}")
        if self.pattern:
            parts.append(f"pattern: {self.pattern}")
        if self.entity_ref:
            parts.append(f"entity_ref: {self.entity_ref}")
        if self.entity_type:
            parts.append(f"entity_type: {self.entity_type}")
        if self.unsupported:
            parts.append("unsupported case")
        return " | ".join(parts)


class ImportDiagnosticError(ValueError):
    def __init__(self, diagnostic: ImportDiagnostic) -> None:
        super().__init__(diagnostic.format_message())
        self.diagnostic = diagnostic


class PythonImporter:
    def __init__(
        self,
        widget_registry: WidgetRegistry,
        validator: DocumentValidator | None = None,
    ) -> None:
        self._widget_registry = widget_registry
        self._validator = validator or DocumentValidator()
        self._last_diagnostic: ImportDiagnostic | None = None

    @property
    def last_diagnostic(self) -> ImportDiagnostic | None:
        return self._last_diagnostic

    def import_from_file(self, path: str) -> FormDocument:
        code = Path(path).read_text(encoding="utf-8")
        try:
            return self.import_from_code(code)
        except ImportDiagnosticError as error:
            if "filename" not in error.diagnostic.details:
                error.diagnostic.details["filename"] = str(path)
            raise

    def import_from_code(self, code: str) -> FormDocument:
        self._last_diagnostic = None
        try:
            module = self._parse_ast(code)
            class_node = self._find_form_class(module)
            setup_method = self._find_setup_method(class_node)
            parsed_root = self._extract_root_info(class_node, setup_method)
            parsed_entities = self._extract_entities(setup_method)
            document = self._build_document(parsed_root, parsed_entities)
            self._validator.validate_document(document)
            return document
        except ImportDiagnosticError as error:
            self._last_diagnostic = error.diagnostic
            raise
        except ValueError as error:
            diagnostic = ImportDiagnostic(stage="import", message=str(error))
            self._last_diagnostic = diagnostic
            raise ImportDiagnosticError(diagnostic) from error

    def _raise_diagnostic(
        self,
        message: str,
        *,
        stage: str,
        node: ast.AST | None = None,
        line: int | None = None,
        pattern: str | None = None,
        entity: ParsedEntity | None = None,
        unsupported: bool = False,
        details: dict[str, object] | None = None,
    ) -> None:
        diagnostic = ImportDiagnostic(
            stage=stage,
            message=message,
            line=line if line is not None else getattr(node, "lineno", None),
            pattern=pattern,
            entity_ref=None if entity is None else entity.ref_name,
            entity_type=None if entity is None else entity.type_name,
            unsupported=unsupported,
            details={} if details is None else dict(details),
        )
        raise ImportDiagnosticError(diagnostic)

    def _parse_ast(self, code: str) -> ast.Module:
        try:
            return ast.parse(code)
        except SyntaxError as error:
            self._raise_diagnostic(
                "Invalid Python syntax.",
                stage="parse_ast",
                line=error.lineno,
                pattern=error.text.strip() if error.text else None,
                details={"offset": error.offset or 0},
            )

    def _find_form_class(self, module: ast.Module) -> ast.ClassDef:
        for node in module.body:
            if not isinstance(node, ast.ClassDef):
                continue
            base_names = [self._name_from_expr(base) for base in node.bases]
            if any(base_name in {"QWidget", "QDialog"} for base_name in base_names):
                return node
        self._raise_diagnostic(
            "Could not find exported form class.",
            stage="find_form_class",
            node=module,
            pattern="class GeneratedWidget(QWidget|QDialog)",
        )

    def _find_setup_method(self, class_node: ast.ClassDef) -> ast.FunctionDef:
        for node in class_node.body:
            if isinstance(node, ast.FunctionDef) and node.name == "setup_ui":
                return node
        self._raise_diagnostic(
            "Could not find setup_ui method in exported form class.",
            stage="find_setup_method",
            node=class_node,
            pattern="def setup_ui(self):",
        )

    def _extract_root_info(self, class_node: ast.ClassDef, setup_method: ast.FunctionDef) -> ParsedRoot:
        base_names = [self._name_from_expr(base) for base in class_node.bases]
        root_widget_type = "QDialog" if "QDialog" in base_names else "QWidget"
        parsed_root = ParsedRoot(root_widget_type=root_widget_type, window_title="")
        for statement in setup_method.body:
            call = self._extract_call(statement)
            if call is None:
                continue
            target_ref = self._call_target_ref(call)
            if target_ref != "self":
                continue
            method_name = self._call_method_name(call)
            if method_name == "setObjectName" and call.args:
                parsed_root.name = self._string_value(call.args[0]) or parsed_root.name
            elif method_name == "resize" and len(call.args) == 2:
                parsed_root.width = self._int_value(call.args[0], parsed_root.width)
                parsed_root.height = self._int_value(call.args[1], parsed_root.height)
            elif method_name == "setWindowTitle" and call.args:
                parsed_root.window_title = self._string_value(call.args[0]) or ""
        return parsed_root

    def _extract_entities(self, setup_method: ast.FunctionDef) -> dict[str, ParsedEntity]:
        parsed_entities: dict[str, ParsedEntity] = {}
        string_list_models: dict[str, list[str]] = {}
        standard_item_models: dict[str, dict[str, object]] = {}
        tree_widget_items: dict[str, dict[str, object]] = {}
        tree_widget_roots: dict[str, list[str]] = {}
        creation_order = 0

        for statement in setup_method.body:
            if not isinstance(statement, ast.Assign) or len(statement.targets) != 1:
                continue
            target = statement.targets[0]
            if isinstance(target, ast.Name) and isinstance(statement.value, ast.Call):
                type_name = self._name_from_expr(statement.value.func)
                if type_name == "QStringListModel":
                    string_list_models[target.id] = []
                elif type_name == "QStandardItemModel":
                    standard_item_models[target.id] = {
                        "column_count": 0,
                        "header_labels": [],
                    }
                elif type_name == "QTreeWidgetItem":
                    tree_item = self._parse_qtreewidgetitem_data(statement.value)
                    if tree_item is None:
                        self._raise_diagnostic(
                            "QTreeWidget import supports only QTreeWidgetItem([...]) in exported format.",
                            stage="extract_entities",
                            node=statement.value,
                            pattern="QTreeWidgetItem([...])",
                            unsupported=True,
                        )
                    tree_widget_items[target.id] = tree_item
                continue
            if not isinstance(target, ast.Attribute) or not self._is_self_ref(target.value):
                continue
            if not isinstance(statement.value, ast.Call):
                continue
            ref_name = target.attr
            type_name = self._name_from_expr(statement.value.func)
            if not type_name:
                continue
            parent_ref = self._extract_parent_ref_from_creation(statement.value)
            parsed_entities[ref_name] = ParsedEntity(
                ref_name=ref_name,
                type_name=type_name,
                parent_ref=parent_ref,
                creation_order=creation_order,
            )
            creation_order += 1

        for statement in setup_method.body:
            call = self._extract_call(statement)
            if call is None:
                continue
            target_ref = self._call_target_ref(call)
            method_name = self._call_method_name(call)
            if target_ref == "self":
                continue
            if target_ref in string_list_models:
                if method_name == "setStringList" and call.args:
                    string_list_models[target_ref] = self._string_list_value(call.args[0])
                continue
            if target_ref in standard_item_models:
                if method_name == "setColumnCount" and call.args:
                    standard_item_models[target_ref]["column_count"] = self._int_value(call.args[0], 0)
                if method_name == "setHorizontalHeaderLabels" and call.args:
                    standard_item_models[target_ref]["header_labels"] = self._string_list_value(call.args[0])
                continue
            if target_ref in tree_widget_items:
                if method_name == "addChild" and call.args:
                    child_ref = self._ref_name_from_expr(call.args[0])
                    if child_ref not in tree_widget_items:
                        self._raise_diagnostic(
                            "QTreeWidget import supports only QTreeWidgetItem variables created in exported format.",
                            stage="extract_entities",
                            node=call,
                            pattern="parent_item.addChild(child_item)",
                            unsupported=True,
                        )
                    children = tree_widget_items[target_ref].setdefault("children", [])
                    if isinstance(children, list):
                        children.append(child_ref)
                    continue
                continue
            entity = parsed_entities.get(target_ref)
            if entity is None:
                continue
            self._apply_entity_call(
                parsed_entities,
                string_list_models,
                standard_item_models,
                tree_widget_items,
                tree_widget_roots,
                entity,
                method_name,
                call,
            )

        for entity in parsed_entities.values():
            if entity.type_name == "QTreeWidget":
                entity.properties["tree_items"] = self._build_tree_widget_items(
                    tree_widget_roots.get(entity.ref_name, []),
                    tree_widget_items,
                )

        self._convert_internal_entities(parsed_entities)
        self._normalize_entity_geometry(parsed_entities)
        return parsed_entities

    def _apply_entity_call(
        self,
        parsed_entities: dict[str, ParsedEntity],
        string_list_models: dict[str, list[str]],
        standard_item_models: dict[str, dict[str, object]],
        tree_widget_items: dict[str, dict[str, object]],
        tree_widget_roots: dict[str, list[str]],
        entity: ParsedEntity,
        method_name: str,
        call: ast.Call,
    ) -> None:
        if method_name == "setObjectName" and call.args:
            entity.object_name = self._string_value(call.args[0])
            return
        if method_name == "setGeometry" and len(call.args) == 4:
            entity.geometry = make_geometry(
                self._int_value(call.args[0], 0),
                self._int_value(call.args[1], 0),
                self._int_value(call.args[2], 0),
                self._int_value(call.args[3], 0),
            )
            return
        if method_name == "setText" and call.args:
            entity.properties["text"] = self._string_value(call.args[0]) or ""
            return
        if method_name == "setPlaceholderText" and call.args:
            entity.properties["placeholder"] = self._string_value(call.args[0]) or ""
            return
        if method_name == "setModel" and call.args and entity.type_name == "QListView":
            model_ref = self._ref_name_from_expr(call.args[0])
            if model_ref in string_list_models:
                entity.properties["model_items"] = list(string_list_models[model_ref])
                return
            self._raise_diagnostic(
                "QListView import supports only QStringListModel created in exported format.",
                stage="apply_entity_call",
                node=call,
                pattern="QStringListModel -> setStringList -> setModel",
                entity=entity,
                unsupported=True,
            )
        if method_name == "setModel" and call.args and entity.type_name == "QTreeView":
            model_ref = self._ref_name_from_expr(call.args[0])
            if model_ref in standard_item_models:
                model_info = standard_item_models[model_ref]
                entity.properties["header_labels"] = list(model_info.get("header_labels", []))
                return
            self._raise_diagnostic(
                "QTreeView import supports only QStandardItemModel created in exported format.",
                stage="apply_entity_call",
                node=call,
                pattern="QStandardItemModel -> setHorizontalHeaderLabels -> setModel",
                entity=entity,
                unsupported=True,
            )
        if method_name == "setModel" and call.args and entity.type_name == "QTableView":
            model_ref = self._ref_name_from_expr(call.args[0])
            if model_ref in standard_item_models:
                model_info = standard_item_models[model_ref]
                entity.properties["column_count"] = int(model_info.get("column_count", 0))
                entity.properties["header_labels"] = list(model_info.get("header_labels", []))
                return
            self._raise_diagnostic(
                "QTableView import supports only QStandardItemModel created in exported format.",
                stage="apply_entity_call",
                node=call,
                pattern="QStandardItemModel -> setColumnCount -> setHorizontalHeaderLabels -> setModel",
                entity=entity,
                unsupported=True,
            )
        if method_name == "setPlainText" and call.args:
            entity.properties["text"] = self._string_value(call.args[0]) or ""
            return
        if method_name == "setDate" and call.args:
            parsed_date = self._parse_qdate_call(call.args[0])
            entity.properties["date"] = parsed_date or "2026-01-01"
            return
        if method_name == "setSelectedDate" and call.args:
            parsed_date = self._parse_qdate_call(call.args[0])
            entity.properties["selected_date"] = parsed_date or "2026-01-01"
            return
        if method_name == "setCurrentFont" and call.args:
            parsed_font = self._parse_qfont_call(call.args[0])
            if parsed_font is None:
                target_name = None
                if isinstance(call.args[0], ast.Call):
                    target_name = self._name_from_expr(call.args[0].func)
                elif isinstance(call.args[0], ast.AST):
                    target_name = self._name_from_expr(call.args[0])
                if target_name == "QFont":
                    self._raise_diagnostic(
                        "Complex QFont import is not supported in this version.",
                        stage="apply_entity_call",
                        node=call,
                        pattern="setCurrentFont(QFont(...))",
                        entity=entity,
                        unsupported=True,
                    )
                entity.properties["current_font_family"] = ""
                return
            entity.properties["current_font_family"] = parsed_font
            return
        if method_name == "setKeySequence" and call.args:
            parsed_key_sequence = self._parse_qkeysequence_call(call.args[0])
            if parsed_key_sequence is None:
                target_name = None
                if isinstance(call.args[0], ast.Call):
                    target_name = self._name_from_expr(call.args[0].func)
                elif isinstance(call.args[0], ast.AST):
                    target_name = self._name_from_expr(call.args[0])
                if target_name == "QKeySequence":
                    self._raise_diagnostic(
                        "Complex QKeySequence import is not supported in this version.",
                        stage="apply_entity_call",
                        node=call,
                        pattern="setKeySequence(QKeySequence(...))",
                        entity=entity,
                        unsupported=True,
                    )
                entity.properties["key_sequence"] = ""
                return
            entity.properties["key_sequence"] = parsed_key_sequence
            return
        if method_name == "setMinimum" and call.args and entity.type_name == "QDial":
            entity.properties["minimum"] = self._int_value(call.args[0], 0)
            return
        if method_name == "setMaximum" and call.args and entity.type_name == "QDial":
            entity.properties["maximum"] = self._int_value(call.args[0], 100)
            return
        if method_name == "setSingleStep" and call.args and entity.type_name == "QDial":
            entity.properties["step"] = self._int_value(call.args[0], 1)
            return
        if method_name == "setValue" and call.args and entity.type_name == "QDial":
            entity.properties["value"] = self._int_value(call.args[0], 0)
            return
        if method_name == "setDigitCount" and call.args and entity.type_name == "QLCDNumber":
            entity.properties["digit_count"] = self._int_value(call.args[0], 5)
            return
        if method_name == "display" and call.args and entity.type_name == "QLCDNumber":
            entity.properties["value"] = self._int_value(call.args[0], 0)
            return
        if method_name == "setTime" and call.args:
            parsed_time = self._parse_qtime_call(call.args[0])
            entity.properties["time"] = parsed_time or "12:00:00"
            return
        if method_name == "setDateTime" and call.args:
            parsed_datetime = self._parse_qdatetime_call(call.args[0])
            entity.properties["datetime"] = parsed_datetime or "2026-01-01 12:00:00"
            return
        if method_name == "setMinimumDate" and call.args:
            parsed_date = self._parse_qdate_call(call.args[0])
            entity.properties["minimum_date"] = parsed_date or "1900-01-01"
            return
        if method_name == "setMinimumTime" and call.args:
            parsed_time = self._parse_qtime_call(call.args[0])
            entity.properties["minimum_time"] = parsed_time or "00:00:00"
            return
        if method_name == "setMinimumDateTime" and call.args:
            parsed_datetime = self._parse_qdatetime_call(call.args[0])
            entity.properties["minimum_datetime"] = parsed_datetime or "1900-01-01 00:00:00"
            return
        if method_name == "setMaximumDate" and call.args:
            parsed_date = self._parse_qdate_call(call.args[0])
            entity.properties["maximum_date"] = parsed_date or "2100-12-31"
            return
        if method_name == "setMaximumTime" and call.args:
            parsed_time = self._parse_qtime_call(call.args[0])
            entity.properties["maximum_time"] = parsed_time or "23:59:59"
            return
        if method_name == "setMaximumDateTime" and call.args:
            parsed_datetime = self._parse_qdatetime_call(call.args[0])
            entity.properties["maximum_datetime"] = parsed_datetime or "2100-12-31 23:59:59"
            return
        if method_name == "setReadOnly" and call.args:
            entity.properties["read_only"] = self._bool_value(call.args[0], False)
            return
        if method_name == "setHtml" and call.args:
            self._raise_diagnostic(
                "QTextEdit HTML import is not supported in this version.",
                stage="apply_entity_call",
                node=call,
                pattern="setHtml(...)",
                entity=entity,
                unsupported=True,
            )
        if method_name == "appendPlainText" and call.args:
            self._raise_diagnostic(
                "QPlainTextEdit appendPlainText import is not supported in this version.",
                stage="apply_entity_call",
                node=call,
                pattern="appendPlainText(...)",
                entity=entity,
                unsupported=True,
            )
        if method_name == "setDisplayFormat" and call.args:
            if entity.type_name == "QDateEdit":
                self._raise_diagnostic(
                    "QDateEdit display format import is not supported in this version.",
                    stage="apply_entity_call",
                    node=call,
                    pattern="setDisplayFormat(...)",
                    entity=entity,
                    unsupported=True,
                )
            if entity.type_name == "QTimeEdit":
                self._raise_diagnostic(
                    "QTimeEdit display format import is not supported in this version.",
                    stage="apply_entity_call",
                    node=call,
                    pattern="setDisplayFormat(...)",
                    entity=entity,
                    unsupported=True,
                )
            if entity.type_name == "QDateTimeEdit":
                self._raise_diagnostic(
                    "QDateTimeEdit display format import is not supported in this version.",
                    stage="apply_entity_call",
                    node=call,
                    pattern="setDisplayFormat(...)",
                    entity=entity,
                    unsupported=True,
                )
            self._raise_diagnostic(
                "Display format import is not supported in this version.",
                stage="apply_entity_call",
                node=call,
                pattern="setDisplayFormat(...)",
                entity=entity,
                unsupported=True,
            )
        if method_name == "setGridVisible" and call.args:
            self._raise_diagnostic(
                "QCalendarWidget grid visibility import is not supported in this version.",
                stage="apply_entity_call",
                node=call,
                pattern="setGridVisible(...)",
                entity=entity,
                unsupported=True,
            )
        if method_name == "setNavigationBarVisible" and call.args:
            self._raise_diagnostic(
                "QCalendarWidget navigation bar visibility import is not supported in this version.",
                stage="apply_entity_call",
                node=call,
                pattern="setNavigationBarVisible(...)",
                entity=entity,
                unsupported=True,
            )
        if method_name == "setHorizontalHeaderFormat" and call.args:
            self._raise_diagnostic(
                "QCalendarWidget horizontal header format import is not supported in this version.",
                stage="apply_entity_call",
                node=call,
                pattern="setHorizontalHeaderFormat(...)",
                entity=entity,
                unsupported=True,
            )
        if method_name == "setVerticalHeaderFormat" and call.args:
            self._raise_diagnostic(
                "QCalendarWidget vertical header format import is not supported in this version.",
                stage="apply_entity_call",
                node=call,
                pattern="setVerticalHeaderFormat(...)",
                entity=entity,
                unsupported=True,
            )
        if method_name == "setChecked" and call.args:
            entity.properties["checked"] = self._bool_value(call.args[0], False)
            return
        if method_name == "setEditable" and call.args:
            entity.properties["editable"] = self._bool_value(call.args[0], False)
            return
        if method_name == "setTextVisible" and call.args:
            entity.properties["text_visible"] = self._bool_value(call.args[0], True)
            return
        if method_name == "setMinimum" and call.args:
            default = 0.0 if entity.type_name == "QDoubleSpinBox" else 0
            entity.properties["minimum"] = self._numeric_value(call.args[0], default)
            return
        if method_name == "setMaximum" and call.args:
            default = 99.0 if entity.type_name == "QDoubleSpinBox" else 99
            entity.properties["maximum"] = self._numeric_value(call.args[0], default)
            return
        if method_name == "setSingleStep" and call.args:
            default = 1.0 if entity.type_name == "QDoubleSpinBox" else 1
            entity.properties["step"] = self._numeric_value(call.args[0], default)
            return
        if method_name == "setDecimals" and call.args:
            entity.properties["decimals"] = self._int_value(call.args[0], 2)
            return
        if method_name == "setValue" and call.args:
            default = 0.0 if entity.type_name == "QDoubleSpinBox" else 0
            entity.properties["value"] = self._numeric_value(call.args[0], default)
            return
        if method_name == "setPrefix" and call.args:
            entity.properties["prefix"] = self._string_value(call.args[0]) or ""
            return
        if method_name == "setSuffix" and call.args:
            entity.properties["suffix"] = self._string_value(call.args[0]) or ""
            return
        if method_name == "addItem" and call.args:
            entity.properties.setdefault("items", []).append(self._string_value(call.args[0]) or "")
            return
        if method_name == "addItems" and call.args:
            entity.properties.setdefault("items", []).extend(self._string_list_value(call.args[0]))
            return
        if method_name == "setRowCount" and call.args:
            entity.properties["row_count"] = self._int_value(call.args[0], 3)
            return
        if method_name == "setColumnCount" and call.args:
            entity.properties["column_count"] = self._int_value(call.args[0], 3)
            return
        if method_name == "setHorizontalHeaderLabels" and call.args:
            entity.properties["horizontal_headers"] = self._string_list_value(call.args[0])
            return
        if method_name == "setVerticalHeaderLabels" and call.args:
            entity.properties["vertical_headers"] = self._string_list_value(call.args[0])
            return
        if method_name == "setHeaderLabels" and call.args:
            entity.properties["header_labels"] = self._string_list_value(call.args[0])
            return
        if method_name == "setCurrentIndex" and call.args:
            entity.properties["current_index"] = self._int_value(call.args[0], 0)
            return
        if method_name == "setCurrentRow" and call.args:
            entity.properties["current_row"] = self._int_value(call.args[0], -1)
            return
        if method_name == "setItem" and call.args:
            if entity.type_name != "QTableWidget" or len(call.args) < 3:
                self._raise_diagnostic(
                    "QTableWidget cell import is not supported in this version.",
                    stage="apply_entity_call",
                    node=call,
                    pattern="setItem(row, column, QTableWidgetItem(...))",
                    entity=entity,
                    unsupported=True,
                )
            row = self._int_value(call.args[0], -1)
            column = self._int_value(call.args[1], -1)
            cell_text = self._parse_qtablewidgetitem_text(call.args[2])
            if row < 0 or column < 0 or cell_text is None:
                self._raise_diagnostic(
                    'QTableWidget cell import supports only inline QTableWidgetItem("text").',
                    stage="apply_entity_call",
                    node=call,
                    pattern='setItem(row, column, QTableWidgetItem("text"))',
                    entity=entity,
                    unsupported=True,
                )
            cell_values = entity.properties.setdefault("cell_values", [])
            while len(cell_values) <= row:
                cell_values.append([])
            while len(cell_values[row]) <= column:
                cell_values[row].append("")
            cell_values[row][column] = cell_text
            return
        if method_name in {"addTopLevelItem", "addChild"} and call.args:
            tree_item_ref = self._ref_name_from_expr(call.args[0])
            if entity.type_name == "QTreeWidget" and method_name == "addTopLevelItem":
                if tree_item_ref not in tree_widget_items:
                    self._raise_diagnostic(
                        "QTreeWidget import supports only QTreeWidgetItem variables created in exported format.",
                        stage="apply_entity_call",
                        node=call,
                        pattern="tree_widget.addTopLevelItem(item_ref)",
                        entity=entity,
                        unsupported=True,
                    )
                tree_widget_roots.setdefault(entity.ref_name, []).append(tree_item_ref)
                return
            if tree_item_ref not in tree_widget_items:
                self._raise_diagnostic(
                    "QTreeWidget import supports only QTreeWidgetItem variables created in exported format.",
                    stage="apply_entity_call",
                    node=call,
                    pattern="tree_widget.addTopLevelItem(item_ref)",
                    entity=entity,
                    unsupported=True,
                )
            if method_name == "addChild":
                parent_item = tree_widget_items.get(entity.ref_name)
                if parent_item is None:
                    self._raise_diagnostic(
                        "QTreeWidget addChild import requires known QTreeWidgetItem parent.",
                        stage="apply_entity_call",
                        node=call,
                        pattern="parent_item.addChild(child_item)",
                        entity=entity,
                        unsupported=True,
                    )
                children = parent_item.setdefault("children", [])
                if isinstance(children, list):
                    children.append(tree_item_ref)
                    return
            self._raise_diagnostic(
                "QTreeWidget import supports only exported QTreeWidgetItem hierarchy.",
                stage="apply_entity_call",
                node=call,
                pattern="QTreeWidgetItem hierarchy exported by PythonExporter",
                entity=entity,
                unsupported=True,
            )
        if method_name == "setStartId" and call.args:
            entity.properties["current_index"] = self._int_value(call.args[0], 0)
            return
        if method_name == "setTabsClosable" and call.args:
            entity.properties["tabs_closable"] = self._bool_value(call.args[0], False)
            return
        if method_name == "setWidgetResizable" and call.args:
            entity.properties["widget_resizable"] = self._bool_value(call.args[0], True)
            return
        if method_name == "setOrientation" and call.args:
            entity.properties["orientation"] = self._orientation_value(call.args[0])
            return
        if method_name == "setSizes" and call.args:
            entity.properties["sizes"] = self._int_list_value(call.args[0])
            return
        if method_name == "setFrameShape" and call.args:
            entity.properties["frame_shape"] = self._frame_shape_value(call.args[0])
            return
        if method_name == "setFrameShadow" and call.args:
            entity.properties["frame_shadow"] = self._frame_shadow_value(call.args[0])
            return
        if method_name == "setTitle" and call.args:
            entity.properties["title"] = self._string_value(call.args[0]) or ""
            return
        if method_name == "setCheckable" and call.args:
            entity.properties["checkable"] = self._bool_value(call.args[0], False)
            return
        if method_name == "setWindowTitle" and call.args:
            entity.properties["window_title"] = self._string_value(call.args[0]) or ""
            return
        if method_name == "setSubTitle" and call.args:
            entity.properties["subtitle"] = self._string_value(call.args[0]) or ""
            return
        if method_name == "addTab" and len(call.args) >= 2:
            page_ref = self._ref_name_from_expr(call.args[0])
            if page_ref and page_ref in parsed_entities:
                page = parsed_entities[page_ref]
                page.special_parent_ref = entity.ref_name
                page.internal_role = "TabPage"
                page.special_order = self._next_special_order(parsed_entities, entity.ref_name, "TabPage")
                page.properties["title"] = self._string_value(call.args[1]) or ""
            return
        if method_name == "setWidget" and call.args:
            content_ref = self._ref_name_from_expr(call.args[0])
            if content_ref and content_ref in parsed_entities:
                content = parsed_entities[content_ref]
                content.special_parent_ref = entity.ref_name
                content.internal_role = "ContainerContent"
                content.special_order = 0
            return
        if method_name == "addWidget" and call.args:
            child_ref = self._ref_name_from_expr(call.args[0])
            if child_ref and child_ref in parsed_entities:
                child = parsed_entities[child_ref]
                if entity.type_name == "QSplitter":
                    child.special_parent_ref = entity.ref_name
                    child.internal_role = "SplitterPane"
                    child.special_order = self._next_special_order(parsed_entities, entity.ref_name, "SplitterPane")
            return
        if method_name == "setPage" and len(call.args) == 2:
            page_index = self._int_value(call.args[0], 0)
            page_ref = self._ref_name_from_expr(call.args[1])
            if page_ref and page_ref in parsed_entities:
                page = parsed_entities[page_ref]
                page.special_parent_ref = entity.ref_name
                page.internal_role = "WizardPage"
                page.special_order = page_index

    def _convert_internal_entities(self, parsed_entities: dict[str, ParsedEntity]) -> None:
        for entity in parsed_entities.values():
            if entity.internal_role is None:
                continue
            entity.type_name = entity.internal_role
            entity.parent_ref = entity.special_parent_ref

    def _normalize_entity_geometry(self, parsed_entities: dict[str, ParsedEntity]) -> None:
        for entity in parsed_entities.values():
            if entity.geometry is not None:
                continue
            if entity.type_name == "ContainerContent":
                parent = parsed_entities.get(entity.parent_ref or "")
                if parent is not None and parent.geometry is not None:
                    entity.geometry = make_geometry(0, 0, parent.geometry["width"], parent.geometry["height"])
                    continue
            if entity.type_name == "SplitterPane":
                parent = parsed_entities.get(entity.parent_ref or "")
                if parent is not None and parent.geometry is not None:
                    sizes = parent.properties.get("sizes", [1, 1])
                    if not isinstance(sizes, list) or len(sizes) != 2:
                        sizes = [1, 1]
                    first_size = max(1, int(sizes[0]))
                    second_size = max(1, int(sizes[1]))
                    total = first_size + second_size
                    width = max(1, int(parent.geometry["width"]))
                    height = max(1, int(parent.geometry["height"]))
                    if str(parent.properties.get("orientation", "horizontal")) == "vertical":
                        first_height = max(1, round(height * first_size / total))
                        second_height = max(1, height - first_height)
                        if entity.special_order == 0:
                            entity.geometry = make_geometry(0, 0, width, first_height)
                        else:
                            entity.geometry = make_geometry(0, first_height, width, second_height)
                    else:
                        first_width = max(1, round(width * first_size / total))
                        second_width = max(1, width - first_width)
                        if entity.special_order == 0:
                            entity.geometry = make_geometry(0, 0, first_width, height)
                        else:
                            entity.geometry = make_geometry(first_width, 0, second_width, height)
                    continue
            entity.geometry = make_geometry(0, 0, 0, 0)

    def _build_document(
        self,
        parsed_root: ParsedRoot,
        parsed_entities: dict[str, ParsedEntity],
    ) -> FormDocument:
        form_root = FormRootModel(
            id="form_root",
            type="FormRoot",
            name=parsed_root.name,
            root_widget_type=parsed_root.root_widget_type,
            width=parsed_root.width,
            height=parsed_root.height,
            window_title=parsed_root.window_title,
        )

        entity_models: dict[str, EntityModel] = {}
        for entity in self._sorted_parsed_entities(parsed_entities):
            entity_id = entity.ref_name
            parent_id = "form_root" if entity.parent_ref in {None, "self"} else entity.parent_ref
            entity_models[entity_id] = EntityModel(
                id=entity_id,
                type=entity.type_name,
                parent_id=parent_id,
                name=(entity.object_name or entity.ref_name),
                order=self._resolve_entity_order(parsed_entities, entity),
                geometry=dict(entity.geometry or make_geometry(0, 0, 0, 0)),
                properties=self._normalize_properties_for_type(entity.type_name, dict(entity.properties)),
            )

        return FormDocument(
            form_root=form_root,
            widget_registry=self._widget_registry,
            entities_by_id=entity_models,
        )

    @staticmethod
    def _sorted_parsed_entities(parsed_entities: dict[str, ParsedEntity]) -> list[ParsedEntity]:
        return sorted(
            parsed_entities.values(),
            key=lambda entity: (
                0 if entity.type_name not in {"TabPage", "ContainerContent", "SplitterPane", "WizardPage"} else 1,
                entity.creation_order,
                entity.ref_name,
            ),
        )

    @staticmethod
    def _resolve_entity_order(parsed_entities: dict[str, ParsedEntity], entity: ParsedEntity) -> int:
        if entity.special_order is not None:
            return int(entity.special_order)
        sibling_refs = [
            sibling
            for sibling in parsed_entities.values()
            if sibling.parent_ref == entity.parent_ref and sibling.internal_role is None
        ]
        sibling_refs = sorted(sibling_refs, key=lambda sibling: (sibling.creation_order, sibling.ref_name))
        for index, sibling in enumerate(sibling_refs):
            if sibling.ref_name == entity.ref_name:
                return index
        return 0

    @staticmethod
    def _normalize_properties_for_type(type_name: str, properties: dict) -> dict:
        if type_name == "QLabel":
            properties.setdefault("text", "")
        elif type_name == "QPushButton":
            properties.setdefault("text", "")
        elif type_name == "QLineEdit":
            properties.setdefault("text", "")
            properties.setdefault("placeholder", "")
        elif type_name == "QTextEdit":
            properties.setdefault("text", "")
            properties.setdefault("placeholder", "")
            properties.setdefault("read_only", False)
        elif type_name == "QPlainTextEdit":
            properties.setdefault("text", "")
            properties.setdefault("placeholder", "")
            properties.setdefault("read_only", False)
        elif type_name in {"QCheckBox", "QRadioButton"}:
            properties.setdefault("text", "")
            properties.setdefault("checked", False)
        elif type_name == "QComboBox":
            properties.setdefault("items", [])
            properties.setdefault("current_index", 0)
            properties.setdefault("editable", False)
        elif type_name == "QListView":
            properties.setdefault("model_items", [])
        elif type_name == "QTreeView":
            properties.setdefault("header_labels", [])
        elif type_name == "QTableView":
            properties.setdefault("column_count", 3)
            properties.setdefault("header_labels", [])
        elif type_name == "QListWidget":
            properties.setdefault("items", [])
            properties.setdefault("current_row", -1)
            properties.setdefault("current_text", "")
        elif type_name == "QTableWidget":
            properties.setdefault("row_count", 3)
            properties.setdefault("column_count", 3)
            properties.setdefault("horizontal_headers", [])
            properties.setdefault("vertical_headers", [])
            properties.setdefault("cell_values", [])
        elif type_name == "QTreeWidget":
            properties.setdefault("column_count", 1)
            properties.setdefault("header_labels", [])
        elif type_name == "QDateEdit":
            properties.setdefault("date", "2026-01-01")
            properties.setdefault("minimum_date", "1900-01-01")
            properties.setdefault("maximum_date", "2100-12-31")
        elif type_name == "QCalendarWidget":
            properties.setdefault("selected_date", "2026-01-01")
            properties.setdefault("minimum_date", "1900-01-01")
            properties.setdefault("maximum_date", "2100-12-31")
        elif type_name == "QFontComboBox":
            properties.setdefault("current_font_family", "")
        elif type_name == "QKeySequenceEdit":
            properties.setdefault("key_sequence", "")
        elif type_name == "QDial":
            properties.setdefault("value", 0)
            properties.setdefault("minimum", 0)
            properties.setdefault("maximum", 100)
            properties.setdefault("step", 1)
        elif type_name == "QLCDNumber":
            properties.setdefault("value", 0)
            properties.setdefault("digit_count", 5)
        elif type_name == "QTimeEdit":
            properties.setdefault("time", "12:00:00")
            properties.setdefault("minimum_time", "00:00:00")
            properties.setdefault("maximum_time", "23:59:59")
        elif type_name == "QDateTimeEdit":
            properties.setdefault("datetime", "2026-01-01 12:00:00")
            properties.setdefault("minimum_datetime", "1900-01-01 00:00:00")
            properties.setdefault("maximum_datetime", "2100-12-31 23:59:59")
        elif type_name == "QSpinBox":
            properties.setdefault("value", 0)
            properties.setdefault("minimum", 0)
            properties.setdefault("maximum", 99)
            properties.setdefault("step", 1)
            properties.setdefault("prefix", "")
            properties.setdefault("suffix", "")
        elif type_name == "QSlider":
            properties.setdefault("orientation", "horizontal")
            properties.setdefault("value", 0)
            properties.setdefault("minimum", 0)
            properties.setdefault("maximum", 100)
            properties.setdefault("step", 1)
        elif type_name == "QProgressBar":
            properties.setdefault("value", 0)
            properties.setdefault("minimum", 0)
            properties.setdefault("maximum", 100)
            properties.setdefault("text_visible", True)
        elif type_name == "QDoubleSpinBox":
            properties.setdefault("value", 0.0)
            properties.setdefault("minimum", 0.0)
            properties.setdefault("maximum", 99.0)
            properties.setdefault("step", 1.0)
            properties.setdefault("decimals", 2)
            properties.setdefault("prefix", "")
            properties.setdefault("suffix", "")
        elif type_name == "QFrame":
            properties.setdefault("frame_shape", "StyledPanel")
            properties.setdefault("frame_shadow", "Raised")
        elif type_name == "QGroupBox":
            properties.setdefault("title", "")
            properties.setdefault("checkable", False)
            properties.setdefault("checked", False)
        elif type_name == "QTabWidget":
            properties.setdefault("current_index", 0)
            properties.setdefault("tabs_closable", False)
        elif type_name == "QScrollArea":
            properties.setdefault("widget_resizable", True)
        elif type_name == "QSplitter":
            properties.setdefault("orientation", "horizontal")
            properties.setdefault("sizes", [1, 1])
        elif type_name == "QWizard":
            properties.setdefault("window_title", "Wizard")
            properties.setdefault("current_index", 0)
        elif type_name == "TabPage":
            properties.setdefault("title", "Tab")
        elif type_name == "WizardPage":
            properties.setdefault("title", "Page")
            properties.setdefault("subtitle", "")
        if type_name == "QSpinBox":
            minimum = int(properties.get("minimum", 0))
            maximum = int(properties.get("maximum", 99))
            if minimum > maximum:
                maximum = minimum
            step = int(properties.get("step", 1))
            if step <= 0:
                step = 1
            value = int(properties.get("value", 0))
            properties["minimum"] = minimum
            properties["maximum"] = maximum
            properties["step"] = step
            properties["value"] = max(minimum, min(value, maximum))
            properties["prefix"] = str(properties.get("prefix", ""))
            properties["suffix"] = str(properties.get("suffix", ""))
        if type_name == "QSlider":
            orientation = str(properties.get("orientation", "horizontal")).strip().lower()
            if orientation not in {"horizontal", "vertical"}:
                orientation = "horizontal"
            minimum = int(properties.get("minimum", 0))
            maximum = int(properties.get("maximum", 100))
            if minimum > maximum:
                maximum = minimum
            step = int(properties.get("step", 1))
            if step <= 0:
                step = 1
            value = int(properties.get("value", 0))
            properties["orientation"] = orientation
            properties["minimum"] = minimum
            properties["maximum"] = maximum
            properties["step"] = step
            properties["value"] = max(minimum, min(value, maximum))
        if type_name == "QListWidget":
            raw_items = properties.get("items", [])
            if isinstance(raw_items, list):
                items = [str(item) for item in raw_items]
            elif isinstance(raw_items, tuple):
                items = [str(item) for item in raw_items]
            elif raw_items in {None, ""}:
                items = []
            else:
                items = [str(raw_items)]
            current_row = int(properties.get("current_row", -1))
            current_text = str(properties.get("current_text", ""))
            if current_row < -1:
                current_row = -1
            if not items:
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
            properties["items"] = items
            properties["current_row"] = current_row
            properties["current_text"] = current_text
        if type_name == "QListView":
            raw_items = properties.get("model_items", [])
            if isinstance(raw_items, (list, tuple)):
                model_items = [str(item) for item in raw_items]
            elif raw_items in {None, ""}:
                model_items = []
            else:
                model_items = [str(raw_items)]
            properties["model_items"] = model_items
        if type_name == "QTreeView":
            raw_headers = properties.get("header_labels", [])
            if isinstance(raw_headers, (list, tuple)):
                header_labels = [str(item) for item in raw_headers]
            elif raw_headers in {None, ""}:
                header_labels = []
            else:
                header_labels = [str(raw_headers)]
            properties["header_labels"] = header_labels
        if type_name == "QTableView":
            column_count = int(properties.get("column_count", 3))
            if column_count < 0:
                column_count = 0
            raw_headers = properties.get("header_labels", [])
            if isinstance(raw_headers, (list, tuple)):
                header_labels = [str(item) for item in raw_headers]
            elif raw_headers in {None, ""}:
                header_labels = []
            else:
                header_labels = [str(raw_headers)]
            properties["column_count"] = column_count
            properties["header_labels"] = header_labels[:column_count]
        if type_name == "QTableWidget":
            row_count = int(properties.get("row_count", 3))
            column_count = int(properties.get("column_count", 3))
            if row_count < 0:
                row_count = 0
            if column_count < 0:
                column_count = 0
            raw_horizontal = properties.get("horizontal_headers", [])
            if isinstance(raw_horizontal, (list, tuple)):
                horizontal_headers = [str(item) for item in raw_horizontal]
            elif raw_horizontal in {None, ""}:
                horizontal_headers = []
            else:
                horizontal_headers = [str(raw_horizontal)]
            raw_vertical = properties.get("vertical_headers", [])
            if isinstance(raw_vertical, (list, tuple)):
                vertical_headers = [str(item) for item in raw_vertical]
            elif raw_vertical in {None, ""}:
                vertical_headers = []
            else:
                vertical_headers = [str(raw_vertical)]
            raw_cells = properties.get("cell_values", [])
            cell_values: list[list[str]] = []
            if isinstance(raw_cells, (list, tuple)):
                for raw_row in raw_cells[:row_count]:
                    if isinstance(raw_row, (list, tuple)):
                        normalized_row = [str(item) for item in raw_row[:column_count]]
                    elif raw_row in {None, ""}:
                        normalized_row = []
                    else:
                        normalized_row = [str(raw_row)][:column_count]
                    cell_values.append(normalized_row)
            properties["row_count"] = row_count
            properties["column_count"] = column_count
            properties["horizontal_headers"] = horizontal_headers[:column_count]
            properties["vertical_headers"] = vertical_headers[:row_count]
            properties["cell_values"] = cell_values
        if type_name == "QTreeWidget":
            column_count = int(properties.get("column_count", 1))
            if column_count < 0:
                column_count = 0
            raw_headers = properties.get("header_labels", [])
            if isinstance(raw_headers, (list, tuple)):
                header_labels = [str(item) for item in raw_headers]
            elif raw_headers in {None, ""}:
                header_labels = []
            else:
                header_labels = [str(raw_headers)]
            raw_tree_items = properties.get("tree_items", [])
            properties["column_count"] = column_count
            properties["header_labels"] = [] if column_count == 0 else header_labels[:column_count]
            properties["tree_items"] = PythonImporter._normalize_tree_widget_items(raw_tree_items, column_count)
        if type_name == "QDateEdit":
            minimum_date = normalize_date_string(str(properties.get("minimum_date", "1900-01-01")), "1900-01-01")
            maximum_date = normalize_date_string(str(properties.get("maximum_date", "2100-12-31")), "2100-12-31")
            minimum_parsed = parse_date_string(minimum_date)
            maximum_parsed = parse_date_string(maximum_date)
            if minimum_parsed is None or maximum_parsed is None:
                self._raise_diagnostic(
                    "QDateEdit importer requires valid fallback dates.",
                    stage="normalize_properties",
                    pattern="YYYY-MM-DD",
                )
            if minimum_parsed > maximum_parsed:
                maximum_parsed = minimum_parsed
            current_date = normalize_date_string(str(properties.get("date", "2026-01-01")), "2026-01-01")
            current_parsed = parse_date_string(current_date)
            if current_parsed is None:
                current_parsed = minimum_parsed
            if current_parsed < minimum_parsed:
                current_parsed = minimum_parsed
            if current_parsed > maximum_parsed:
                current_parsed = maximum_parsed
            properties["minimum_date"] = format_date_string(minimum_parsed)
            properties["maximum_date"] = format_date_string(maximum_parsed)
            properties["date"] = format_date_string(current_parsed)
        if type_name == "QCalendarWidget":
            minimum_date = normalize_date_string(str(properties.get("minimum_date", "1900-01-01")), "1900-01-01")
            maximum_date = normalize_date_string(str(properties.get("maximum_date", "2100-12-31")), "2100-12-31")
            minimum_parsed = parse_date_string(minimum_date)
            maximum_parsed = parse_date_string(maximum_date)
            if minimum_parsed is None or maximum_parsed is None:
                self._raise_diagnostic(
                    "QCalendarWidget importer requires valid fallback dates.",
                    stage="normalize_properties",
                    pattern="YYYY-MM-DD",
                )
            if minimum_parsed > maximum_parsed:
                maximum_parsed = minimum_parsed
            selected_date = normalize_date_string(str(properties.get("selected_date", "2026-01-01")), "2026-01-01")
            selected_parsed = parse_date_string(selected_date)
            if selected_parsed is None:
                selected_parsed = minimum_parsed
            if selected_parsed < minimum_parsed:
                selected_parsed = minimum_parsed
            if selected_parsed > maximum_parsed:
                selected_parsed = maximum_parsed
            properties["minimum_date"] = format_date_string(minimum_parsed)
            properties["maximum_date"] = format_date_string(maximum_parsed)
            properties["selected_date"] = format_date_string(selected_parsed)
        if type_name == "QFontComboBox":
            properties["current_font_family"] = str(properties.get("current_font_family", ""))
        if type_name == "QKeySequenceEdit":
            properties["key_sequence"] = str(properties.get("key_sequence", ""))
        if type_name == "QDial":
            minimum = int(properties.get("minimum", 0))
            maximum = int(properties.get("maximum", 100))
            if minimum > maximum:
                maximum = minimum
            step = int(properties.get("step", 1))
            if step < 1:
                step = 1
            value = int(properties.get("value", 0))
            if value < minimum:
                value = minimum
            if value > maximum:
                value = maximum
            properties["minimum"] = minimum
            properties["maximum"] = maximum
            properties["step"] = step
            properties["value"] = value
        if type_name == "QLCDNumber":
            digit_count = int(properties.get("digit_count", 5))
            if digit_count < 1:
                digit_count = 1
            properties["digit_count"] = digit_count
            properties["value"] = int(properties.get("value", 0))
        if type_name == "QTimeEdit":
            minimum_time = normalize_time_string(str(properties.get("minimum_time", "00:00:00")), "00:00:00")
            maximum_time = normalize_time_string(str(properties.get("maximum_time", "23:59:59")), "23:59:59")
            minimum_parsed = parse_time_string(minimum_time)
            maximum_parsed = parse_time_string(maximum_time)
            if minimum_parsed is None or maximum_parsed is None:
                self._raise_diagnostic(
                    "QTimeEdit importer requires valid fallback times.",
                    stage="normalize_properties",
                    pattern="HH:MM:SS",
                )
            if minimum_parsed > maximum_parsed:
                maximum_parsed = minimum_parsed
            current_time = normalize_time_string(str(properties.get("time", "12:00:00")), "12:00:00")
            current_parsed = parse_time_string(current_time)
            if current_parsed is None:
                current_parsed = minimum_parsed
            if current_parsed < minimum_parsed:
                current_parsed = minimum_parsed
            if current_parsed > maximum_parsed:
                current_parsed = maximum_parsed
            properties["minimum_time"] = format_time_string(minimum_parsed)
            properties["maximum_time"] = format_time_string(maximum_parsed)
            properties["time"] = format_time_string(current_parsed)
        if type_name == "QDateTimeEdit":
            minimum_datetime = normalize_datetime_string(
                str(properties.get("minimum_datetime", "1900-01-01 00:00:00")),
                "1900-01-01 00:00:00",
            )
            maximum_datetime = normalize_datetime_string(
                str(properties.get("maximum_datetime", "2100-12-31 23:59:59")),
                "2100-12-31 23:59:59",
            )
            minimum_parsed = parse_datetime_string(minimum_datetime)
            maximum_parsed = parse_datetime_string(maximum_datetime)
            if minimum_parsed is None or maximum_parsed is None:
                self._raise_diagnostic(
                    "QDateTimeEdit importer requires valid fallback datetimes.",
                    stage="normalize_properties",
                    pattern="YYYY-MM-DD HH:MM:SS",
                )
            if minimum_parsed > maximum_parsed:
                maximum_parsed = minimum_parsed
            current_datetime = normalize_datetime_string(
                str(properties.get("datetime", "2026-01-01 12:00:00")),
                "2026-01-01 12:00:00",
            )
            current_parsed = parse_datetime_string(current_datetime)
            if current_parsed is None:
                current_parsed = minimum_parsed
            if current_parsed < minimum_parsed:
                current_parsed = minimum_parsed
            if current_parsed > maximum_parsed:
                current_parsed = maximum_parsed
            properties["minimum_datetime"] = format_datetime_string(minimum_parsed)
            properties["maximum_datetime"] = format_datetime_string(maximum_parsed)
            properties["datetime"] = format_datetime_string(current_parsed)
        if type_name == "QProgressBar":
            minimum = int(properties.get("minimum", 0))
            maximum = int(properties.get("maximum", 100))
            if minimum > maximum:
                maximum = minimum
            value = int(properties.get("value", 0))
            properties["minimum"] = minimum
            properties["maximum"] = maximum
            properties["value"] = max(minimum, min(value, maximum))
            properties["text_visible"] = bool(properties.get("text_visible", True))
        if type_name == "QTextEdit":
            properties["text"] = str(properties.get("text", ""))
            properties["placeholder"] = str(properties.get("placeholder", ""))
            properties["read_only"] = bool(properties.get("read_only", False))
        if type_name == "QPlainTextEdit":
            properties["text"] = str(properties.get("text", ""))
            properties["placeholder"] = str(properties.get("placeholder", ""))
            properties["read_only"] = bool(properties.get("read_only", False))
        if type_name == "QDoubleSpinBox":
            minimum = float(properties.get("minimum", 0.0))
            maximum = float(properties.get("maximum", 99.0))
            if minimum > maximum:
                maximum = minimum
            step = float(properties.get("step", 1.0))
            if step <= 0:
                step = 1.0
            decimals = int(properties.get("decimals", 2))
            if decimals < 0:
                decimals = 0
            if decimals > 10:
                decimals = 10
            value = float(properties.get("value", 0.0))
            properties["minimum"] = minimum
            properties["maximum"] = maximum
            properties["step"] = step
            properties["decimals"] = decimals
            properties["value"] = max(minimum, min(value, maximum))
            properties["prefix"] = str(properties.get("prefix", ""))
            properties["suffix"] = str(properties.get("suffix", ""))
        return properties

    @staticmethod
    def _extract_call(statement: ast.stmt) -> ast.Call | None:
        if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call):
            return statement.value
        return None

    @staticmethod
    def _extract_parent_ref_from_creation(call: ast.Call) -> str | None:
        if not call.args:
            return None
        return PythonImporter._ref_name_from_expr(call.args[0])

    @staticmethod
    def _call_target_ref(call: ast.Call) -> str | None:
        if not isinstance(call.func, ast.Attribute):
            return None
        return PythonImporter._ref_name_from_expr(call.func.value)

    @staticmethod
    def _call_method_name(call: ast.Call) -> str | None:
        if not isinstance(call.func, ast.Attribute):
            return None
        return call.func.attr

    @staticmethod
    def _name_from_expr(node: ast.AST) -> str | None:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            prefix = PythonImporter._name_from_expr(node.value)
            if prefix:
                return f"{prefix}.{node.attr}"
            return node.attr
        return None

    @staticmethod
    def _is_self_ref(node: ast.AST) -> bool:
        return isinstance(node, ast.Name) and node.id == "self"

    @staticmethod
    def _ref_name_from_expr(node: ast.AST) -> str | None:
        if isinstance(node, ast.Name):
            return "self" if node.id == "self" else node.id
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "self":
            return node.attr
        return None

    @staticmethod
    def _string_value(node: ast.AST) -> str | None:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        return None

    @staticmethod
    def _bool_value(node: ast.AST, default: bool) -> bool:
        if isinstance(node, ast.Constant) and isinstance(node.value, bool):
            return node.value
        return default

    @staticmethod
    def _int_value(node: ast.AST, default: int) -> int:
        if isinstance(node, ast.Constant) and isinstance(node.value, int):
            return int(node.value)
        if (
            isinstance(node, ast.UnaryOp)
            and isinstance(node.op, ast.USub)
            and isinstance(node.operand, ast.Constant)
            and isinstance(node.operand.value, int)
        ):
            return -int(node.operand.value)
        return default

    @staticmethod
    def _float_value(node: ast.AST, default: float) -> float:
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if (
            isinstance(node, ast.UnaryOp)
            and isinstance(node.op, ast.USub)
            and isinstance(node.operand, ast.Constant)
            and isinstance(node.operand.value, (int, float))
        ):
            return -float(node.operand.value)
        return default

    @staticmethod
    def _numeric_value(node: ast.AST, default: int | float) -> int | float:
        if isinstance(default, float):
            return PythonImporter._float_value(node, default)
        return PythonImporter._int_value(node, int(default))

    @staticmethod
    def _string_list_value(node: ast.AST) -> list[str]:
        if isinstance(node, (ast.List, ast.Tuple)):
            values: list[str] = []
            for item in node.elts:
                if isinstance(item, ast.Constant) and isinstance(item.value, str):
                    values.append(item.value)
            return values
        return []

    @staticmethod
    def _int_list_value(node: ast.AST) -> list[int]:
        if isinstance(node, (ast.List, ast.Tuple)):
            values: list[int] = []
            for item in node.elts:
                if isinstance(item, ast.Constant) and isinstance(item.value, int):
                    values.append(int(item.value))
            return values
        return []

    @staticmethod
    def _parse_qdate_call(node: ast.AST) -> str | None:
        if not isinstance(node, ast.Call):
            return None
        name = PythonImporter._name_from_expr(node.func)
        if name != "QDate" or len(node.args) != 3:
            return None
        year = PythonImporter._int_value(node.args[0], -1)
        month = PythonImporter._int_value(node.args[1], -1)
        day = PythonImporter._int_value(node.args[2], -1)
        parsed = parse_date_string(f"{year:04d}-{month:02d}-{day:02d}")
        if parsed is None:
            return None
        return format_date_string(parsed)

    @staticmethod
    def _parse_qtime_call(node: ast.AST) -> str | None:
        if not isinstance(node, ast.Call):
            return None
        name = PythonImporter._name_from_expr(node.func)
        if name != "QTime" or len(node.args) != 3:
            return None
        hour = PythonImporter._int_value(node.args[0], -1)
        minute = PythonImporter._int_value(node.args[1], -1)
        second = PythonImporter._int_value(node.args[2], -1)
        parsed = parse_time_string(f"{hour:02d}:{minute:02d}:{second:02d}")
        if parsed is None:
            return None
        return format_time_string(parsed)

    @staticmethod
    def _parse_qdatetime_call(node: ast.AST) -> str | None:
        if not isinstance(node, ast.Call):
            return None
        name = PythonImporter._name_from_expr(node.func)
        if name != "QDateTime" or len(node.args) != 2:
            return None
        date_part = PythonImporter._parse_qdate_call(node.args[0])
        time_part = PythonImporter._parse_qtime_call(node.args[1])
        if date_part is None or time_part is None:
            return None
        parsed = parse_datetime_string(f"{date_part} {time_part}")
        if parsed is None:
            return None
        return format_datetime_string(parsed)

    @staticmethod
    def _parse_qfont_call(node: ast.AST) -> str | None:
        if not isinstance(node, ast.Call):
            return None
        name = PythonImporter._name_from_expr(node.func)
        if name != "QFont":
            return None
        if len(node.args) != 1:
            return None
        return PythonImporter._string_value(node.args[0]) or ""

    @staticmethod
    def _parse_qkeysequence_call(node: ast.AST) -> str | None:
        if not isinstance(node, ast.Call):
            return None
        name = PythonImporter._name_from_expr(node.func)
        if name != "QKeySequence":
            return None
        if len(node.args) != 1:
            return None
        return PythonImporter._string_value(node.args[0]) or ""

    @staticmethod
    def _parse_qtablewidgetitem_text(node: ast.AST) -> str | None:
        if not isinstance(node, ast.Call):
            return None
        name = PythonImporter._name_from_expr(node.func)
        if name != "QTableWidgetItem":
            return None
        if len(node.args) != 1:
            return None
        return PythonImporter._string_value(node.args[0]) or ""

    @staticmethod
    def _parse_qtreewidgetitem_data(node: ast.AST) -> dict[str, object] | None:
        if not isinstance(node, ast.Call):
            return None
        name = PythonImporter._name_from_expr(node.func)
        if name != "QTreeWidgetItem":
            return None
        if len(node.args) != 1:
            return None
        texts = PythonImporter._string_list_value(node.args[0])
        return {
            "texts": texts,
            "children": [],
        }

    @staticmethod
    def _build_tree_widget_items(
        root_refs: list[str],
        tree_widget_items: dict[str, dict[str, object]],
    ) -> list[dict[str, object]]:
        built_items: list[dict[str, object]] = []
        for root_ref in root_refs:
            item = PythonImporter._build_tree_widget_item(root_ref, tree_widget_items)
            if item is not None:
                built_items.append(item)
        return built_items

    @staticmethod
    def _build_tree_widget_item(
        item_ref: str,
        tree_widget_items: dict[str, dict[str, object]],
    ) -> dict[str, object] | None:
        item_data = tree_widget_items.get(item_ref)
        if item_data is None:
            return None
        texts = item_data.get("texts", [])
        children_refs = item_data.get("children", [])
        built_children: list[dict[str, object]] = []
        if isinstance(children_refs, list):
            for child_ref in children_refs:
                if not isinstance(child_ref, str):
                    continue
                child_item = PythonImporter._build_tree_widget_item(child_ref, tree_widget_items)
                if child_item is not None:
                    built_children.append(child_item)
        return {
            "texts": [str(text) for text in texts] if isinstance(texts, list) else [],
            "children": built_children,
        }

    @staticmethod
    def _normalize_tree_widget_items(
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
            children = PythonImporter._normalize_tree_widget_items(raw_children, column_count)
            normalized_items.append(
                {
                    "texts": texts,
                    "children": children,
                }
            )
        return normalized_items

    @staticmethod
    def _orientation_value(node: ast.AST) -> str:
        name = PythonImporter._name_from_expr(node)
        if name and name.endswith("Vertical"):
            return "vertical"
        return "horizontal"

    @staticmethod
    def _frame_shape_value(node: ast.AST) -> str:
        name = PythonImporter._name_from_expr(node)
        if not name:
            return "StyledPanel"
        return name.split(".")[-1]

    @staticmethod
    def _frame_shadow_value(node: ast.AST) -> str:
        name = PythonImporter._name_from_expr(node)
        if not name:
            return "Raised"
        return name.split(".")[-1]

    @staticmethod
    def _next_special_order(
        parsed_entities: dict[str, ParsedEntity],
        parent_ref: str,
        role: str,
    ) -> int:
        orders = [
            entity.special_order
            for entity in parsed_entities.values()
            if entity.special_parent_ref == parent_ref and entity.internal_role == role and entity.special_order is not None
        ]
        return len(orders)


Importer = PythonImporter
