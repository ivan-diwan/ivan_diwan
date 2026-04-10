from __future__ import annotations

import unittest

from PySide6.QtWidgets import QApplication, QWidget

from form_constructor.document.models import EntityModel
from form_constructor.factory.widget_factory import WidgetFactory
from form_constructor.registry.builtins import build_builtin_registry


class WidgetCatalogAlignmentSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.registry = build_builtin_registry()
        self.factory = WidgetFactory()

    def test_every_palette_type_has_working_runtime_factory_path(self) -> None:
        for definition in self.registry.list_palette_types():
            with self.subTest(type_name=definition.type_name):
                widget = self.factory.create_widget(self._make_entity(definition.type_name), parent=None)
                self.assertIsInstance(widget, QWidget)
                self.factory.refresh_widget(widget, self._make_entity(definition.type_name))

    def test_special_container_registry_entries_define_required_support_metadata(self) -> None:
        expected_actions = {
            "QTabWidget": {"add_tab_page", "remove_tab_page", "rename_tab_page", "set_current_tab"},
            "QScrollArea": {"get_scroll_content"},
            "QSplitter": {"set_splitter_orientation", "set_splitter_sizes"},
            "QWizard": {"add_wizard_page", "remove_wizard_page", "rename_wizard_page", "set_current_wizard_page"},
        }
        expected_auto_children = {
            "QTabWidget": ["TabPage", "TabPage"],
            "QScrollArea": ["ContainerContent"],
            "QSplitter": ["SplitterPane", "SplitterPane"],
            "QWizard": ["WizardPage", "WizardPage"],
        }

        for type_name, actions in expected_actions.items():
            with self.subTest(type_name=type_name):
                self.assertEqual(set(self.registry.get_special_actions(type_name)), actions)
                self.assertEqual(self.registry.get_auto_create_children(type_name), expected_auto_children[type_name])

    def test_registry_grouping_helpers_match_palette_contract(self) -> None:
        grouped = self.registry.list_palette_types_by_group()
        palette_types = {definition.type_name for definition in self.registry.list_palette_types()}
        grouped_types = {
            definition.type_name
            for definitions in grouped.values()
            for definition in definitions
        }
        creatable_types = {definition.type_name for definition in self.registry.list_creatable_types()}
        internal_types = {definition.type_name for definition in self.registry.list_types_by_editor_kind("internal")}

        self.assertEqual(set(grouped), set(self.registry.list_palette_groups()))
        self.assertEqual(grouped_types, palette_types)
        self.assertTrue(palette_types.issubset(creatable_types))
        self.assertFalse(palette_types.intersection(internal_types))

    def _make_entity(self, type_name: str) -> EntityModel:
        width, height = self.registry.get_default_size(type_name)
        return EntityModel(
            id=f"{type_name.lower()}_1",
            type=type_name,
            parent_id="form_root",
            name=f"{type_name.lower()}_1",
            order=0,
            geometry={"x": 10, "y": 10, "width": width, "height": height},
            properties=self.registry.get_default_properties(type_name),
        )


if __name__ == "__main__":
    unittest.main()
