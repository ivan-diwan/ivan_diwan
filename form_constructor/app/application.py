from PySide6.QtWidgets import QApplication

from form_constructor.controller.document_controller import DocumentController
from form_constructor.registry.builtins import build_builtin_registry
from form_constructor.ui.main_editor.main_editor_window import MainEditorWindow


class FormConstructorApplication:
    def __init__(self) -> None:
        self.qt_app = QApplication.instance() or QApplication([])
        self.registry = build_builtin_registry()
        self.controller = DocumentController(widget_registry=self.registry)
        self.main_window = MainEditorWindow(controller=self.controller)

    def run(self) -> int:
        self.main_window.show()
        self.qt_app.processEvents()
        self.main_window.apply_screen_layout()
        return self.qt_app.exec()
