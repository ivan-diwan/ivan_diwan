from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import unittest

from PySide6.QtWidgets import QApplication

from form_constructor.conversion.exporter import PythonExporter
from form_constructor.serialization.form_serializer import FormSerializer
from form_constructor.registry.builtins import build_builtin_registry
from tests.support import managed_test_paths


class ExportCaseFilesSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])
        cls._cases_dir = Path("tests/export_cases")

    def setUp(self) -> None:
        self.registry = build_builtin_registry()
        self.serializer = FormSerializer(widget_registry=self.registry)
        self.exporter = PythonExporter()

    def test_case_files_export_compile_and_instantiate(self) -> None:
        for case_path in sorted(self._cases_dir.glob("*.json")):
            with self.subTest(case=case_path.name):
                document = self.serializer.load_json(str(case_path))
                self.exporter.validate_export(document)
                source = self.exporter.export(document)
                compile(source, f"<{case_path.stem}>", "exec")
                generated_widget = self._instantiate_generated(source, "GeneratedWidget")
                self._assert_case_runtime(case_path.stem, generated_widget)

    def test_case_files_exported_python_runs_as_script(self) -> None:
        for case_path in sorted(self._cases_dir.glob("*.json")):
            with self.subTest(case=case_path.name):
                document = self.serializer.load_json(str(case_path))
                exported_path_str = str(self._cases_dir / f"_{case_path.stem}_generated.py")
                with managed_test_paths(exported_path_str) as (exported_path,):
                    self.exporter.export_to_file(document, str(exported_path))
                    result = subprocess.run(
                        [
                            sys.executable,
                            "-c",
                            (
                                "import os, runpy;"
                                "from PySide6.QtWidgets import QApplication;"
                                "os.environ['QT_QPA_PLATFORM']='offscreen';"
                                "QApplication.exec=lambda self: 0;"
                                f"runpy.run_path(r'{exported_path}', run_name='__main__')"
                            ),
                        ],
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
                    self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)

    @staticmethod
    def _instantiate_generated(source: str, class_name: str):
        namespace: dict[str, object] = {}
        exec(source, namespace)
        generated_class = namespace[class_name]
        return generated_class()

    def _assert_case_runtime(self, case_name: str, widget) -> None:
        if case_name == "empty_form":
            self.assertEqual((widget.width(), widget.height()), (800, 600))
            return

        if case_name == "basic_leafs":
            self.assertEqual(widget.combo_box_1.currentIndex(), 2)
            self.assertTrue(widget.combo_box_1.isEditable())
            self.assertEqual(widget.check_box_1.text(), "Check")
            return

        if case_name == "containers":
            self.assertIs(widget.widget_button_1.parentWidget(), widget.widget_1)
            self.assertIs(widget.frame_label_1.parentWidget(), widget.frame_1)
            self.assertIs(widget.group_line_edit_1.parentWidget(), widget.group_box_1)
            self.assertEqual(widget.group_box_1.title(), "Options")
            return

        if case_name == "tabs":
            self.assertEqual(widget.tab_widget_1.count(), 2)
            self.assertEqual(widget.tab_widget_1.currentIndex(), 1)
            self.assertIs(widget.tab_button_1.parentWidget(), widget.tab_page_1)
            self.assertIs(widget.tab_label_1.parentWidget(), widget.tab_page_2)
            return

        if case_name == "scroll_area":
            self.assertEqual(widget.scroll_area_1.widget().objectName(), "scroll_content_1")
            self.assertIs(widget.scroll_button_1.parentWidget(), widget.scroll_content_1)
            self.assertIs(widget.scroll_label_1.parentWidget(), widget.scroll_content_1)
            return

        if case_name == "splitter":
            self.assertEqual(widget.splitter_1.count(), 2)
            self.assertEqual(widget.splitter_1.orientation().name, "Vertical")
            self.assertIs(widget.pane_button_1.parentWidget(), widget.splitter_pane_1)
            self.assertIs(widget.pane_label_1.parentWidget(), widget.splitter_pane_2)
            return

        if case_name == "wizard":
            self.assertEqual(widget.wizard_1.page(0).title(), "Intro")
            self.assertEqual(widget.wizard_1.page(1).title(), "Finish")
            self.assertIs(widget.wizard_line_edit_1.parentWidget(), widget.wizard_page_1)
            self.assertIs(widget.wizard_check_box_1.parentWidget(), widget.wizard_page_2)
            return

        if case_name == "mixed_complex":
            self.assertIs(widget.tab_widget_1.parentWidget(), widget.group_box_1)
            self.assertIs(widget.scroll_button_1.parentWidget(), widget.scroll_content_1)
            self.assertIs(widget.wizard_label_1.parentWidget(), widget.wizard_page_1)
            self.assertIs(widget.splitter_label_1.parentWidget(), widget.splitter_pane_1)
            self.assertIs(widget.splitter_line_edit_1.parentWidget(), widget.splitter_pane_2)
            self.assertEqual(widget.tab_widget_1.tabText(0), "Scroll")
            self.assertEqual(widget.tab_widget_1.tabText(1), "Wizard")
            return

        raise AssertionError(f"Unknown export case '{case_name}'.")


if __name__ == "__main__":
    unittest.main()
