from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from PySide6.QtWidgets import QApplication

from form_constructor.conversion.export_validation import ExportDiagnosticError, ExportValidator
from form_constructor.conversion.exporter import PythonExporter
from form_constructor.document.form_document import FormDocument
from form_constructor.document.models import FormRootModel
from form_constructor.registry.builtins import build_builtin_registry
from form_constructor.serialization.form_serializer import FormSerializer
from tests.support import managed_test_paths


class PythonExporterSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.registry = build_builtin_registry()
        self.exporter = PythonExporter()
        self.export_validator = ExportValidator()
        self.serializer = FormSerializer(widget_registry=self.registry)

    def test_exports_widget_root_and_leaf_widgets(self) -> None:
        document = self._make_document(root_widget_type="QWidget")
        document.create_entity(
            type_name="QPushButton",
            parent_id="form_root",
            geometry={"x": 10, "y": 20, "width": 120, "height": 32},
            name="push_button_1",
            properties={"text": "Run"},
        )
        document.create_entity(
            type_name="QComboBox",
            parent_id="form_root",
            geometry={"x": 30, "y": 70, "width": 160, "height": 30},
            name="combo_box_1",
            properties={"items": ["One", "Two"], "current_index": 1, "editable": True},
        )

        source = self.exporter.export(document)

        self.assertIn("class GeneratedWidget(QWidget):", source)
        self.assertIn('self.resize(800, 600)', source)
        self.assertIn('self.setWindowTitle(\'Demo Form\')', source)
        self.assertIn("self.push_button_1 = QPushButton(self)", source)
        self.assertIn("self.push_button_1.setText('Run')", source)
        self.assertIn("self.combo_box_1 = QComboBox(self)", source)
        self.assertIn("self.combo_box_1.setEditable(True)", source)
        self.assertIn("self.combo_box_1.addItem('One')", source)
        self.assertIn("self.combo_box_1.setCurrentIndex(1)", source)
        compile(source, "<generated_widget>", "exec")
        generated_widget = self._instantiate_generated(source, "GeneratedWidget")
        self.assertEqual(generated_widget.objectName(), "Form")
        self.assertEqual(generated_widget.push_button_1.objectName(), "push_button_1")
        self.assertEqual(generated_widget.combo_box_1.currentIndex(), 1)
        self._assert_geometry(generated_widget.push_button_1, 10, 20, 120, 32)
        self._assert_geometry(generated_widget.combo_box_1, 30, 70, 160, 30)
        self.assertIs(generated_widget.push_button_1.parentWidget(), generated_widget)
        self.assertIs(generated_widget.combo_box_1.parentWidget(), generated_widget)

    def test_collects_only_required_imports_for_simple_widget_document(self) -> None:
        document = self._make_document(root_widget_type="QWidget")
        document.create_entity(
            type_name="QPushButton",
            parent_id="form_root",
            geometry={"x": 10, "y": 20, "width": 120, "height": 32},
            name="push_button_1",
            properties={"text": "Run"},
        )

        source = self.exporter.export(document)

        self.assertIn(
            "from PySide6.QtWidgets import QApplication, QPushButton, QWidget",
            source,
        )
        self.assertNotIn("from PySide6.QtCore import Qt", source)
        self.assertNotIn("QWizardPage", source)

    def test_exports_dialog_root(self) -> None:
        document = self._make_document(root_widget_type="QDialog")

        source = self.exporter.export(document)

        self.assertIn("class GeneratedDialog(QDialog):", source)
        compile(source, "<generated_dialog>", "exec")
        generated_dialog = self._instantiate_generated(source, "GeneratedDialog")
        self.assertEqual(generated_dialog.objectName(), "Form")
        self.assertEqual(generated_dialog.width(), 800)
        self.assertEqual(generated_dialog.height(), 600)

    def test_collects_qt_import_when_splitter_exists(self) -> None:
        document = self._make_document(root_widget_type="QDialog")
        document.create_splitter(
            parent_id="form_root",
            geometry={"x": 10, "y": 10, "width": 240, "height": 120},
            orientation="horizontal",
            name="splitter_1",
        )

        source = self.exporter.export(document)

        self.assertIn("from PySide6.QtCore import Qt", source)
        self.assertIn(
            "from PySide6.QtWidgets import QApplication, QDialog, QSplitter, QWidget",
            source,
        )

    def test_exports_supported_special_containers_with_internal_structure(self) -> None:
        document = self._make_document(root_widget_type="QWidget")

        tab_widget = document.create_tab_widget(
            parent_id="form_root",
            geometry={"x": 10, "y": 10, "width": 300, "height": 200},
            name="tab_widget_1",
        )
        scroll_area = document.create_scroll_area(
            parent_id="form_root",
            geometry={"x": 20, "y": 20, "width": 250, "height": 180},
            name="scroll_area_1",
        )
        splitter = document.create_splitter(
            parent_id="form_root",
            geometry={"x": 30, "y": 30, "width": 320, "height": 160},
            orientation="vertical",
            name="splitter_1",
        )
        wizard = document.create_wizard(
            parent_id="form_root",
            geometry={"x": 40, "y": 40, "width": 500, "height": 360},
            name="wizard_1",
        )

        first_tab_page = document.get_tab_pages(tab_widget.id)[0]
        document.create_entity(
            type_name="QLabel",
            parent_id=first_tab_page.id,
            geometry={"x": 5, "y": 6, "width": 80, "height": 20},
            name="tab_label_1",
            properties={"text": "Inside Tab"},
        )

        scroll_content = document.get_scroll_content(scroll_area.id)
        document.create_entity(
            type_name="QPushButton",
            parent_id=scroll_content.id,
            geometry={"x": 7, "y": 8, "width": 90, "height": 28},
            name="scroll_button_1",
            properties={"text": "Inside Scroll"},
        )

        first_pane = document.get_splitter_panes(splitter.id)[0]
        document.create_entity(
            type_name="QGroupBox",
            parent_id=first_pane.id,
            geometry={"x": 9, "y": 10, "width": 140, "height": 70},
            name="pane_group_1",
            properties={"title": "Pane Group", "checkable": True, "checked": False},
        )

        first_page = document.get_wizard_pages(wizard.id)[0]
        document.rename_wizard_page(first_page.id, "Step One", "Wizard Intro")
        document.create_entity(
            type_name="QLineEdit",
            parent_id=first_page.id,
            geometry={"x": 11, "y": 12, "width": 160, "height": 30},
            name="wizard_line_1",
            properties={"text": "Wizard Value", "placeholder": "Enter text"},
        )

        source = self.exporter.export(document)

        self.assertIn("self.tab_widget_1 = QTabWidget(self)", source)
        self.assertIn("self.tab_page_1 = QWidget()", source)
        self.assertIn("self.tab_widget_1.addTab(self.tab_page_1, 'Tab 1')", source)
        self.assertIn("self.tab_label_1 = QLabel(self.tab_page_1)", source)

        self.assertIn("self.scroll_area_1 = QScrollArea(self)", source)
        self.assertIn("self.scroll_content_1 = QWidget()", source)
        self.assertIn("self.scroll_area_1.setWidget(self.scroll_content_1)", source)
        self.assertIn("self.scroll_button_1 = QPushButton(self.scroll_content_1)", source)

        self.assertIn("self.splitter_1 = QSplitter(self)", source)
        self.assertIn("self.splitter_1.setOrientation(Qt.Vertical)", source)
        self.assertIn("self.splitter_pane_1 = QWidget()", source)
        self.assertIn("self.splitter_1.setSizes([1, 1])", source)
        self.assertIn("self.pane_group_1 = QGroupBox(self.splitter_pane_1)", source)

        self.assertIn("self.wizard_1 = QWizard(self)", source)
        self.assertIn("self.wizard_page_1 = QWizardPage()", source)
        self.assertIn("self.wizard_1.setPage(0, self.wizard_page_1)", source)
        self.assertIn("self.wizard_page_1.setTitle('Step One')", source)
        self.assertIn("self.wizard_page_1.setSubTitle('Wizard Intro')", source)
        self.assertIn("self.wizard_line_1 = QLineEdit(self.wizard_page_1)", source)
        compile(source, "<generated_specials>", "exec")
        generated_widget = self._instantiate_generated(source, "GeneratedWidget")
        self.assertEqual(generated_widget.tab_widget_1.count(), 2)
        self.assertEqual(generated_widget.tab_widget_1.currentIndex(), 0)
        self._assert_geometry(generated_widget.tab_widget_1, 10, 10, 300, 200)
        self.assertIs(generated_widget.tab_label_1.parentWidget(), generated_widget.tab_page_1)
        self._assert_geometry(generated_widget.tab_label_1, 5, 6, 80, 20)
        self.assertEqual(generated_widget.scroll_area_1.widget().objectName(), "scroll_content_1")
        self.assertTrue(generated_widget.scroll_area_1.widgetResizable())
        self.assertEqual(generated_widget.scroll_button_1.text(), "Inside Scroll")
        self.assertIs(generated_widget.scroll_button_1.parentWidget(), generated_widget.scroll_content_1)
        self._assert_geometry(generated_widget.scroll_button_1, 7, 8, 90, 28)
        self.assertEqual(generated_widget.splitter_1.count(), 2)
        self.assertEqual(generated_widget.splitter_1.orientation().name, "Vertical")
        self._assert_geometry(generated_widget.splitter_1, 30, 30, 320, 160)
        self.assertIs(generated_widget.pane_group_1.parentWidget(), generated_widget.splitter_pane_1)
        self._assert_geometry(generated_widget.pane_group_1, 9, 10, 140, 70)
        self.assertEqual(generated_widget.wizard_1.page(0).title(), "Step One")
        self.assertEqual(generated_widget.wizard_1.page(0).subTitle(), "Wizard Intro")
        self.assertEqual(generated_widget.wizard_line_1.text(), "Wizard Value")
        self.assertIs(generated_widget.wizard_line_1.parentWidget(), generated_widget.wizard_page_1)
        self._assert_geometry(generated_widget.wizard_line_1, 11, 12, 160, 30)

    def test_object_name_is_preserved_from_document_name(self) -> None:
        document = self._make_document(root_widget_type="QWidget")
        document.form_root.name = "Root Form"
        document.create_entity(
            type_name="QLabel",
            parent_id="form_root",
            geometry={"x": 10, "y": 10, "width": 80, "height": 20},
            name="Status Label",
            properties={"text": "Ready"},
        )

        source = self.exporter.export(document)

        self.assertIn("self.setObjectName('Root Form')", source)
        self.assertIn("self.status_label = QLabel(self)", source)
        self.assertIn("self.status_label.setObjectName('Status Label')", source)
        generated_widget = self._instantiate_generated(source, "GeneratedWidget")
        self.assertEqual(generated_widget.objectName(), "Root Form")
        self.assertEqual(generated_widget.status_label.objectName(), "Status Label")

    def test_exports_frame_and_group_box_runtime_properties(self) -> None:
        document = self._make_document(root_widget_type="QWidget")
        document.create_entity(
            type_name="QFrame",
            parent_id="form_root",
            geometry={"x": 10, "y": 20, "width": 160, "height": 90},
            name="frame_1",
            properties={"frame_shape": "Box", "frame_shadow": "Sunken"},
        )
        document.create_entity(
            type_name="QGroupBox",
            parent_id="form_root",
            geometry={"x": 30, "y": 40, "width": 180, "height": 100},
            name="group_box_1",
            properties={"title": "Options", "checkable": True, "checked": True},
        )

        source = self.exporter.export(document)
        generated_widget = self._instantiate_generated(source, "GeneratedWidget")

        self.assertEqual(generated_widget.frame_1.frameShape().name, "Box")
        self.assertEqual(generated_widget.frame_1.frameShadow().name, "Sunken")
        self.assertEqual(generated_widget.group_box_1.title(), "Options")
        self.assertTrue(generated_widget.group_box_1.isCheckable())
        self.assertTrue(generated_widget.group_box_1.isChecked())
        self._assert_geometry(generated_widget.frame_1, 10, 20, 160, 90)
        self._assert_geometry(generated_widget.group_box_1, 30, 40, 180, 100)

    def test_export_to_file_writes_python_source(self) -> None:
        document = self._make_document(root_widget_type="QWidget")
        with managed_test_paths("tests\\_tmp_generated_form.py") as (path,):
            self.exporter.export_to_file(document, str(path))
            source = path.read_text(encoding="utf-8")
            self.assertIn("class GeneratedWidget(QWidget):", source)

    def test_validate_export_accepts_generated_python(self) -> None:
        document = self._make_document(root_widget_type="QWidget")
        document.create_entity(
            type_name="QLabel",
            parent_id="form_root",
            geometry={"x": 10, "y": 20, "width": 120, "height": 24},
            name="label_1",
            properties={"text": "Ready"},
        )

        self.exporter.validate_export(document)

    def test_export_validator_validates_python_code_and_file(self) -> None:
        code = "class Demo:\n    pass\n"
        with managed_test_paths("tests\\_tmp_export_validator.py") as (path,):
            self.export_validator.validate_python_syntax(code)
            path.write_text(code, encoding="utf-8")
            self.export_validator.validate_python_file(str(path))

    def test_export_to_file_does_not_write_invalid_python_when_validation_fails(self) -> None:
        document = self._make_document(root_widget_type="QWidget")
        with managed_test_paths("tests\\_tmp_invalid_generated_form.py") as (path,):
            with patch.object(
                self.exporter._export_validator,
                "validate_python_syntax",
                side_effect=SyntaxError("broken export"),
            ):
                with self.assertRaises(ExportDiagnosticError) as context:
                    self.exporter.export_to_file(document, str(path))
            diagnostic = context.exception.diagnostic
            self.assertEqual(diagnostic.stage, "export_to_file")
            self.assertIn("broken export", diagnostic.message)
            self.assertFalse(path.exists())

    def test_exporter_exposes_structured_diagnostic_for_invalid_date_value(self) -> None:
        document = self._make_document(root_widget_type="QWidget")
        document.create_entity(
            type_name="QDateEdit",
            parent_id="form_root",
            geometry={"x": 10, "y": 20, "width": 140, "height": 28},
            name="date_edit_1",
            properties={
                "date": "broken-date",
                "minimum_date": "1900-01-01",
                "maximum_date": "2100-12-31",
            },
        )

        with self.assertRaises(ExportDiagnosticError) as context:
            self.exporter.export(document)

        diagnostic = context.exception.diagnostic
        self.assertEqual(diagnostic.stage, "emit_qdate")
        self.assertEqual(diagnostic.pattern, "YYYY-MM-DD")
        self.assertEqual(diagnostic.details.get("value"), "broken-date")

    def test_exported_python_file_can_be_executed_as_script(self) -> None:
        document = self._make_document(root_widget_type="QWidget")
        document.create_entity(
            type_name="QPushButton",
            parent_id="form_root",
            geometry={"x": 10, "y": 20, "width": 120, "height": 32},
            name="push_button_1",
            properties={"text": "Run"},
        )
        with managed_test_paths("tests\\_tmp_generated_run.py") as (path,):
            self.exporter.export_to_file(document, str(path))
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    (
                        "import os, runpy;"
                        "from PySide6.QtWidgets import QApplication;"
                        "os.environ['QT_QPA_PLATFORM']='offscreen';"
                        "QApplication.exec=lambda self: 0;"
                        "runpy.run_path(r'" + str(path) + "', run_name='__main__')"
                    ),
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)

    def test_exported_dialog_python_file_can_be_executed_as_script(self) -> None:
        document = self._make_document(root_widget_type="QDialog")
        document.create_entity(
            type_name="QLabel",
            parent_id="form_root",
            geometry={"x": 14, "y": 18, "width": 100, "height": 24},
            name="dialog_label_1",
            properties={"text": "Dialog"},
        )
        with managed_test_paths("tests\\_tmp_generated_dialog_run.py") as (path,):
            self.exporter.export_to_file(document, str(path))
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    (
                        "import os, runpy;"
                        "from PySide6.QtWidgets import QApplication;"
                        "os.environ['QT_QPA_PLATFORM']='offscreen';"
                        "QApplication.exec=lambda self: 0;"
                        "runpy.run_path(r'" + str(path) + "', run_name='__main__')"
                    ),
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)

    def test_repeated_export_of_same_document_is_stable(self) -> None:
        document = self._make_document(root_widget_type="QWidget")
        document.create_entity(
            type_name="QPushButton",
            parent_id="form_root",
            geometry={"x": 10, "y": 20, "width": 120, "height": 32},
            name="push_button_1",
            properties={"text": "Run"},
        )
        tab_widget = document.create_tab_widget(
            parent_id="form_root",
            geometry={"x": 50, "y": 60, "width": 280, "height": 180},
            name="tab_widget_1",
        )
        first_tab_page = document.get_tab_pages(tab_widget.id)[0]
        document.create_entity(
            type_name="QLabel",
            parent_id=first_tab_page.id,
            geometry={"x": 5, "y": 6, "width": 70, "height": 20},
            name="tab_label_1",
            properties={"text": "Stable"},
        )

        source_first = self.exporter.export(document)
        source_second = self.exporter.export(document)

        self.assertEqual(source_first, source_second)

    def test_export_template_keeps_post_build_after_creation_and_properties(self) -> None:
        document = self._make_document(root_widget_type="QWidget")
        splitter = document.create_splitter(
            parent_id="form_root",
            geometry={"x": 10, "y": 20, "width": 300, "height": 160},
            orientation="horizontal",
            name="splitter_1",
        )
        document.set_splitter_sizes(splitter.id, [120, 180])

        source = self.exporter.export(document)

        orientation_pos = source.index("self.splitter_1.setOrientation(Qt.Horizontal)")
        sizes_pos = source.index("self.splitter_1.setSizes([120, 180])")
        footer_pos = source.index('if __name__ == "__main__":')
        self.assertLess(orientation_pos, sizes_pos)
        self.assertLess(sizes_pos, footer_pos)

    def test_equal_sibling_order_is_resolved_deterministically_by_name_and_id(self) -> None:
        document = self._make_document(root_widget_type="QWidget")
        first = document.create_entity(
            type_name="QLabel",
            parent_id="form_root",
            geometry={"x": 10, "y": 10, "width": 80, "height": 24},
            name="beta_label",
            properties={"text": "B"},
        )
        second = document.create_entity(
            type_name="QLabel",
            parent_id="form_root",
            geometry={"x": 20, "y": 20, "width": 80, "height": 24},
            name="alpha_label",
            properties={"text": "A"},
        )
        first.order = 0
        second.order = 0

        source = self.exporter.export(document)

        alpha_pos = source.index("self.alpha_label = QLabel(self)")
        beta_pos = source.index("self.beta_label = QLabel(self)")
        self.assertLess(alpha_pos, beta_pos)

    def test_duplicate_and_keyword_names_produce_valid_unique_python_refs(self) -> None:
        document = self._make_document(root_widget_type="QWidget")
        document.create_entity(
            type_name="QLabel",
            parent_id="form_root",
            geometry={"x": 10, "y": 10, "width": 70, "height": 20},
            name="Status Label",
            properties={"text": "One"},
        )
        document.create_entity(
            type_name="QPushButton",
            parent_id="form_root",
            geometry={"x": 20, "y": 20, "width": 90, "height": 28},
            name="Status Label",
            properties={"text": "Two"},
        )
        document.create_entity(
            type_name="QLineEdit",
            parent_id="form_root",
            geometry={"x": 30, "y": 30, "width": 120, "height": 30},
            name="class",
            properties={"text": "Three", "placeholder": ""},
        )

        source = self.exporter.export(document)

        self.assertIn("self.status_label = QLabel(self)", source)
        self.assertIn("self.status_label_2 = QPushButton(self)", source)
        self.assertIn("self.class_widget = QLineEdit(self)", source)
        compile(source, "<generated_duplicate_names>", "exec")
        generated_widget = self._instantiate_generated(source, "GeneratedWidget")
        self.assertEqual(generated_widget.status_label.objectName(), "Status Label")
        self.assertEqual(generated_widget.status_label_2.objectName(), "Status Label")
        self.assertEqual(generated_widget.class_widget.objectName(), "class")

    def test_editor_only_properties_are_not_emitted_into_python(self) -> None:
        document = self._make_document(root_widget_type="QWidget")
        document.create_entity(
            type_name="QPushButton",
            parent_id="form_root",
            geometry={"x": 10, "y": 20, "width": 120, "height": 32},
            name="push_button_1",
            properties={"text": "Run", "geometry_locked": True},
        )

        source = self.exporter.export(document)

        self.assertNotIn("geometry_locked", source)
        self.assertNotIn("setGeometryLocked", source)
        generated_widget = self._instantiate_generated(source, "GeneratedWidget")
        self.assertEqual(generated_widget.push_button_1.text(), "Run")

    def test_export_does_not_mutate_document_structure_or_data(self) -> None:
        document = self._make_document(root_widget_type="QWidget")
        document.create_tab_widget(
            parent_id="form_root",
            geometry={"x": 50, "y": 60, "width": 280, "height": 180},
            name="tab_widget_1",
        )
        before = self.serializer.serialize_to_json(document)

        source = self.exporter.export(document)

        after = self.serializer.serialize_to_json(document)
        self.assertTrue(source.strip())
        self.assertEqual(before, after)

    def _make_document(self, *, root_widget_type: str) -> FormDocument:
        form_root = FormRootModel(
            id="form_root",
            type="FormRoot",
            name="Form",
            root_widget_type=root_widget_type,
            width=800,
            height=600,
            window_title="Demo Form",
        )
        return FormDocument(form_root=form_root, widget_registry=self.registry)

    def _instantiate_generated(self, source: str, class_name: str):
        namespace: dict[str, object] = {}
        exec(source, namespace)
        generated_class = namespace[class_name]
        return generated_class()

    def _assert_geometry(self, widget, x: int, y: int, width: int, height: int) -> None:
        geometry = widget.geometry()
        self.assertEqual(
            (geometry.x(), geometry.y(), geometry.width(), geometry.height()),
            (x, y, width, height),
        )


if __name__ == "__main__":
    unittest.main()
