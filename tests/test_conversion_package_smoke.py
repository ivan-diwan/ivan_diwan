from __future__ import annotations

import unittest

from form_constructor.conversion import Exporter, Importer, PythonConverter, PythonExporter
from form_constructor.registry.builtins import build_builtin_registry


class ConversionPackageSmokeTests(unittest.TestCase):
    def test_conversion_exports_resolve_to_python_exporter(self) -> None:
        self.assertIs(Exporter, PythonExporter)
        self.assertIs(Importer.__name__, "PythonImporter")

    def test_python_converter_exposes_bidirectional_api(self) -> None:
        converter = PythonConverter(widget_registry=build_builtin_registry())
        self.assertTrue(callable(converter.export_to_python))
        self.assertTrue(callable(converter.import_from_python))


if __name__ == "__main__":
    unittest.main()
