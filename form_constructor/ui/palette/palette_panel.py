from PySide6.QtCore import QMimeData, Qt
from PySide6.QtWidgets import (
    QLabel,
    QPlainTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from form_constructor.registry.widget_registry import WidgetRegistry


class PaletteTreeWidget(QTreeWidget):
    def mimeData(self, items):
        mime_data = QMimeData()
        if items:
            type_name = items[0].data(0, Qt.ItemDataRole.UserRole)
            if type_name:
                mime_data.setText(str(type_name))
        return mime_data


class PalettePanel(QWidget):
    def __init__(self, widget_registry: WidgetRegistry, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._widget_registry = widget_registry
        self._definitions_by_type = {
            definition.type_name: definition
            for definition in widget_registry.list_palette_types()
        }

        self._tree = PaletteTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setDragEnabled(True)
        self._tree.setRootIsDecorated(True)
        self._tree.setIndentation(14)
        self._tree.setMinimumHeight(220)

        self._description_title = QLabel("Описание объекта")
        self._description_view = QPlainTextEdit()
        self._description_view.setReadOnly(True)
        self._description_view.setFixedHeight(72)
        self._description_view.setPlaceholderText(
            "Выберите объект в дереве, чтобы увидеть его описание."
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._tree, 1)
        layout.addWidget(self._description_title)
        layout.addWidget(self._description_view, 0)

        self._populate_tree()
        self._tree.currentItemChanged.connect(self._update_description)
        current_item = self._tree.currentItem()
        if current_item is not None:
            self._update_description(current_item, None)

    def _populate_tree(self) -> None:
        groups: dict[str, QTreeWidgetItem] = {}
        for group_name, definitions in self._widget_registry.list_palette_types_by_group().items():
            group_item = QTreeWidgetItem([group_name])
            group_item.setFlags(
                group_item.flags() & ~Qt.ItemFlag.ItemIsDragEnabled
            )
            self._tree.addTopLevelItem(group_item)
            groups[group_name] = group_item

            for definition in definitions:
                child_item = QTreeWidgetItem([definition.display_name])
                child_item.setData(0, Qt.ItemDataRole.UserRole, definition.type_name)
                group_item.addChild(child_item)

        for group_item in groups.values():
            group_item.setExpanded(True)

        first_leaf = self._first_leaf_item()
        if first_leaf is not None:
            self._tree.setCurrentItem(first_leaf)

    def _first_leaf_item(self) -> QTreeWidgetItem | None:
        for index in range(self._tree.topLevelItemCount()):
            group_item = self._tree.topLevelItem(index)
            if group_item.childCount() > 0:
                return group_item.child(0)
        return None

    def _update_description(
        self,
        current: QTreeWidgetItem | None,
        previous: QTreeWidgetItem | None,
    ) -> None:
        del previous
        if current is None:
            self._description_view.clear()
            return

        type_name = current.data(0, Qt.ItemDataRole.UserRole)
        if not type_name:
            self._description_view.clear()
            return

        definition = self._definitions_by_type.get(str(type_name))
        if definition is None:
            self._description_view.clear()
            return
        self._description_view.setPlainText(definition.description)
