from __future__ import annotations

from form_constructor.document.models import EntityModel, FormRootModel
from form_constructor.registry.widget_registry import WidgetRegistry
from form_constructor.utils.date_utils import is_valid_date_string, parse_date_string
from form_constructor.utils.datetime_utils import is_valid_datetime_string, parse_datetime_string
from form_constructor.utils.time_utils import is_valid_time_string, parse_time_string


class DocumentValidator:
    def validate(self, document) -> None:
        self.validate_document(document)

    def validate_document(self, document) -> None:
        self._validate_form_root(document.form_root)
        if document.form_root.id in document.entities_by_id:
            raise ValueError("Form root id must not appear in entities_by_id.")

        seen_ids = {document.form_root.id}
        for entity_id, entity in document.entities_by_id.items():
            if entity.id != entity_id:
                raise ValueError(f"Entity key '{entity_id}' does not match entity.id '{entity.id}'.")
            if entity.id in seen_ids:
                raise ValueError(f"Duplicate entity id: {entity.id}")
            seen_ids.add(entity.id)
            self.validate_entity(entity, document.widget_registry)
            if entity.parent_id != document.form_root.id and entity.parent_id not in document.entities_by_id:
                raise ValueError(f"Entity '{entity.id}' points to unknown parent '{entity.parent_id}'.")

        self._validate_parent_child_relationships(document)
        self._validate_child_orders(document)
        self._validate_special_container_invariants(document)

    def validate_entity(self, entity: EntityModel, registry: WidgetRegistry) -> None:
        definition = registry.get_type(entity.type)
        if definition is None:
            raise ValueError(f"Unknown entity type: {entity.type}")
        if not entity.id:
            raise ValueError("Entity id must not be empty.")
        if not entity.name:
            raise ValueError(f"Entity '{entity.id}' must have a non-empty name.")
        if entity.order < 0:
            raise ValueError(f"Entity '{entity.id}' has negative order.")
        self._validate_geometry(entity.id, entity.geometry, allow_zero_size=definition.editor_kind == "internal")
        schema_by_name = {prop.name: prop for prop in registry.get_property_schema(entity.type)}
        for property_name, property_definition in schema_by_name.items():
            if property_definition.required and property_name not in entity.properties:
                raise ValueError(
                    f"Entity '{entity.id}' is missing required property '{property_name}'."
                )
        for property_name in entity.properties:
            if property_name not in schema_by_name:
                continue
            property_definition = schema_by_name[property_name]
            self._validate_property_value(
                entity.id,
                property_name,
                entity.properties[property_name],
                property_definition.data_type,
            )
            if property_definition.allowed_values:
                self._validate_allowed_values(
                    entity.id,
                    property_name,
                    entity.properties[property_name],
                    property_definition.allowed_values,
                )

    def validate_parent_child(
        self,
        parent_type: str,
        child_type: str,
        registry: WidgetRegistry,
    ) -> None:
        if not registry.can_parent(parent_type, child_type):
            raise ValueError(f"Parent '{parent_type}' cannot contain '{child_type}'.")

    def _validate_form_root(self, form_root: FormRootModel) -> None:
        allowed_root_widget_types = {"QWidget", "QDialog"}
        if form_root.id != "form_root":
            raise ValueError("Form root id must be 'form_root'.")
        if form_root.type != "FormRoot":
            raise ValueError("Form root type must be 'FormRoot'.")
        if not form_root.name:
            raise ValueError("Form root must have a non-empty name.")
        if form_root.width <= 0 or form_root.height <= 0:
            raise ValueError("Form size must be positive.")
        if not form_root.root_widget_type:
            raise ValueError("Form root must define root_widget_type.")
        if form_root.root_widget_type not in allowed_root_widget_types:
            raise ValueError(
                f"Form root has unsupported root_widget_type '{form_root.root_widget_type}'."
            )

    def _validate_parent_child_relationships(self, document) -> None:
        for entity in document.entities_by_id.values():
            parent_type = document.get_parent_type(entity.parent_id)
            self.validate_parent_child(parent_type, entity.type, document.widget_registry)

    def _validate_child_orders(self, document) -> None:
        parent_ids = [document.form_root.id, *document.entities_by_id.keys()]
        for parent_id in parent_ids:
            children = document.get_children(parent_id)
            expected_orders = list(range(len(children)))
            actual_orders = [child.order for child in children]
            if actual_orders != expected_orders:
                raise ValueError(
                    f"Children of '{parent_id}' have inconsistent order: {actual_orders}."
                )

    def _validate_special_container_invariants(self, document) -> None:
        for entity in document.entities_by_id.values():
            if entity.type == "QTabWidget":
                children = document.get_children(entity.id)
                if not children:
                    raise ValueError(f"QTabWidget '{entity.id}' must have at least one TabPage.")
                if any(child.type != "TabPage" for child in children):
                    raise ValueError(f"QTabWidget '{entity.id}' must contain only TabPage children.")
                current_index = int(entity.properties.get("current_index", 0))
                if not 0 <= current_index < len(children):
                    raise ValueError(f"QTabWidget '{entity.id}' current_index is out of range.")
            elif entity.type == "QScrollArea":
                children = document.get_children(entity.id)
                if len(children) != 1 or children[0].type != "ContainerContent":
                    raise ValueError(
                        f"QScrollArea '{entity.id}' must contain exactly one ContainerContent."
                    )
            elif entity.type == "QSplitter":
                children = document.get_children(entity.id)
                if len(children) != 2 or any(child.type != "SplitterPane" for child in children):
                    raise ValueError(
                        f"QSplitter '{entity.id}' must contain exactly two SplitterPane children."
                    )
                sizes = entity.properties.get("sizes", [])
                if not isinstance(sizes, list) or len(sizes) != 2:
                    raise ValueError(f"QSplitter '{entity.id}' must define exactly two sizes.")
            elif entity.type == "QWizard":
                children = document.get_children(entity.id)
                if not children:
                    raise ValueError(f"QWizard '{entity.id}' must have at least one WizardPage.")
                if any(child.type != "WizardPage" for child in children):
                    raise ValueError(f"QWizard '{entity.id}' must contain only WizardPage children.")
                current_index = int(entity.properties.get("current_index", 0))
                if not 0 <= current_index < len(children):
                    raise ValueError(f"QWizard '{entity.id}' current_index is out of range.")
            elif entity.type == "QComboBox":
                items = entity.properties.get("items", [])
                if not isinstance(items, list):
                    raise ValueError(f"QComboBox '{entity.id}' items must be list[str].")
                current_index = int(entity.properties.get("current_index", 0))
                if items:
                    if not 0 <= current_index < len(items):
                        raise ValueError(f"QComboBox '{entity.id}' current_index is out of range.")
                elif current_index != 0:
                    raise ValueError(f"QComboBox '{entity.id}' current_index must be 0 when items are empty.")
            elif entity.type == "QListWidget":
                items = entity.properties.get("items", [])
                current_text = entity.properties.get("current_text", "")
                if not isinstance(items, list) or any(not isinstance(item, str) for item in items):
                    raise ValueError(f"QListWidget '{entity.id}' items must be list[str].")
                if not isinstance(current_text, str):
                    raise ValueError(f"QListWidget '{entity.id}' current_text must be str.")
                current_row = int(entity.properties.get("current_row", -1))
                if items:
                    if current_row != -1 and not 0 <= current_row < len(items):
                        raise ValueError(f"QListWidget '{entity.id}' current_row is out of range.")
                    if current_row == -1:
                        if current_text != "":
                            raise ValueError(
                                f"QListWidget '{entity.id}' current_text must be empty when nothing is selected."
                            )
                    elif current_text != items[current_row]:
                        raise ValueError(
                            f"QListWidget '{entity.id}' current_text must match selected item text."
                        )
                elif current_row != -1:
                    raise ValueError(f"QListWidget '{entity.id}' current_row must be -1 when items are empty.")
                elif current_text != "":
                    raise ValueError(f"QListWidget '{entity.id}' current_text must be empty when items are empty.")
            elif entity.type == "QListView":
                model_items = entity.properties.get("model_items", [])
                if not isinstance(model_items, list) or any(not isinstance(item, str) for item in model_items):
                    raise ValueError(f"QListView '{entity.id}' model_items must be list[str].")
            elif entity.type == "QTreeView":
                header_labels = entity.properties.get("header_labels", [])
                if not isinstance(header_labels, list) or any(not isinstance(item, str) for item in header_labels):
                    raise ValueError(f"QTreeView '{entity.id}' header_labels must be list[str].")
            elif entity.type == "QTableView":
                column_count = int(entity.properties.get("column_count", 3))
                header_labels = entity.properties.get("header_labels", [])
                if column_count < 0:
                    raise ValueError(f"QTableView '{entity.id}' column_count must be non-negative.")
                if not isinstance(header_labels, list) or any(not isinstance(item, str) for item in header_labels):
                    raise ValueError(f"QTableView '{entity.id}' header_labels must be list[str].")
                if len(header_labels) > column_count:
                    raise ValueError(f"QTableView '{entity.id}' header_labels cannot exceed column_count.")
            elif entity.type == "QTableWidget":
                row_count = int(entity.properties.get("row_count", 3))
                column_count = int(entity.properties.get("column_count", 3))
                horizontal_headers = entity.properties.get("horizontal_headers", [])
                vertical_headers = entity.properties.get("vertical_headers", [])
                cell_values = entity.properties.get("cell_values", [])
                if row_count < 0:
                    raise ValueError(f"QTableWidget '{entity.id}' row_count must be non-negative.")
                if column_count < 0:
                    raise ValueError(f"QTableWidget '{entity.id}' column_count must be non-negative.")
                if not isinstance(horizontal_headers, list) or any(not isinstance(item, str) for item in horizontal_headers):
                    raise ValueError(f"QTableWidget '{entity.id}' horizontal_headers must be list[str].")
                if not isinstance(vertical_headers, list) or any(not isinstance(item, str) for item in vertical_headers):
                    raise ValueError(f"QTableWidget '{entity.id}' vertical_headers must be list[str].")
                if len(horizontal_headers) > column_count:
                    raise ValueError(
                        f"QTableWidget '{entity.id}' horizontal_headers cannot exceed column_count."
                    )
                if len(vertical_headers) > row_count:
                    raise ValueError(f"QTableWidget '{entity.id}' vertical_headers cannot exceed row_count.")
                if not isinstance(cell_values, list):
                    raise ValueError(f"QTableWidget '{entity.id}' cell_values must be list[list[str]].")
                if len(cell_values) > row_count:
                    raise ValueError(f"QTableWidget '{entity.id}' cell_values rows cannot exceed row_count.")
                for row in cell_values:
                    if not isinstance(row, list) or any(not isinstance(item, str) for item in row):
                        raise ValueError(f"QTableWidget '{entity.id}' cell_values must be list[list[str]].")
                    if len(row) > column_count:
                        raise ValueError(f"QTableWidget '{entity.id}' cell_values columns cannot exceed column_count.")
            elif entity.type == "QTreeWidget":
                column_count = int(entity.properties.get("column_count", 1))
                header_labels = entity.properties.get("header_labels", [])
                tree_items = entity.properties.get("tree_items", [])
                if column_count < 0:
                    raise ValueError(f"QTreeWidget '{entity.id}' column_count must be non-negative.")
                if not isinstance(header_labels, list) or any(not isinstance(item, str) for item in header_labels):
                    raise ValueError(f"QTreeWidget '{entity.id}' header_labels must be list[str].")
                if len(header_labels) > column_count:
                    raise ValueError(f"QTreeWidget '{entity.id}' header_labels cannot exceed column_count.")
                self._validate_tree_items(entity.id, tree_items, column_count)
            elif entity.type == "QDateEdit":
                date_value = entity.properties.get("date", "")
                minimum_date = entity.properties.get("minimum_date", "")
                maximum_date = entity.properties.get("maximum_date", "")
                if not isinstance(date_value, str) or not is_valid_date_string(date_value):
                    raise ValueError(f"QDateEdit '{entity.id}' date must be valid YYYY-MM-DD string.")
                if not isinstance(minimum_date, str) or not is_valid_date_string(minimum_date):
                    raise ValueError(f"QDateEdit '{entity.id}' minimum_date must be valid YYYY-MM-DD string.")
                if not isinstance(maximum_date, str) or not is_valid_date_string(maximum_date):
                    raise ValueError(f"QDateEdit '{entity.id}' maximum_date must be valid YYYY-MM-DD string.")
                date_parsed = parse_date_string(date_value)
                minimum_parsed = parse_date_string(minimum_date)
                maximum_parsed = parse_date_string(maximum_date)
                if minimum_parsed is None or maximum_parsed is None or date_parsed is None:
                    raise ValueError(f"QDateEdit '{entity.id}' dates must be parseable.")
                if minimum_parsed > maximum_parsed:
                    raise ValueError(f"QDateEdit '{entity.id}' minimum_date must be <= maximum_date.")
                if date_parsed < minimum_parsed or date_parsed > maximum_parsed:
                    raise ValueError(f"QDateEdit '{entity.id}' date must be inside allowed range.")
            elif entity.type == "QCalendarWidget":
                selected_date = entity.properties.get("selected_date", "")
                minimum_date = entity.properties.get("minimum_date", "")
                maximum_date = entity.properties.get("maximum_date", "")
                if not isinstance(selected_date, str) or not is_valid_date_string(selected_date):
                    raise ValueError(f"QCalendarWidget '{entity.id}' selected_date must be valid YYYY-MM-DD string.")
                if not isinstance(minimum_date, str) or not is_valid_date_string(minimum_date):
                    raise ValueError(f"QCalendarWidget '{entity.id}' minimum_date must be valid YYYY-MM-DD string.")
                if not isinstance(maximum_date, str) or not is_valid_date_string(maximum_date):
                    raise ValueError(f"QCalendarWidget '{entity.id}' maximum_date must be valid YYYY-MM-DD string.")
                selected_parsed = parse_date_string(selected_date)
                minimum_parsed = parse_date_string(minimum_date)
                maximum_parsed = parse_date_string(maximum_date)
                if minimum_parsed is None or maximum_parsed is None or selected_parsed is None:
                    raise ValueError(f"QCalendarWidget '{entity.id}' dates must be parseable.")
                if minimum_parsed > maximum_parsed:
                    raise ValueError(f"QCalendarWidget '{entity.id}' minimum_date must be <= maximum_date.")
                if selected_parsed < minimum_parsed or selected_parsed > maximum_parsed:
                    raise ValueError(f"QCalendarWidget '{entity.id}' selected_date must be inside allowed range.")
            elif entity.type == "QTimeEdit":
                time_value = entity.properties.get("time", "")
                minimum_time = entity.properties.get("minimum_time", "")
                maximum_time = entity.properties.get("maximum_time", "")
                if not isinstance(time_value, str) or not is_valid_time_string(time_value):
                    raise ValueError(f"QTimeEdit '{entity.id}' time must be valid HH:MM:SS string.")
                if not isinstance(minimum_time, str) or not is_valid_time_string(minimum_time):
                    raise ValueError(f"QTimeEdit '{entity.id}' minimum_time must be valid HH:MM:SS string.")
                if not isinstance(maximum_time, str) or not is_valid_time_string(maximum_time):
                    raise ValueError(f"QTimeEdit '{entity.id}' maximum_time must be valid HH:MM:SS string.")
                time_parsed = parse_time_string(time_value)
                minimum_parsed = parse_time_string(minimum_time)
                maximum_parsed = parse_time_string(maximum_time)
                if minimum_parsed is None or maximum_parsed is None or time_parsed is None:
                    raise ValueError(f"QTimeEdit '{entity.id}' times must be parseable.")
                if minimum_parsed > maximum_parsed:
                    raise ValueError(f"QTimeEdit '{entity.id}' minimum_time must be <= maximum_time.")
                if time_parsed < minimum_parsed or time_parsed > maximum_parsed:
                    raise ValueError(f"QTimeEdit '{entity.id}' time must be inside allowed range.")
            elif entity.type == "QDateTimeEdit":
                datetime_value = entity.properties.get("datetime", "")
                minimum_datetime = entity.properties.get("minimum_datetime", "")
                maximum_datetime = entity.properties.get("maximum_datetime", "")
                if not isinstance(datetime_value, str) or not is_valid_datetime_string(datetime_value):
                    raise ValueError(
                        f"QDateTimeEdit '{entity.id}' datetime must be valid YYYY-MM-DD HH:MM:SS string."
                    )
                if not isinstance(minimum_datetime, str) or not is_valid_datetime_string(minimum_datetime):
                    raise ValueError(
                        f"QDateTimeEdit '{entity.id}' minimum_datetime must be valid YYYY-MM-DD HH:MM:SS string."
                    )
                if not isinstance(maximum_datetime, str) or not is_valid_datetime_string(maximum_datetime):
                    raise ValueError(
                        f"QDateTimeEdit '{entity.id}' maximum_datetime must be valid YYYY-MM-DD HH:MM:SS string."
                    )
                datetime_parsed = parse_datetime_string(datetime_value)
                minimum_parsed = parse_datetime_string(minimum_datetime)
                maximum_parsed = parse_datetime_string(maximum_datetime)
                if minimum_parsed is None or maximum_parsed is None or datetime_parsed is None:
                    raise ValueError(f"QDateTimeEdit '{entity.id}' datetimes must be parseable.")
                if minimum_parsed > maximum_parsed:
                    raise ValueError(f"QDateTimeEdit '{entity.id}' minimum_datetime must be <= maximum_datetime.")
                if datetime_parsed < minimum_parsed or datetime_parsed > maximum_parsed:
                    raise ValueError(f"QDateTimeEdit '{entity.id}' datetime must be inside allowed range.")
            elif entity.type == "QSpinBox":
                minimum = int(entity.properties.get("minimum", 0))
                maximum = int(entity.properties.get("maximum", 99))
                value = int(entity.properties.get("value", 0))
                step = int(entity.properties.get("step", 1))
                if minimum > maximum:
                    raise ValueError(f"QSpinBox '{entity.id}' minimum must be <= maximum.")
                if not minimum <= value <= maximum:
                    raise ValueError(f"QSpinBox '{entity.id}' value must be inside range.")
                if step <= 0:
                    raise ValueError(f"QSpinBox '{entity.id}' step must be positive.")
            elif entity.type == "QDoubleSpinBox":
                minimum = float(entity.properties.get("minimum", 0.0))
                maximum = float(entity.properties.get("maximum", 99.0))
                value = float(entity.properties.get("value", 0.0))
                step = float(entity.properties.get("step", 1.0))
                decimals = int(entity.properties.get("decimals", 2))
                if minimum > maximum:
                    raise ValueError(f"QDoubleSpinBox '{entity.id}' minimum must be <= maximum.")
                if not minimum <= value <= maximum:
                    raise ValueError(f"QDoubleSpinBox '{entity.id}' value must be inside range.")
                if step <= 0:
                    raise ValueError(f"QDoubleSpinBox '{entity.id}' step must be positive.")
                if decimals < 0 or decimals > 10:
                    raise ValueError(f"QDoubleSpinBox '{entity.id}' decimals must be between 0 and 10.")
            elif entity.type == "QSlider":
                orientation = str(entity.properties.get("orientation", "horizontal")).lower()
                minimum = int(entity.properties.get("minimum", 0))
                maximum = int(entity.properties.get("maximum", 100))
                value = int(entity.properties.get("value", 0))
                step = int(entity.properties.get("step", 1))
                if orientation not in {"horizontal", "vertical"}:
                    raise ValueError(f"QSlider '{entity.id}' orientation must be horizontal or vertical.")
                if minimum > maximum:
                    raise ValueError(f"QSlider '{entity.id}' minimum must be <= maximum.")
                if not minimum <= value <= maximum:
                    raise ValueError(f"QSlider '{entity.id}' value must be inside range.")
                if step <= 0:
                    raise ValueError(f"QSlider '{entity.id}' step must be positive.")
            elif entity.type == "QProgressBar":
                minimum = int(entity.properties.get("minimum", 0))
                maximum = int(entity.properties.get("maximum", 100))
                value = int(entity.properties.get("value", 0))
                text_visible = entity.properties.get("text_visible", True)
                if minimum > maximum:
                    raise ValueError(f"QProgressBar '{entity.id}' minimum must be <= maximum.")
                if not minimum <= value <= maximum:
                    raise ValueError(f"QProgressBar '{entity.id}' value must be inside range.")
                if not isinstance(text_visible, bool):
                    raise ValueError(f"QProgressBar '{entity.id}' text_visible must be bool.")
            elif entity.type == "QDial":
                minimum = int(entity.properties.get("minimum", 0))
                maximum = int(entity.properties.get("maximum", 100))
                value = int(entity.properties.get("value", 0))
                step = int(entity.properties.get("step", 1))
                if minimum > maximum:
                    raise ValueError(f"QDial '{entity.id}' minimum must be <= maximum.")
                if not minimum <= value <= maximum:
                    raise ValueError(f"QDial '{entity.id}' value must be inside range.")
                if step < 1:
                    raise ValueError(f"QDial '{entity.id}' step must be >= 1.")
            elif entity.type == "QLCDNumber":
                int(entity.properties.get("value", 0))
                digit_count = int(entity.properties.get("digit_count", 5))
                if digit_count < 1:
                    raise ValueError(f"QLCDNumber '{entity.id}' digit_count must be >= 1.")

    def _validate_geometry(
        self,
        entity_id: str,
        geometry: dict,
        *,
        allow_zero_size: bool,
    ) -> None:
        required_keys = ("x", "y", "width", "height")
        for key in required_keys:
            if key not in geometry:
                raise ValueError(f"Entity '{entity_id}' geometry is missing '{key}'.")
            if not isinstance(geometry[key], int):
                raise ValueError(f"Entity '{entity_id}' geometry '{key}' must be int.")
        if allow_zero_size:
            if geometry["width"] < 0 or geometry["height"] < 0:
                raise ValueError(f"Entity '{entity_id}' geometry size must be non-negative.")
            return
        if geometry["width"] <= 0 or geometry["height"] <= 0:
            raise ValueError(f"Entity '{entity_id}' geometry size must be positive.")

    def _validate_property_value(
        self,
        entity_id: str,
        property_name: str,
        value: object,
        data_type: str,
    ) -> None:
        if data_type == "str" and not isinstance(value, str):
            raise ValueError(f"Entity '{entity_id}' property '{property_name}' must be str.")
        if data_type == "bool" and not isinstance(value, bool):
            raise ValueError(f"Entity '{entity_id}' property '{property_name}' must be bool.")
        if data_type == "int" and not isinstance(value, int):
            raise ValueError(f"Entity '{entity_id}' property '{property_name}' must be int.")
        if data_type == "float" and not isinstance(value, (int, float)):
            raise ValueError(f"Entity '{entity_id}' property '{property_name}' must be float.")
        if data_type == "list[str]":
            if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
                raise ValueError(
                    f"Entity '{entity_id}' property '{property_name}' must be list[str]."
                )
        if data_type == "list[int]":
            if not isinstance(value, list) or any(not isinstance(item, int) for item in value):
                raise ValueError(
                    f"Entity '{entity_id}' property '{property_name}' must be list[int]."
                )
        if data_type == "list[tree_item]":
            if not isinstance(value, list):
                raise ValueError(
                    f"Entity '{entity_id}' property '{property_name}' must be list[tree_item]."
                )
        if data_type == "date_string":
            if not isinstance(value, str) or not is_valid_date_string(value):
                raise ValueError(
                    f"Entity '{entity_id}' property '{property_name}' must be YYYY-MM-DD string."
                )
        if data_type == "time_string":
            if not isinstance(value, str) or not is_valid_time_string(value):
                raise ValueError(
                    f"Entity '{entity_id}' property '{property_name}' must be HH:MM:SS string."
                )
        if data_type == "datetime_string":
            if not isinstance(value, str) or not is_valid_datetime_string(value):
                raise ValueError(
                    f"Entity '{entity_id}' property '{property_name}' must be YYYY-MM-DD HH:MM:SS string."
                )

    def _validate_allowed_values(
        self,
        entity_id: str,
        property_name: str,
        value: object,
        allowed_values: list,
    ) -> None:
        if value not in allowed_values:
            raise ValueError(
                f"Entity '{entity_id}' property '{property_name}' has unsupported value '{value}'."
            )

    def _validate_tree_items(
        self,
        entity_id: str,
        tree_items: object,
        column_count: int,
    ) -> None:
        if not isinstance(tree_items, list):
            raise ValueError(f"QTreeWidget '{entity_id}' tree_items must be list[tree_item].")
        for item in tree_items:
            self._validate_tree_item(entity_id, item, column_count)

    def _validate_tree_item(
        self,
        entity_id: str,
        item: object,
        column_count: int,
    ) -> None:
        if not isinstance(item, dict):
            raise ValueError(f"QTreeWidget '{entity_id}' tree_items must contain dict nodes.")
        texts = item.get("texts", [])
        children = item.get("children", [])
        if not isinstance(texts, list) or any(not isinstance(text, str) for text in texts):
            raise ValueError(f"QTreeWidget '{entity_id}' node texts must be list[str].")
        if len(texts) > column_count:
            raise ValueError(f"QTreeWidget '{entity_id}' node texts cannot exceed column_count.")
        if not isinstance(children, list):
            raise ValueError(f"QTreeWidget '{entity_id}' node children must be list[tree_item].")
        for child in children:
            self._validate_tree_item(entity_id, child, column_count)
