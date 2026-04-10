from __future__ import annotations

import unittest

from PySide6.QtWidgets import QApplication

from form_constructor.controller.document_controller import DocumentController
from form_constructor.registry.builtins import build_builtin_registry
from form_constructor.ui.main_editor.main_editor_window import MainEditorWindow


class PropertyPanelSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.controller = DocumentController(build_builtin_registry())
        self.window = MainEditorWindow(self.controller)
        self.window.show()
        self._process_events()
        self.controller.new_document(width=640, height=480)
        self._process_events()
        self.panel = self.window._property_panel

    def tearDown(self) -> None:
        self.window.close()
        self._process_events()

    def test_leaf_and_container_property_sets_match_supported_types(self) -> None:
        expected_properties = {
            "QLabel": {"geometry_locked", "text"},
            "QPushButton": {"geometry_locked", "text"},
            "QLineEdit": {"geometry_locked", "text", "placeholder"},
            "QFontComboBox": {"geometry_locked", "current_font_family"},
            "QKeySequenceEdit": {"geometry_locked", "key_sequence"},
            "QDial": {"geometry_locked", "value", "minimum", "maximum", "step"},
            "QLCDNumber": {"geometry_locked", "value", "digit_count"},
            "QPlainTextEdit": {"geometry_locked", "text", "placeholder", "read_only"},
            "QTextEdit": {"geometry_locked", "text", "placeholder", "read_only"},
            "QCheckBox": {"geometry_locked", "text", "checked"},
            "QRadioButton": {"geometry_locked", "text", "checked"},
            "QComboBox": {"geometry_locked", "items", "current_index", "editable"},
            "QListView": {"geometry_locked", "model_items"},
            "QListWidget": {"geometry_locked", "items", "current_row", "current_text"},
            "QTableView": {"geometry_locked", "column_count", "header_labels"},
            "QTreeView": {"geometry_locked", "header_labels"},
            "QTableWidget": {"geometry_locked", "row_count", "column_count", "horizontal_headers", "vertical_headers", "cell_values"},
            "QTreeWidget": {"geometry_locked", "column_count", "header_labels", "tree_items"},
            "QDateEdit": {"geometry_locked", "date", "minimum_date", "maximum_date", "display_format"},
            "QCalendarWidget": {"geometry_locked", "selected_date", "minimum_date", "maximum_date"},
            "QTimeEdit": {"geometry_locked", "time", "minimum_time", "maximum_time", "display_format"},
            "QDateTimeEdit": {"geometry_locked", "datetime", "minimum_datetime", "maximum_datetime", "display_format"},
            "QProgressBar": {"geometry_locked", "value", "minimum", "maximum", "text_visible"},
            "QSlider": {"geometry_locked", "orientation", "value", "minimum", "maximum", "step"},
            "QDoubleSpinBox": {"geometry_locked", "value", "minimum", "maximum", "step", "decimals", "prefix", "suffix"},
            "QSpinBox": {"geometry_locked", "value", "minimum", "maximum", "step", "prefix", "suffix"},
            "QWidget": {"geometry_locked"},
            "QFrame": {"geometry_locked", "frame_shape", "frame_shadow"},
            "QGroupBox": {"geometry_locked", "title", "checkable", "checked"},
            "QScrollArea": {"geometry_locked", "widget_resizable"},
        }

        for type_name, expected in expected_properties.items():
            with self.subTest(type_name=type_name):
                entity = self.controller.create_entity_from_drop(type_name, 10, 10, "form_root")
                self._process_events()
                self.assertEqual(self._visible_property_names(), expected)
                self.assertFalse(self._is_special_box_visible("tabs"))
                self.assertFalse(self._is_special_box_visible("splitter"))
                self.assertFalse(self._is_special_box_visible("wizard"))
                self.assertTrue(self.panel._geometry_box.isVisible())
                self.assertEqual(self.panel._entity_parent_edit.text(), "form_root")
                self.assertEqual(self.panel._entity_type_edit.text(), type_name)
                self.assertEqual(self.panel._active_entity_id, entity.id)

    def test_special_container_sections_follow_selection(self) -> None:
        tab_widget = self.controller.create_entity_from_drop("QTabWidget", 10, 10, "form_root")
        self._process_events()
        self.assertEqual(self._visible_property_names(), {"geometry_locked", "current_index", "tabs_closable"})
        self.assertTrue(self._is_special_box_visible("tabs"))
        self.assertFalse(self._is_special_box_visible("splitter"))
        self.assertFalse(self._is_special_box_visible("wizard"))
        self.assertEqual(self.panel._tabs_list.count(), 2)

        splitter = self.controller.create_entity_from_drop("QSplitter", 20, 20, "form_root")
        self._process_events()
        self.assertEqual(self._visible_property_names(), {"geometry_locked"})
        self.assertFalse(self._is_special_box_visible("tabs"))
        self.assertTrue(self._is_special_box_visible("splitter"))
        self.assertFalse(self._is_special_box_visible("wizard"))
        self.assertEqual(self.panel._splitter_orientation_edit.currentText(), "horizontal")

        wizard = self.controller.create_entity_from_drop("QWizard", 30, 30, "form_root")
        self._process_events()
        self.assertEqual(self._visible_property_names(), {"geometry_locked", "window_title", "current_index"})
        self.assertFalse(self._is_special_box_visible("tabs"))
        self.assertFalse(self._is_special_box_visible("splitter"))
        self.assertTrue(self._is_special_box_visible("wizard"))
        self.assertEqual(self.panel._wizard_pages_list.count(), 2)
        self.assertEqual(self.panel._active_entity_id, wizard.id)

    def test_internal_entities_are_edited_through_parent_container(self) -> None:
        tab_widget = self.controller.create_entity_from_drop("QTabWidget", 10, 10, "form_root")
        self._process_events()
        tab_page = self.controller.active_document.get_tab_pages(tab_widget.id)[0]

        self.controller.select_entity(tab_page.id)
        self._process_events()

        self.assertEqual(self.panel._active_entity_id, tab_widget.id)
        self.assertEqual(self.panel._entity_type_edit.text(), "QTabWidget")
        self.assertTrue(self._is_special_box_visible("tabs"))

    def test_geometry_locked_disables_geometry_editors(self) -> None:
        label = self.controller.create_entity_from_drop("QLabel", 10, 10, "form_root")
        self._process_events()

        for spin in (self.panel._x_spin, self.panel._y_spin, self.panel._width_spin, self.panel._height_spin):
            self.assertTrue(spin.isEnabled())

        self.controller.update_entity_property(label.id, "geometry_locked", True)
        self._process_events()

        for spin in (self.panel._x_spin, self.panel._y_spin, self.panel._width_spin, self.panel._height_spin):
            self.assertFalse(spin.isEnabled())

    def test_form_mode_is_restored_after_selected_entity_deletion(self) -> None:
        label = self.controller.create_entity_from_drop("QLabel", 10, 10, "form_root")
        self._process_events()

        self.controller.delete_entity(label.id)
        self._process_events()

        self.assertIsNone(self.panel._active_entity_id)
        self.assertIs(self.panel._mode_stack.currentWidget(), self.panel._form_box)
        self.assertEqual(self.panel._form_root_widget_type_edit.currentText(), "QWidget")

    def test_form_mode_supports_root_widget_switch(self) -> None:
        self.assertIs(self.panel._mode_stack.currentWidget(), self.panel._form_box)
        self.assertEqual(self.panel._form_root_widget_type_edit.currentText(), "QWidget")
        self.assertFalse(hasattr(self.panel, "_form_parent_edit"))

        self.panel._form_root_widget_type_edit.setCurrentText("QDialog")
        self._process_events()

        self.assertEqual(self.controller.active_document.get_form_root().root_widget_type, "QDialog")
        self.assertEqual(self.panel._form_root_widget_type_edit.currentText(), "QDialog")

    def test_combo_box_current_index_spinbox_tracks_items_count(self) -> None:
        combo = self.controller.create_entity_from_drop("QComboBox", 10, 10, "form_root")
        self._process_events()

        current_index_widget = self.panel._property_widgets["current_index"]
        self.assertEqual(current_index_widget.maximum(), 1)

        self.controller.update_entity_property(combo.id, "items", ["Only"])
        self._process_events()
        self.assertEqual(current_index_widget.maximum(), 0)

    def test_list_widget_current_row_spinbox_tracks_items_count(self) -> None:
        list_widget = self.controller.create_entity_from_drop("QListWidget", 10, 10, "form_root")
        self._process_events()

        current_row_widget = self.panel._property_widgets["current_row"]
        self.assertEqual(current_row_widget.minimum(), -1)
        self.assertEqual(current_row_widget.maximum(), -1)

        self.controller.update_entity_property(list_widget.id, "items", ["One", "Two", "Three"])
        self._process_events()
        self.assertEqual(current_row_widget.minimum(), -1)
        self.assertEqual(current_row_widget.maximum(), 2)

    def test_table_widget_row_and_column_spins_are_non_negative(self) -> None:
        table_widget = self.controller.create_entity_from_drop("QTableWidget", 10, 10, "form_root")
        self._process_events()

        row_count_widget = self.panel._property_widgets["row_count"]
        column_count_widget = self.panel._property_widgets["column_count"]
        self.assertEqual(row_count_widget.minimum(), 0)
        self.assertEqual(column_count_widget.minimum(), 0)

    def test_tree_widget_column_count_spin_is_non_negative(self) -> None:
        tree_widget = self.controller.create_entity_from_drop("QTreeWidget", 10, 10, "form_root")
        self._process_events()

        column_count_widget = self.panel._property_widgets["column_count"]
        self.assertEqual(column_count_widget.minimum(), 0)

    def test_date_edit_fields_have_expected_placeholder(self) -> None:
        date_edit = self.controller.create_entity_from_drop("QDateEdit", 10, 10, "form_root")
        self._process_events()

        self.assertEqual(self.panel._property_widgets["date"].placeholderText(), "YYYY-MM-DD")
        self.assertEqual(self.panel._property_widgets["minimum_date"].placeholderText(), "YYYY-MM-DD")
        self.assertEqual(self.panel._property_widgets["maximum_date"].placeholderText(), "YYYY-MM-DD")

    def test_calendar_widget_fields_have_expected_placeholder(self) -> None:
        calendar_widget = self.controller.create_entity_from_drop("QCalendarWidget", 10, 10, "form_root")
        self._process_events()

        self.assertEqual(self.panel._property_widgets["selected_date"].placeholderText(), "YYYY-MM-DD")
        self.assertEqual(self.panel._property_widgets["minimum_date"].placeholderText(), "YYYY-MM-DD")
        self.assertEqual(self.panel._property_widgets["maximum_date"].placeholderText(), "YYYY-MM-DD")

    def test_time_edit_fields_have_expected_placeholder(self) -> None:
        time_edit = self.controller.create_entity_from_drop("QTimeEdit", 10, 10, "form_root")
        self._process_events()

        self.assertEqual(self.panel._property_widgets["time"].placeholderText(), "HH:MM:SS")
        self.assertEqual(self.panel._property_widgets["minimum_time"].placeholderText(), "HH:MM:SS")
        self.assertEqual(self.panel._property_widgets["maximum_time"].placeholderText(), "HH:MM:SS")

    def test_datetime_edit_fields_have_expected_placeholder(self) -> None:
        datetime_edit = self.controller.create_entity_from_drop("QDateTimeEdit", 10, 10, "form_root")
        self._process_events()

        self.assertEqual(self.panel._property_widgets["datetime"].placeholderText(), "YYYY-MM-DD HH:MM:SS")
        self.assertEqual(
            self.panel._property_widgets["minimum_datetime"].placeholderText(),
            "YYYY-MM-DD HH:MM:SS",
        )
        self.assertEqual(
            self.panel._property_widgets["maximum_datetime"].placeholderText(),
            "YYYY-MM-DD HH:MM:SS",
        )

    def test_scroll_area_internal_content_is_edited_through_parent(self) -> None:
        scroll_area = self.controller.create_entity_from_drop("QScrollArea", 10, 10, "form_root")
        self._process_events()
        content = self.controller.active_document.get_scroll_content(scroll_area.id)

        self.controller.select_entity(content.id)
        self._process_events()

        self.assertEqual(self.panel._active_entity_id, scroll_area.id)
        self.assertEqual(self.panel._entity_type_edit.text(), "QScrollArea")
        self.assertEqual(self._visible_property_names(), {"geometry_locked", "widget_resizable"})

    def test_splitter_pane_and_wizard_page_are_edited_through_parent(self) -> None:
        splitter = self.controller.create_entity_from_drop("QSplitter", 10, 10, "form_root")
        self._process_events()
        splitter_pane = self.controller.active_document.get_children(splitter.id)[0]

        self.controller.select_entity(splitter_pane.id)
        self._process_events()
        self.assertEqual(self.panel._active_entity_id, splitter.id)
        self.assertEqual(self.panel._entity_type_edit.text(), "QSplitter")
        self.assertTrue(self._is_special_box_visible("splitter"))

        wizard = self.controller.create_entity_from_drop("QWizard", 20, 20, "form_root")
        self._process_events()
        wizard_page = self.controller.active_document.get_wizard_pages(wizard.id)[0]

        self.controller.select_entity(wizard_page.id)
        self._process_events()
        self.assertEqual(self.panel._active_entity_id, wizard.id)
        self.assertEqual(self.panel._entity_type_edit.text(), "QWizard")
        self.assertTrue(self._is_special_box_visible("wizard"))

    def test_readonly_fields_and_selection_switching_remain_consistent(self) -> None:
        push_button = self.controller.create_entity_from_drop("QPushButton", 10, 10, "form_root")
        self._process_events()

        self.assertTrue(self.panel._entity_type_edit.isReadOnly())
        self.assertTrue(self.panel._entity_id_edit.isReadOnly())
        self.assertTrue(self.panel._entity_parent_edit.isReadOnly())
        self.assertEqual(self.panel._entity_parent_edit.text(), "form_root")
        self.assertEqual(self.panel._entity_type_edit.text(), "QPushButton")
        self.assertEqual(self._visible_property_names(), {"geometry_locked", "text"})

        tab_widget = self.controller.create_entity_from_drop("QTabWidget", 20, 20, "form_root")
        self._process_events()
        self.assertTrue(self._is_special_box_visible("tabs"))
        self.assertFalse(self._is_special_box_visible("splitter"))
        self.assertFalse(self._is_special_box_visible("wizard"))

        self.controller.select_entity(push_button.id)
        self._process_events()
        self.assertFalse(self._is_special_box_visible("tabs"))
        self.assertFalse(self._is_special_box_visible("splitter"))
        self.assertFalse(self._is_special_box_visible("wizard"))
        self.assertEqual(self.panel._entity_type_edit.text(), "QPushButton")
        self.assertEqual(self._visible_property_names(), {"geometry_locked", "text"})

    def _visible_property_names(self) -> set[str]:
        return {
            name
            for name, widget in self.panel._property_widgets.items()
            if not widget.isHidden()
        }

    def _is_special_box_visible(self, name: str) -> bool:
        boxes = {
            "tabs": self.panel._tabs_box,
            "splitter": self.panel._splitter_box,
            "wizard": self.panel._wizard_box,
        }
        return not boxes[name].isHidden()

    @classmethod
    def _process_events(cls) -> None:
        cls._app.processEvents()


if __name__ == "__main__":
    unittest.main()
