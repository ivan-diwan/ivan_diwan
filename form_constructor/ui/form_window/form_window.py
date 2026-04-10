from PySide6.QtCore import QRect
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QMainWindow

from form_constructor.canvas.canvas_editor import CanvasEditor
from form_constructor.controller.document_controller import DocumentController
from form_constructor.document.form_document import FormDocument


class FormWindow(QMainWindow):
    def __init__(
        self,
        document: FormDocument,
        controller: DocumentController,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._controller = controller
        self._canvas = CanvasEditor(controller=controller)
        self.setCentralWidget(self._canvas)
        self._delete_shortcut = QShortcut(QKeySequence("Del"), self)
        self._delete_shortcut.activated.connect(self._controller.delete_selected_entity)
        self.set_document(document)

    def set_document(self, document: FormDocument) -> None:
        form_root = document.get_form_root()
        self.setWindowTitle(form_root.window_title)
        self._canvas.set_document(document)
        self.adjustSize()

    def select_entity(self, entity_id: str | None) -> None:
        self._canvas.select_entity(entity_id)

    def rebuild_canvas(self) -> None:
        self._canvas.rebuild_all()

    def handle_entity_update(self, entity) -> None:
        self._canvas.handle_entity_update(entity)

    def apply_screen_layout(self, screen_geometry: QRect) -> None:
        editor_width = max(360, screen_geometry.width() // 4)
        form_width = max(480, screen_geometry.width() - editor_width)
        left, top, right, bottom = self._frame_margins()
        self.setGeometry(
            screen_geometry.x() + editor_width + left,
            screen_geometry.y() + top,
            max(320, form_width - left - right),
            max(240, screen_geometry.height() - top - bottom),
        )

    def _frame_extra(self) -> tuple[int, int]:
        frame = self.frameGeometry()
        client = self.geometry()
        return (
            max(0, frame.width() - client.width()),
            max(0, frame.height() - client.height()),
        )

    def _frame_margins(self) -> tuple[int, int, int, int]:
        frame = self.frameGeometry()
        client = self.geometry()
        left = max(0, client.x() - frame.x())
        top = max(0, client.y() - frame.y())
        right = max(0, frame.right() - client.right())
        bottom = max(0, frame.bottom() - client.bottom())
        return left, top, right, bottom
