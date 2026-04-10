from __future__ import annotations

import json

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QLineEdit,
    QPlainTextEdit,
    QSpinBox,
    QWidget,
)

from form_constructor.registry.definitions import PropertyDefinition


class PlainTextPropertyEditor(QPlainTextEdit):
    editingFinished = Signal()

    def focusOutEvent(self, event) -> None:
        super().focusOutEvent(event)
        self.editingFinished.emit()


class PropertyEditorFactory:
    def create_editor(self, prop: PropertyDefinition, parent: QWidget | None = None) -> QWidget:
        if prop.allowed_values:
            widget = QComboBox(parent)
            widget.addItems([str(value) for value in prop.allowed_values])
            return self.configure_editor(widget, prop)

        if prop.editor == "checkbox" or prop.data_type == "bool":
            return self.configure_editor(QCheckBox(parent), prop)

        if prop.editor == "spinbox" or prop.data_type == "int":
            widget = QSpinBox(parent)
            widget.setRange(-9999, 9999)
            return self.configure_editor(widget, prop)

        if prop.data_type == "float":
            widget = QDoubleSpinBox(parent)
            widget.setRange(-9999.0, 9999.0)
            widget.setDecimals(3)
            return self.configure_editor(widget, prop)

        if prop.editor in {"multiline", "table_text", "tree_text"}:
            return self.configure_editor(PlainTextPropertyEditor(parent), prop)

        if prop.data_type in {"list[str]", "list[int]", "list[list[str]]", "list[tree_item]"}:
            return self.configure_editor(PlainTextPropertyEditor(parent), prop)

        return self.configure_editor(QLineEdit(parent), prop)

    def configure_editor(self, widget: QWidget, prop: PropertyDefinition) -> QWidget:
        if isinstance(widget, QLineEdit):
            if prop.data_type == "date_string":
                widget.setPlaceholderText("YYYY-MM-DD")
            elif prop.data_type == "time_string":
                widget.setPlaceholderText("HH:MM:SS")
            elif prop.data_type == "datetime_string":
                widget.setPlaceholderText("YYYY-MM-DD HH:MM:SS")
        return widget

    def connect_change(self, widget: QWidget, prop: PropertyDefinition, callback) -> None:
        if isinstance(widget, QComboBox):
            widget.currentTextChanged.connect(lambda _: callback())
            return
        if isinstance(widget, QCheckBox):
            widget.toggled.connect(lambda _: callback())
            return
        if isinstance(widget, (QSpinBox, QDoubleSpinBox)):
            widget.editingFinished.connect(callback)
            return
        if isinstance(widget, PlainTextPropertyEditor):
            widget.editingFinished.connect(callback)
            return
        if isinstance(widget, QLineEdit):
            widget.editingFinished.connect(callback)

    def set_value(self, widget: QWidget, prop: PropertyDefinition, value: object) -> None:
        if isinstance(widget, QCheckBox):
            widget.setChecked(bool(value))
            return

        if isinstance(widget, QComboBox):
            text_value = str(value)
            index = widget.findText(text_value)
            if index < 0:
                widget.addItem(text_value)
                index = widget.findText(text_value)
            widget.setCurrentIndex(max(0, index))
            return

        if isinstance(widget, QSpinBox):
            widget.setValue(int(value))
            return

        if isinstance(widget, QDoubleSpinBox):
            widget.setValue(float(value))
            return

        if isinstance(widget, PlainTextPropertyEditor):
            widget.setPlainText(self._stringify(prop, value))
            return

        if isinstance(widget, QLineEdit):
            widget.setText(self._stringify(prop, value))

    def get_value(self, widget: QWidget, prop: PropertyDefinition) -> object:
        if isinstance(widget, QCheckBox):
            return widget.isChecked()
        if isinstance(widget, QComboBox):
            return widget.currentText()
        if isinstance(widget, QSpinBox):
            return widget.value()
        if isinstance(widget, QDoubleSpinBox):
            return widget.value()
        if isinstance(widget, PlainTextPropertyEditor):
            return self._parse(prop, widget.toPlainText())
        if isinstance(widget, QLineEdit):
            return self._parse(prop, widget.text())
        return None

    def _parse(self, prop: PropertyDefinition, raw_value: str) -> object:
        if prop.data_type == "float":
            return float(raw_value or 0)
        if prop.data_type == "list[str]":
            return [line.strip() for line in raw_value.splitlines() if line.strip()]
        if prop.data_type == "list[int]":
            return [int(line.strip()) for line in raw_value.splitlines() if line.strip()]
        if prop.data_type == "list[list[str]]" or prop.editor == "table_text":
            rows: list[list[str]] = []
            for line in raw_value.splitlines():
                if not line.strip():
                    continue
                rows.append([cell for cell in line.split("\t")])
            return rows
        if prop.data_type == "list[tree_item]" or prop.editor == "tree_text":
            if not raw_value.strip():
                return []
            parsed = json.loads(raw_value)
            return parsed if isinstance(parsed, list) else []
        return raw_value

    def _stringify(self, prop: PropertyDefinition, value: object) -> str:
        if prop.data_type in {"list[str]", "list[int]"} and isinstance(value, list):
            return "\n".join(str(item) for item in value)
        if (prop.data_type == "list[list[str]]" or prop.editor == "table_text") and isinstance(value, list):
            lines: list[str] = []
            for row in value:
                if isinstance(row, list):
                    lines.append("\t".join(str(cell) for cell in row))
            return "\n".join(lines)
        if prop.data_type == "list[tree_item]" or prop.editor == "tree_text":
            if isinstance(value, list):
                return json.dumps(value, ensure_ascii=False, indent=2)
            return "[]"
        return "" if value is None else str(value)
