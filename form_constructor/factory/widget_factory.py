from PySide6.QtCore import QDate, QDateTime, QStringListModel, QTime, Qt
from PySide6.QtGui import QFont, QKeySequence, QStandardItemModel
from PySide6.QtWidgets import (
    QCheckBox,
    QCalendarWidget,
    QComboBox,
    QDateEdit,
    QDateTimeEdit,
    QDial,
    QDoubleSpinBox,
    QFrame,
    QFontComboBox,
    QGroupBox,
    QKeySequenceEdit,
    QLabel,
    QLCDNumber,
    QLineEdit,
    QListView,
    QListWidget,
    QTableView,
    QTableWidget,
    QTreeView,
    QTreeWidget,
    QTreeWidgetItem,
    QTableWidgetItem,
    QProgressBar,
    QPushButton,
    QPlainTextEdit,
    QRadioButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QTimeEdit,
    QTextEdit,
    QWizard,
    QWizardPage,
    QWidget,
)

from form_constructor.document.models import EntityModel


class WidgetFactory:
    def __init__(self) -> None:
        self._constructors = self._build_constructors()
        self._property_appliers = self._build_property_appliers()

    def _build_constructors(self) -> dict[str, type[QWidget]]:
        return {
            "QWidget": QWidget,
            "QFrame": QFrame,
            "QGroupBox": QGroupBox,
            "QLabel": QLabel,
            "QPushButton": QPushButton,
            "QLineEdit": QLineEdit,
            "QCheckBox": QCheckBox,
            "QRadioButton": QRadioButton,
            "QComboBox": QComboBox,
            "QListView": QListView,
            "QListWidget": QListWidget,
            "QTableView": QTableView,
            "QTableWidget": QTableWidget,
            "QTreeView": QTreeView,
            "QTreeWidget": QTreeWidget,
            "QDateEdit": QDateEdit,
            "QDateTimeEdit": QDateTimeEdit,
            "QCalendarWidget": QCalendarWidget,
            "QFontComboBox": QFontComboBox,
            "QKeySequenceEdit": QKeySequenceEdit,
            "QDial": QDial,
            "QLCDNumber": QLCDNumber,
            "QTimeEdit": QTimeEdit,
            "QPlainTextEdit": QPlainTextEdit,
            "QTextEdit": QTextEdit,
            "QProgressBar": QProgressBar,
            "QSlider": QSlider,
            "QDoubleSpinBox": QDoubleSpinBox,
            "QSpinBox": QSpinBox,
            "QScrollArea": QScrollArea,
            "QSplitter": QSplitter,
            "QWizard": QWizard,
            "QTabWidget": QTabWidget,
            "TabPage": QWidget,
            "WizardPage": QWizardPage,
            "ContainerContent": QWidget,
            "SplitterPane": QWidget,
        }

    def _build_property_appliers(self) -> dict[str, object]:
        return {
            "QLabel": self._apply_text_property,
            "QPushButton": self._apply_text_property,
            "QLineEdit": self._apply_line_edit_properties,
            "QPlainTextEdit": self._apply_plain_text_edit_properties,
            "QTextEdit": self._apply_text_edit_properties,
            "QCheckBox": self._apply_checkable_text_properties,
            "QRadioButton": self._apply_checkable_text_properties,
            "QComboBox": self._apply_combo_box_properties,
            "QListView": self._apply_list_view_properties,
            "QListWidget": self._apply_list_widget_properties,
            "QTableView": self._apply_table_view_properties,
            "QTableWidget": self._apply_table_widget_properties,
            "QTreeView": self._apply_tree_view_properties,
            "QTreeWidget": self._apply_tree_widget_properties,
            "QDateEdit": self._apply_date_edit_properties,
            "QDateTimeEdit": self._apply_datetime_edit_properties,
            "QCalendarWidget": self._apply_calendar_widget_properties,
            "QFontComboBox": self._apply_font_combo_box_properties,
            "QKeySequenceEdit": self._apply_key_sequence_edit_properties,
            "QDial": self._apply_dial_properties,
            "QLCDNumber": self._apply_lcd_number_properties,
            "QTimeEdit": self._apply_time_edit_properties,
            "QProgressBar": self._apply_progress_bar_properties,
            "QSlider": self._apply_slider_properties,
            "QDoubleSpinBox": self._apply_double_spin_box_properties,
            "QSpinBox": self._apply_spin_box_properties,
            "QGroupBox": self._apply_group_box_properties,
            "QFrame": self._apply_frame_properties,
            "QScrollArea": self._apply_scroll_area_properties,
            "QSplitter": self._apply_splitter_properties,
            "QWizard": self._apply_wizard_properties,
            "WizardPage": self._apply_wizard_page_properties,
            "QTabWidget": self._apply_tab_widget_properties,
        }

    def create_widget(self, entity: EntityModel, parent: QWidget | None = None) -> QWidget:
        widget_class = self._constructors.get(entity.type)
        if widget_class is None:
            raise ValueError(f"Unsupported entity type: {entity.type}")
        widget = widget_class(parent)
        self.apply_properties(widget, entity)
        return widget

    def apply_properties(self, widget: QWidget, entity: EntityModel) -> None:
        applier = self._property_appliers.get(entity.type)
        if applier is not None:
            applier(widget, entity)

    def apply_geometry(self, widget: QWidget, entity: EntityModel) -> None:
        geometry = entity.geometry
        widget.setGeometry(
            int(geometry["x"]),
            int(geometry["y"]),
            int(geometry["width"]),
            int(geometry["height"]),
        )

    def refresh_widget(self, widget: QWidget, entity: EntityModel) -> None:
        self.apply_properties(widget, entity)

    def _apply_text_property(self, widget: QWidget, entity: EntityModel) -> None:
        widget.setText(str(entity.properties.get("text", "")))

    def _apply_line_edit_properties(self, widget: QLineEdit, entity: EntityModel) -> None:
        widget.setText(str(entity.properties.get("text", "")))
        widget.setPlaceholderText(str(entity.properties.get("placeholder", "")))

    def _apply_text_edit_properties(self, widget: QTextEdit, entity: EntityModel) -> None:
        widget.setReadOnly(bool(entity.properties.get("read_only", False)))
        widget.setPlaceholderText(str(entity.properties.get("placeholder", "")))
        widget.setPlainText(str(entity.properties.get("text", "")))

    def _apply_plain_text_edit_properties(self, widget: QPlainTextEdit, entity: EntityModel) -> None:
        widget.setReadOnly(bool(entity.properties.get("read_only", False)))
        widget.setPlaceholderText(str(entity.properties.get("placeholder", "")))
        widget.setPlainText(str(entity.properties.get("text", "")))

    def _apply_checkable_text_properties(self, widget: QWidget, entity: EntityModel) -> None:
        widget.setText(str(entity.properties.get("text", "")))
        widget.setChecked(bool(entity.properties.get("checked", False)))

    def _apply_combo_box_properties(self, widget: QComboBox, entity: EntityModel) -> None:
        widget.clear()
        items = self._normalize_combo_items(entity.properties.get("items", []))
        widget.addItems(items)
        widget.setEditable(bool(entity.properties.get("editable", False)))
        current_index = int(entity.properties.get("current_index", 0))
        if widget.count() > 0:
            widget.setCurrentIndex(max(0, min(current_index, widget.count() - 1)))

    def _apply_list_view_properties(self, widget: QListView, entity: EntityModel) -> None:
        model_items = self._normalize_string_list(entity.properties.get("model_items", []))
        widget.setModel(QStringListModel(model_items, widget))

    def _apply_tree_view_properties(self, widget: QTreeView, entity: EntityModel) -> None:
        header_labels = self._normalize_string_list(entity.properties.get("header_labels", []))
        model = QStandardItemModel(widget)
        model.setHorizontalHeaderLabels(header_labels)
        widget.setModel(model)

    def _apply_table_view_properties(self, widget: QTableView, entity: EntityModel) -> None:
        column_count = max(0, int(entity.properties.get("column_count", 3)))
        header_labels = self._normalize_string_list(entity.properties.get("header_labels", []))
        model = QStandardItemModel(widget)
        model.setColumnCount(column_count)
        model.setHorizontalHeaderLabels(header_labels[:column_count])
        widget.setModel(model)

    def _apply_list_widget_properties(self, widget: QListWidget, entity: EntityModel) -> None:
        normalized_items = self._normalize_string_list(entity.properties.get("items", []))
        current_row = int(entity.properties.get("current_row", -1))
        widget.clear()
        widget.addItems(normalized_items)
        if 0 <= current_row < len(normalized_items):
            widget.setCurrentRow(current_row)
        else:
            widget.clearSelection()
            widget.setCurrentRow(-1)

    def _apply_table_widget_properties(self, widget: QTableWidget, entity: EntityModel) -> None:
        row_count = max(0, int(entity.properties.get("row_count", 3)))
        column_count = max(0, int(entity.properties.get("column_count", 3)))
        horizontal_headers = self._normalize_string_list(entity.properties.get("horizontal_headers", []))
        vertical_headers = self._normalize_string_list(entity.properties.get("vertical_headers", []))

        normalized_horizontal = horizontal_headers[:column_count]
        normalized_vertical = vertical_headers[:row_count]
        cell_values = entity.properties.get("cell_values", [])
        if not isinstance(cell_values, list):
            cell_values = []

        widget.clear()
        widget.setRowCount(row_count)
        widget.setColumnCount(column_count)
        if normalized_horizontal:
            widget.setHorizontalHeaderLabels(normalized_horizontal)
        if normalized_vertical:
            widget.setVerticalHeaderLabels(normalized_vertical)
        for row_index, row_values in enumerate(cell_values[:row_count]):
            if not isinstance(row_values, list):
                continue
            for column_index, cell_value in enumerate(row_values[:column_count]):
                widget.setItem(row_index, column_index, QTableWidgetItem(str(cell_value)))

    def _apply_tree_widget_properties(self, widget: QTreeWidget, entity: EntityModel) -> None:
        column_count = max(0, int(entity.properties.get("column_count", 1)))
        header_labels = self._normalize_string_list(entity.properties.get("header_labels", []))
        tree_items = entity.properties.get("tree_items", [])
        if not isinstance(tree_items, list):
            tree_items = []

        normalized_headers = header_labels[:column_count]
        widget.clear()
        widget.setColumnCount(column_count)
        if normalized_headers:
            widget.setHeaderLabels(normalized_headers)
        for tree_item in tree_items:
            widget.addTopLevelItem(self._build_tree_widget_item(tree_item, column_count))

    def _apply_date_edit_properties(self, widget: QDateEdit, entity: EntityModel) -> None:
        self._apply_date_bounds(
            widget,
            entity,
            current_key="date",
            current_default="2026-01-01",
        )
        widget.setDisplayFormat(str(entity.properties.get("display_format", "yyyy-MM-dd")))

    def _apply_datetime_edit_properties(self, widget: QDateTimeEdit, entity: EntityModel) -> None:
        self._apply_datetime_bounds(
            widget,
            entity,
            current_key="datetime",
            current_default="2026-01-01 12:00:00",
        )
        widget.setDisplayFormat(str(entity.properties.get("display_format", "yyyy-MM-dd HH:mm:ss")))

    def _apply_calendar_widget_properties(self, widget: QCalendarWidget, entity: EntityModel) -> None:
        self._apply_date_bounds(
            widget,
            entity,
            current_key="selected_date",
            current_default="2026-01-01",
            current_setter=widget.setSelectedDate,
        )

    def _apply_font_combo_box_properties(self, widget: QFontComboBox, entity: EntityModel) -> None:
        self._apply_font_family(widget, str(entity.properties.get("current_font_family", "")))

    def _apply_key_sequence_edit_properties(self, widget: QKeySequenceEdit, entity: EntityModel) -> None:
        key_sequence = str(entity.properties.get("key_sequence", ""))
        if not key_sequence:
            widget.clear()
            return
        widget.setKeySequence(QKeySequence(key_sequence))

    def _apply_dial_properties(self, widget: QDial, entity: EntityModel) -> None:
        self._apply_integer_range_properties(widget, entity, default_maximum=100)

    def _apply_lcd_number_properties(self, widget: QLCDNumber, entity: EntityModel) -> None:
        digit_count = int(entity.properties.get("digit_count", 5))
        value = int(entity.properties.get("value", 0))
        widget.setDigitCount(digit_count)
        widget.display(value)

    def _apply_time_edit_properties(self, widget: QTimeEdit, entity: EntityModel) -> None:
        self._apply_time_bounds(
            widget,
            entity,
            current_key="time",
            current_default="12:00:00",
        )
        widget.setDisplayFormat(str(entity.properties.get("display_format", "HH:mm:ss")))

    def _apply_progress_bar_properties(self, widget: QProgressBar, entity: EntityModel) -> None:
        value = int(entity.properties.get("value", 0))
        text_visible = bool(entity.properties.get("text_visible", True))
        self._apply_integer_minimum_maximum(widget, entity, default_maximum=100)
        widget.setValue(value)
        widget.setTextVisible(text_visible)

    def _apply_spin_box_properties(self, widget: QSpinBox, entity: EntityModel) -> None:
        self._apply_integer_range_properties(widget, entity, default_maximum=99)
        widget.setPrefix(str(entity.properties.get("prefix", "")))
        widget.setSuffix(str(entity.properties.get("suffix", "")))

    def _apply_double_spin_box_properties(self, widget: QDoubleSpinBox, entity: EntityModel) -> None:
        decimals = int(entity.properties.get("decimals", 2))
        self._apply_float_range_properties(widget, entity, default_maximum=99.0)
        widget.setDecimals(decimals)
        widget.setPrefix(str(entity.properties.get("prefix", "")))
        widget.setSuffix(str(entity.properties.get("suffix", "")))

    def _apply_slider_properties(self, widget: QSlider, entity: EntityModel) -> None:
        orientation = str(entity.properties.get("orientation", "horizontal")).lower()
        widget.setOrientation(self._map_orientation(orientation))
        self._apply_integer_range_properties(widget, entity, default_maximum=100)

    def _apply_group_box_properties(self, widget: QGroupBox, entity: EntityModel) -> None:
        widget.setTitle(str(entity.properties.get("title", "")))
        widget.setCheckable(bool(entity.properties.get("checkable", False)))
        if widget.isCheckable():
            widget.setChecked(bool(entity.properties.get("checked", False)))

    def _apply_frame_properties(self, widget: QFrame, entity: EntityModel) -> None:
        widget.setFrameShape(self._frame_shape(entity.properties.get("frame_shape")))
        widget.setFrameShadow(self._frame_shadow(entity.properties.get("frame_shadow")))

    def _apply_scroll_area_properties(self, widget: QScrollArea, entity: EntityModel) -> None:
        widget.setWidgetResizable(bool(entity.properties.get("widget_resizable", True)))

    def _apply_splitter_properties(self, widget: QSplitter, entity: EntityModel) -> None:
        orientation = str(entity.properties.get("orientation", "horizontal")).lower()
        widget.setOrientation(self._map_orientation(orientation))
        sizes = self._normalize_splitter_sizes(entity.properties.get("sizes", [1, 1]))
        if sizes is not None:
            widget.setSizes(sizes)

    def _apply_wizard_properties(self, widget: QWizard, entity: EntityModel) -> None:
        widget.setWindowTitle(str(entity.properties.get("window_title", "Wizard")))

    def _apply_wizard_page_properties(self, widget: QWizardPage, entity: EntityModel) -> None:
        widget.setTitle(str(entity.properties.get("title", "")))
        widget.setSubTitle(str(entity.properties.get("subtitle", "")))

    def _apply_tab_widget_properties(self, widget: QTabWidget, entity: EntityModel) -> None:
        widget.setTabsClosable(bool(entity.properties.get("tabs_closable", False)))

    def _frame_shape(self, value) -> QFrame.Shape:
        mapping = {
            "NoFrame": QFrame.Shape.NoFrame,
            "Box": QFrame.Shape.Box,
            "Panel": QFrame.Shape.Panel,
            "StyledPanel": QFrame.Shape.StyledPanel,
            "HLine": QFrame.Shape.HLine,
            "VLine": QFrame.Shape.VLine,
            "WinPanel": QFrame.Shape.WinPanel,
        }
        return mapping.get(str(value), QFrame.Shape.StyledPanel)

    def _frame_shadow(self, value) -> QFrame.Shadow:
        mapping = {
            "Plain": QFrame.Shadow.Plain,
            "Raised": QFrame.Shadow.Raised,
            "Sunken": QFrame.Shadow.Sunken,
        }
        return mapping.get(str(value), QFrame.Shadow.Raised)

    @staticmethod
    def _map_orientation(value: str) -> Qt.Orientation:
        return Qt.Orientation.Vertical if str(value).lower() == "vertical" else Qt.Orientation.Horizontal

    @staticmethod
    def _to_qdate(value: str) -> QDate:
        year, month, day = (int(part) for part in str(value).split("-"))
        return QDate(year, month, day)

    @staticmethod
    def _to_qtime(value: str) -> QTime:
        hour, minute, second = (int(part) for part in str(value).split(":"))
        return QTime(hour, minute, second)

    @staticmethod
    def _to_qdatetime(value: str) -> QDateTime:
        date_part, time_part = str(value).split(" ", 1)
        year, month, day = (int(part) for part in date_part.split("-"))
        hour, minute, second = (int(part) for part in time_part.split(":"))
        return QDateTime(QDate(year, month, day), QTime(hour, minute, second))

    @staticmethod
    def _apply_font_family(widget: QFontComboBox, family_name: str) -> None:
        if not family_name:
            return
        try:
            widget.setCurrentFont(QFont(str(family_name)))
        except Exception:
            return

    def _build_tree_widget_item(
        self,
        item_data: object,
        column_count: int,
    ) -> QTreeWidgetItem:
        if not isinstance(item_data, dict):
            return QTreeWidgetItem([""] * max(0, column_count))
        raw_texts = item_data.get("texts", [])
        if isinstance(raw_texts, list):
            texts = [str(item) for item in raw_texts[:column_count]]
        else:
            texts = []
        item = QTreeWidgetItem(texts)
        raw_children = item_data.get("children", [])
        if isinstance(raw_children, list):
            for child_data in raw_children:
                item.addChild(self._build_tree_widget_item(child_data, column_count))
        return item

    @staticmethod
    def _normalize_string_list(value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item) for item in value]

    @classmethod
    def _normalize_combo_items(cls, value: object) -> list[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return cls._normalize_string_list(value)

    @staticmethod
    def _normalize_splitter_sizes(value: object) -> list[int] | None:
        if not isinstance(value, list) or len(value) != 2:
            return None
        return [max(1, int(size)) for size in value]

    @staticmethod
    def _apply_integer_minimum_maximum(widget: QWidget, entity: EntityModel, default_maximum: int) -> None:
        widget.setMinimum(int(entity.properties.get("minimum", 0)))
        widget.setMaximum(int(entity.properties.get("maximum", default_maximum)))

    @classmethod
    def _apply_integer_range_properties(
        cls,
        widget: QWidget,
        entity: EntityModel,
        default_maximum: int,
    ) -> None:
        cls._apply_integer_minimum_maximum(widget, entity, default_maximum)
        widget.setSingleStep(int(entity.properties.get("step", 1)))
        widget.setValue(int(entity.properties.get("value", 0)))

    @staticmethod
    def _apply_float_range_properties(
        widget: QDoubleSpinBox,
        entity: EntityModel,
        default_maximum: float,
    ) -> None:
        widget.setMinimum(float(entity.properties.get("minimum", 0.0)))
        widget.setMaximum(float(entity.properties.get("maximum", default_maximum)))
        widget.setSingleStep(float(entity.properties.get("step", 1.0)))
        widget.setValue(float(entity.properties.get("value", 0.0)))

    def _apply_date_bounds(
        self,
        widget: QDateEdit | QCalendarWidget,
        entity: EntityModel,
        current_key: str,
        current_default: str,
        current_setter=None,
    ) -> None:
        widget.setMinimumDate(self._to_qdate(str(entity.properties.get("minimum_date", "1900-01-01"))))
        widget.setMaximumDate(self._to_qdate(str(entity.properties.get("maximum_date", "2100-12-31"))))
        target_setter = widget.setDate if current_setter is None else current_setter
        target_setter(self._to_qdate(str(entity.properties.get(current_key, current_default))))

    def _apply_time_bounds(
        self,
        widget: QTimeEdit,
        entity: EntityModel,
        current_key: str,
        current_default: str,
    ) -> None:
        widget.setMinimumTime(self._to_qtime(str(entity.properties.get("minimum_time", "00:00:00"))))
        widget.setMaximumTime(self._to_qtime(str(entity.properties.get("maximum_time", "23:59:59"))))
        widget.setTime(self._to_qtime(str(entity.properties.get(current_key, current_default))))

    def _apply_datetime_bounds(
        self,
        widget: QDateTimeEdit,
        entity: EntityModel,
        current_key: str,
        current_default: str,
    ) -> None:
        widget.setMinimumDateTime(
            self._to_qdatetime(str(entity.properties.get("minimum_datetime", "1900-01-01 00:00:00")))
        )
        widget.setMaximumDateTime(
            self._to_qdatetime(str(entity.properties.get("maximum_datetime", "2100-12-31 23:59:59")))
        )
        widget.setDateTime(self._to_qdatetime(str(entity.properties.get(current_key, current_default))))
