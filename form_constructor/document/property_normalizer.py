from __future__ import annotations

from form_constructor.document.models import EntityModel
from form_constructor.utils.date_utils import format_date_string, normalize_date_string, parse_date_string
from form_constructor.utils.datetime_utils import format_datetime_string, normalize_datetime_string, parse_datetime_string
from form_constructor.utils.time_utils import format_time_string, normalize_time_string, parse_time_string


class WidgetPropertyNormalizer:
    def normalize(
        self,
        entity: EntityModel,
        *,
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
        entity.properties["display_format"] = str(entity.properties.get("display_format", "yyyy-MM-dd")).strip() or "yyyy-MM-dd"

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
        entity.properties["display_format"] = str(entity.properties.get("display_format", "HH:mm:ss")).strip() or "HH:mm:ss"

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
        entity.properties["display_format"] = (
            str(entity.properties.get("display_format", "yyyy-MM-dd HH:mm:ss")).strip()
            or "yyyy-MM-dd HH:mm:ss"
        )

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
