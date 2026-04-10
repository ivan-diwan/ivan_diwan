from __future__ import annotations

import unittest

from PySide6.QtWidgets import QApplication

from form_constructor.registry.builtins import build_builtin_registry
from form_constructor.ui.palette.palette_panel import PalettePanel


class PalettePanelSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.panel = PalettePanel(build_builtin_registry())
        self.panel.show()
        self._process_events()

    def tearDown(self) -> None:
        self.panel.close()
        self._process_events()

    def test_palette_panel_uses_readable_description_labels(self) -> None:
        self.assertEqual(self.panel._description_title.text(), "Описание объекта")
        self.assertIn("Выберите объект", self.panel._description_view.placeholderText())

    @classmethod
    def _process_events(cls) -> None:
        cls._app.processEvents()


if __name__ == "__main__":
    unittest.main()
