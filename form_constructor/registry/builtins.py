from form_constructor.registry.definitions import PropertyDefinition, WidgetTypeDefinition
from form_constructor.registry.widget_registry import WidgetRegistry


def _geometry_locked_property() -> PropertyDefinition:
    return PropertyDefinition("geometry_locked", "bool", False, False, "checkbox")


def build_builtin_registry() -> WidgetRegistry:
    registry = WidgetRegistry()

    container_parent_types = [
        "FormRoot",
        "QWidget",
        "QFrame",
        "QGroupBox",
        "TabPage",
        "WizardPage",
        "ContainerContent",
        "SplitterPane",
    ]

    registry.register(
        WidgetTypeDefinition(
            type_name="QWidget",
            display_name="Widget",
            category="container",
            editor_kind="container",
            palette_visible=True,
            palette_group="Containers",
            creatable_by_user=True,
            name_prefix="widget",
            default_size=(320, 220),
            property_schema=[_geometry_locked_property()],
            allowed_parent_types=container_parent_types,
            allowed_child_types=["*"],
            qt_class_name="QWidget",
            description="Базовый пустой контейнер для размещения обычных объектов.",
        )
    )
    registry.register(
        WidgetTypeDefinition(
            type_name="QFrame",
            display_name="Frame",
            category="container",
            editor_kind="container",
            palette_visible=True,
            palette_group="Containers",
            creatable_by_user=True,
            name_prefix="frame",
            default_size=(320, 220),
            property_schema=[
                _geometry_locked_property(),
                PropertyDefinition(
                    "frame_shape",
                    "str",
                    False,
                    "StyledPanel",
                    "dropdown",
                    ["NoFrame", "Box", "Panel", "StyledPanel", "HLine", "VLine", "WinPanel"],
                ),
                PropertyDefinition(
                    "frame_shadow",
                    "str",
                    False,
                    "Raised",
                    "dropdown",
                    ["Plain", "Raised", "Sunken"],
                ),
            ],
            allowed_parent_types=container_parent_types,
            allowed_child_types=["*"],
            qt_class_name="QFrame",
            description="Контейнер с видимой рамкой вокруг содержимого.",
        )
    )
    registry.register(
        WidgetTypeDefinition(
            type_name="QGroupBox",
            display_name="Group Box",
            category="container",
            editor_kind="container",
            palette_visible=True,
            palette_group="Containers",
            creatable_by_user=True,
            name_prefix="group_box",
            default_size=(340, 240),
            property_schema=[
                _geometry_locked_property(),
                PropertyDefinition("title", "str", False, "Group", "line_edit"),
                PropertyDefinition("checkable", "bool", False, False, "checkbox"),
                PropertyDefinition("checked", "bool", False, False, "checkbox"),
            ],
            allowed_parent_types=container_parent_types,
            allowed_child_types=["*"],
            qt_class_name="QGroupBox",
            description="Контейнер с заголовком.",
        )
    )
    registry.register(
        WidgetTypeDefinition(
            type_name="QTabWidget",
            display_name="Tab Widget",
            category="special_container",
            editor_kind="special_container",
            palette_visible=True,
            palette_group="Special Containers",
            creatable_by_user=True,
            name_prefix="tab_widget",
            default_size=(420, 280),
            property_schema=[
                _geometry_locked_property(),
                PropertyDefinition("current_index", "int", False, 0, "spinbox"),
                PropertyDefinition("tabs_closable", "bool", False, False, "checkbox"),
            ],
            allowed_parent_types=[
                "FormRoot",
                "QWidget",
                "QFrame",
                "QGroupBox",
                "TabPage",
                "ContainerContent",
            ],
            allowed_child_types=["TabPage"],
            special_actions=[
                "add_tab_page",
                "remove_tab_page",
                "rename_tab_page",
                "set_current_tab",
            ],
            auto_create_children=["TabPage", "TabPage"],
            qt_class_name="QTabWidget",
            description="Контейнер со вкладками. Реальные дочерние объекты живут внутри TabPage.",
        )
    )
    registry.register(
        WidgetTypeDefinition(
            type_name="QScrollArea",
            display_name="Scroll Area",
            category="special_container",
            editor_kind="special_container",
            palette_visible=True,
            palette_group="Special Containers",
            creatable_by_user=True,
            name_prefix="scroll_area",
            default_size=(360, 240),
            property_schema=[
                _geometry_locked_property(),
                PropertyDefinition("widget_resizable", "bool", False, True, "checkbox"),
            ],
            allowed_parent_types=["FormRoot", "QWidget", "QFrame", "QGroupBox", "TabPage"],
            allowed_child_types=["ContainerContent"],
            special_actions=["get_scroll_content"],
            auto_create_children=["ContainerContent"],
            qt_class_name="QScrollArea",
            description="Прокручиваемый контейнер с одной внутренней областью содержимого.",
        )
    )
    registry.register(
        WidgetTypeDefinition(
            type_name="QSplitter",
            display_name="Splitter",
            category="special_container",
            editor_kind="special_container",
            palette_visible=True,
            palette_group="Special Containers",
            creatable_by_user=True,
            name_prefix="splitter",
            default_size=(420, 260),
            property_schema=[
                _geometry_locked_property(),
                PropertyDefinition(
                    "orientation",
                    "str",
                    False,
                    "horizontal",
                    "line_edit",
                    ["horizontal", "vertical"],
                ),
                PropertyDefinition("sizes", "list[int]", False, [210, 210], "line_edit"),
            ],
            allowed_parent_types=[
                "FormRoot",
                "QWidget",
                "QFrame",
                "QGroupBox",
                "TabPage",
                "StackPage",
                "ToolPage",
                "ContainerContent",
            ],
            allowed_child_types=["SplitterPane"],
            special_actions=["set_splitter_orientation", "set_splitter_sizes"],
            auto_create_children=["SplitterPane", "SplitterPane"],
            qt_class_name="QSplitter",
            description="Контейнер с двумя внутренними панелями и изменяемым разделителем.",
        )
    )
    registry.register(
        WidgetTypeDefinition(
            type_name="QWizard",
            display_name="Wizard",
            category="special_container",
            editor_kind="special_container",
            palette_visible=True,
            palette_group="Special Containers",
            creatable_by_user=True,
            name_prefix="wizard",
            default_size=(500, 360),
            property_schema=[
                _geometry_locked_property(),
                PropertyDefinition("window_title", "str", False, "Wizard", "line_edit"),
                PropertyDefinition("current_index", "int", False, 0, "spinbox"),
            ],
            allowed_parent_types=[
                "FormRoot",
                "QWidget",
                "QFrame",
                "QGroupBox",
                "TabPage",
                "ToolPage",
                "StackPage",
                "ContainerContent",
            ],
            allowed_child_types=["WizardPage"],
            special_actions=[
                "add_wizard_page",
                "remove_wizard_page",
                "rename_wizard_page",
                "set_current_wizard_page",
            ],
            auto_create_children=["WizardPage", "WizardPage"],
            qt_class_name="QWizard",
            description="Контейнер мастера с последовательными страницами.",
        )
    )
    registry.register(
        WidgetTypeDefinition(
            type_name="TabPage",
            display_name="Tab Page",
            category="internal",
            editor_kind="internal",
            palette_visible=False,
            palette_group="Internal",
            creatable_by_user=False,
            name_prefix="tab_page",
            default_size=(0, 0),
            property_schema=[
                PropertyDefinition("title", "str", False, "Tab", "line_edit"),
            ],
            allowed_parent_types=["QTabWidget"],
            allowed_child_types=["*"],
            qt_class_name="QWidget",
            geometry_edit_mode="hidden",
            movable=False,
            resizable=False,
            deletable_directly=False,
            description="Внутренняя страница QTabWidget. Управляется только через контейнер вкладок.",
        )
    )
    registry.register(
        WidgetTypeDefinition(
            type_name="ContainerContent",
            display_name="Scroll Content",
            category="internal",
            editor_kind="internal",
            palette_visible=False,
            palette_group="Internal",
            creatable_by_user=False,
            name_prefix="scroll_content",
            default_size=(0, 0),
            allowed_parent_types=["QScrollArea"],
            allowed_child_types=[
                "QLabel",
                "QPushButton",
                "QLineEdit",
                "QCheckBox",
                "QRadioButton",
                "QComboBox",
                "QListView",
                "QListWidget",
                "QTableView",
                "QTableWidget",
                "QTreeView",
                "QTreeWidget",
                "QDateEdit",
                "QTimeEdit",
                "QDateTimeEdit",
                "QCalendarWidget",
                "QFontComboBox",
                "QKeySequenceEdit",
                "QDial",
                "QLCDNumber",
                "QPlainTextEdit",
                "QTextEdit",
                "QProgressBar",
                "QSlider",
                "QDoubleSpinBox",
                "QSpinBox",
                "QWidget",
                "QFrame",
                "QGroupBox",
                "QTabWidget",
            ],
            qt_class_name="QWidget",
            geometry_edit_mode="hidden",
            movable=False,
            resizable=False,
            deletable_directly=False,
            description="Внутренняя область содержимого QScrollArea.",
        )
    )
    registry.register(
        WidgetTypeDefinition(
            type_name="SplitterPane",
            display_name="Splitter Pane",
            category="internal",
            editor_kind="internal",
            palette_visible=False,
            palette_group="Internal",
            creatable_by_user=False,
            name_prefix="splitter_pane",
            default_size=(0, 0),
            allowed_parent_types=["QSplitter"],
            allowed_child_types=[
                "QLabel",
                "QPushButton",
                "QLineEdit",
                "QCheckBox",
                "QRadioButton",
                "QComboBox",
                "QListView",
                "QListWidget",
                "QTableView",
                "QTableWidget",
                "QTreeView",
                "QTreeWidget",
                "QDateEdit",
                "QTimeEdit",
                "QDateTimeEdit",
                "QCalendarWidget",
                "QFontComboBox",
                "QKeySequenceEdit",
                "QDial",
                "QLCDNumber",
                "QPlainTextEdit",
                "QTextEdit",
                "QProgressBar",
                "QSlider",
                "QDoubleSpinBox",
                "QSpinBox",
                "QWidget",
                "QFrame",
                "QGroupBox",
            ],
            qt_class_name="QWidget",
            geometry_edit_mode="hidden",
            movable=False,
            resizable=False,
            deletable_directly=False,
            description="Внутренняя панель QSplitter.",
        )
    )
    registry.register(
        WidgetTypeDefinition(
            type_name="WizardPage",
            display_name="Wizard Page",
            category="internal",
            editor_kind="internal",
            palette_visible=False,
            palette_group="Internal",
            creatable_by_user=False,
            name_prefix="wizard_page",
            default_size=(0, 0),
            property_schema=[
                PropertyDefinition("title", "str", False, "Page", "line_edit"),
                PropertyDefinition("subtitle", "str", False, "", "multiline"),
            ],
            allowed_parent_types=["QWizard"],
            allowed_child_types=[
                "QLabel",
                "QPushButton",
                "QLineEdit",
                "QCheckBox",
                "QRadioButton",
                "QComboBox",
                "QListView",
                "QListWidget",
                "QTableView",
                "QTableWidget",
                "QTreeView",
                "QTreeWidget",
                "QDateEdit",
                "QTimeEdit",
                "QDateTimeEdit",
                "QCalendarWidget",
                "QFontComboBox",
                "QKeySequenceEdit",
                "QDial",
                "QLCDNumber",
                "QPlainTextEdit",
                "QTextEdit",
                "QProgressBar",
                "QSlider",
                "QDoubleSpinBox",
                "QSpinBox",
                "QWidget",
                "QFrame",
                "QGroupBox",
            ],
            qt_class_name="QWizardPage",
            geometry_edit_mode="hidden",
            movable=False,
            resizable=False,
            deletable_directly=False,
            description="Внутренняя страница QWizard.",
        )
    )

    common_leaf_parents = [
        "FormRoot",
        "QWidget",
        "QFrame",
        "QGroupBox",
        "TabPage",
        "WizardPage",
        "ContainerContent",
        "SplitterPane",
    ]

    registry.register(
        WidgetTypeDefinition(
            type_name="QListView",
            display_name="List View",
            category="leaf",
            editor_kind="leaf",
            palette_visible=True,
            palette_group="Data",
            creatable_by_user=True,
            name_prefix="list_view",
            default_size=(180, 120),
            property_schema=[
                _geometry_locked_property(),
                PropertyDefinition("model_items", "list[str]", True, [], "string_list"),
            ],
            allowed_parent_types=common_leaf_parents,
            qt_class_name="QListView",
            description="Представление списка на основе упрощенной QStringListModel с набором строк модели.",
        )
    )
    registry.register(
        WidgetTypeDefinition(
            type_name="QListWidget",
            display_name="List Widget",
            category="leaf",
            editor_kind="leaf",
            palette_visible=True,
            palette_group="Data",
            creatable_by_user=True,
            name_prefix="list_widget",
            default_size=(170, 110),
            property_schema=[
                _geometry_locked_property(),
                PropertyDefinition("items", "list[str]", True, [], "string_list"),
                PropertyDefinition("current_row", "int", True, -1, "integer"),
                PropertyDefinition("current_text", "str", True, "", "text"),
            ],
            allowed_parent_types=common_leaf_parents,
            qt_class_name="QListWidget",
            description="Список строк с возможностью выбрать текущую строку.",
        )
    )
    registry.register(
        WidgetTypeDefinition(
            type_name="QTreeView",
            display_name="Tree View",
            category="leaf",
            editor_kind="leaf",
            palette_visible=True,
            palette_group="Data",
            creatable_by_user=True,
            name_prefix="tree_view",
            default_size=(200, 140),
            property_schema=[
                _geometry_locked_property(),
                PropertyDefinition("header_labels", "list[str]", True, [], "string_list"),
            ],
            allowed_parent_types=common_leaf_parents,
            qt_class_name="QTreeView",
            description="Представление дерева на основе упрощенной QStandardItemModel с заголовками колонок.",
        )
    )
    registry.register(
        WidgetTypeDefinition(
            type_name="QTableView",
            display_name="Table View",
            category="leaf",
            editor_kind="leaf",
            palette_visible=True,
            palette_group="Data",
            creatable_by_user=True,
            name_prefix="table_view",
            default_size=(220, 140),
            property_schema=[
                _geometry_locked_property(),
                PropertyDefinition("column_count", "int", True, 3, "integer"),
                PropertyDefinition("header_labels", "list[str]", True, [], "string_list"),
            ],
            allowed_parent_types=common_leaf_parents,
            qt_class_name="QTableView",
            description="Табличное представление на основе упрощенной QStandardItemModel с заголовками колонок.",
        )
    )
    registry.register(
        WidgetTypeDefinition(
            type_name="QTableWidget",
            display_name="Table Widget",
            category="leaf",
            editor_kind="leaf",
            palette_visible=True,
            palette_group="Data",
            creatable_by_user=True,
            name_prefix="table_widget",
            default_size=(220, 140),
            property_schema=[
                _geometry_locked_property(),
                PropertyDefinition("row_count", "int", True, 3, "integer"),
                PropertyDefinition("column_count", "int", True, 3, "integer"),
                PropertyDefinition("horizontal_headers", "list[str]", True, [], "string_list"),
                PropertyDefinition("vertical_headers", "list[str]", True, [], "string_list"),
                PropertyDefinition("cell_values", "list[list[str]]", True, [], "table_text"),
            ],
            allowed_parent_types=common_leaf_parents,
            qt_class_name="QTableWidget",
            description="Таблица с настраиваемым числом строк, столбцов и заголовков.",
        )
    )
    registry.register(
        WidgetTypeDefinition(
            type_name="QTreeWidget",
            display_name="Tree Widget",
            category="leaf",
            editor_kind="leaf",
            palette_visible=True,
            palette_group="Data",
            creatable_by_user=True,
            name_prefix="tree_widget",
            default_size=(200, 140),
            property_schema=[
                _geometry_locked_property(),
                PropertyDefinition("column_count", "int", True, 1, "integer"),
                PropertyDefinition("header_labels", "list[str]", True, [], "string_list"),
                PropertyDefinition("tree_items", "list[tree_item]", True, [], "tree_text"),
            ],
            allowed_parent_types=common_leaf_parents,
            qt_class_name="QTreeWidget",
            description="Дерево с настраиваемым числом колонок и заголовками.",
        )
    )
    registry.register(
        WidgetTypeDefinition(
            type_name="QDateEdit",
            display_name="Date Edit",
            category="leaf",
            editor_kind="leaf",
            palette_visible=True,
            palette_group="Date and Time",
            creatable_by_user=True,
            name_prefix="date_edit",
            default_size=(120, 26),
            property_schema=[
                _geometry_locked_property(),
                PropertyDefinition("date", "date_string", True, "2026-01-01", "text"),
                PropertyDefinition("minimum_date", "date_string", True, "1900-01-01", "text"),
                PropertyDefinition("maximum_date", "date_string", True, "2100-12-31", "text"),
            ],
            allowed_parent_types=common_leaf_parents,
            qt_class_name="QDateEdit",
            description="Поле даты с нормализованным строковым хранением YYYY-MM-DD.",
        )
    )
    registry.register(
        WidgetTypeDefinition(
            type_name="QTimeEdit",
            display_name="Time Edit",
            category="leaf",
            editor_kind="leaf",
            palette_visible=True,
            palette_group="Date and Time",
            creatable_by_user=True,
            name_prefix="time_edit",
            default_size=(120, 26),
            property_schema=[
                _geometry_locked_property(),
                PropertyDefinition("time", "time_string", True, "12:00:00", "text"),
                PropertyDefinition("minimum_time", "time_string", True, "00:00:00", "text"),
                PropertyDefinition("maximum_time", "time_string", True, "23:59:59", "text"),
            ],
            allowed_parent_types=common_leaf_parents,
            qt_class_name="QTimeEdit",
            description="Поле времени с нормализованным строковым хранением HH:MM:SS.",
        )
    )
    registry.register(
        WidgetTypeDefinition(
            type_name="QDateTimeEdit",
            display_name="Date Time Edit",
            category="leaf",
            editor_kind="leaf",
            palette_visible=True,
            palette_group="Date and Time",
            creatable_by_user=True,
            name_prefix="datetime_edit",
            default_size=(160, 26),
            property_schema=[
                _geometry_locked_property(),
                PropertyDefinition("datetime", "datetime_string", True, "2026-01-01 12:00:00", "text"),
                PropertyDefinition("minimum_datetime", "datetime_string", True, "1900-01-01 00:00:00", "text"),
                PropertyDefinition("maximum_datetime", "datetime_string", True, "2100-12-31 23:59:59", "text"),
            ],
            allowed_parent_types=common_leaf_parents,
            qt_class_name="QDateTimeEdit",
            description="Поле даты и времени с нормализованным строковым хранением YYYY-MM-DD HH:MM:SS.",
        )
    )
    registry.register(
        WidgetTypeDefinition(
            type_name="QCalendarWidget",
            display_name="Calendar Widget",
            category="leaf",
            editor_kind="leaf",
            palette_visible=True,
            palette_group="Date and Time",
            creatable_by_user=True,
            name_prefix="calendar_widget",
            default_size=(260, 200),
            property_schema=[
                _geometry_locked_property(),
                PropertyDefinition("selected_date", "date_string", True, "2026-01-01", "text"),
                PropertyDefinition("minimum_date", "date_string", True, "1900-01-01", "text"),
                PropertyDefinition("maximum_date", "date_string", True, "2100-12-31", "text"),
            ],
            allowed_parent_types=common_leaf_parents,
            qt_class_name="QCalendarWidget",
            description="Календарный виджет с нормализованным хранением выбранной даты YYYY-MM-DD.",
        )
    )
    registry.register(
        WidgetTypeDefinition(
            type_name="QFontComboBox",
            display_name="Font Combo Box",
            category="leaf",
            editor_kind="leaf",
            palette_visible=True,
            palette_group="Input",
            creatable_by_user=True,
            name_prefix="font_combo_box",
            default_size=(180, 26),
            property_schema=[
                _geometry_locked_property(),
                PropertyDefinition("current_font_family", "str", True, "", "text"),
            ],
            allowed_parent_types=common_leaf_parents,
            qt_class_name="QFontComboBox",
            description="Комбобокс выбора семейства шрифта с базовым строковым хранением family.",
        )
    )
    registry.register(
        WidgetTypeDefinition(
            type_name="QKeySequenceEdit",
            display_name="Key Sequence Edit",
            category="leaf",
            editor_kind="leaf",
            palette_visible=True,
            palette_group="Input",
            creatable_by_user=True,
            name_prefix="key_sequence_edit",
            default_size=(180, 26),
            property_schema=[
                _geometry_locked_property(),
                PropertyDefinition("key_sequence", "str", True, "", "text"),
            ],
            allowed_parent_types=common_leaf_parents,
            qt_class_name="QKeySequenceEdit",
            description="Поле ввода сочетания клавиш с базовым строковым хранением последовательности.",
        )
    )
    registry.register(
        WidgetTypeDefinition(
            type_name="QDial",
            display_name="Dial",
            category="leaf",
            editor_kind="leaf",
            palette_visible=True,
            palette_group="Input",
            creatable_by_user=True,
            name_prefix="dial",
            default_size=(80, 80),
            property_schema=[
                _geometry_locked_property(),
                PropertyDefinition("value", "int", True, 0, "integer"),
                PropertyDefinition("minimum", "int", True, 0, "integer"),
                PropertyDefinition("maximum", "int", True, 100, "integer"),
                PropertyDefinition("step", "int", True, 1, "integer"),
            ],
            allowed_parent_types=common_leaf_parents,
            qt_class_name="QDial",
            description="Круговой числовой регулятор с базовыми целочисленными параметрами диапазона.",
        )
    )
    registry.register(
        WidgetTypeDefinition(
            type_name="QLCDNumber",
            display_name="LCD Number",
            category="leaf",
            editor_kind="leaf",
            palette_visible=True,
            palette_group="Numbers",
            creatable_by_user=True,
            name_prefix="lcd_number",
            default_size=(120, 40),
            property_schema=[
                _geometry_locked_property(),
                PropertyDefinition("value", "int", True, 0, "integer"),
                PropertyDefinition("digit_count", "int", True, 5, "integer"),
            ],
            allowed_parent_types=common_leaf_parents,
            qt_class_name="QLCDNumber",
            description="LCD-индикатор для отображения целочисленного значения с фиксированным числом разрядов.",
        )
    )
    registry.register(
        WidgetTypeDefinition(
            type_name="QPlainTextEdit",
            display_name="Plain Text Edit",
            category="leaf",
            editor_kind="leaf",
            palette_visible=True,
            palette_group="Text",
            creatable_by_user=True,
            name_prefix="plain_text_edit",
            default_size=(180, 90),
            property_schema=[
                _geometry_locked_property(),
                PropertyDefinition("text", "str", True, "", "multiline"),
                PropertyDefinition("placeholder", "str", True, "", "text"),
                PropertyDefinition("read_only", "bool", True, False, "checkbox"),
            ],
            allowed_parent_types=common_leaf_parents,
            qt_class_name="QPlainTextEdit",
            description="Многострочное plain-text поле без rich-text возможностей.",
        )
    )
    registry.register(
        WidgetTypeDefinition(
            type_name="QTextEdit",
            display_name="Text Edit",
            category="leaf",
            editor_kind="leaf",
            palette_visible=True,
            palette_group="Text",
            creatable_by_user=True,
            name_prefix="text_edit",
            default_size=(180, 90),
            property_schema=[
                _geometry_locked_property(),
                PropertyDefinition("text", "str", True, "", "multiline"),
                PropertyDefinition("placeholder", "str", True, "", "text"),
                PropertyDefinition("read_only", "bool", True, False, "checkbox"),
            ],
            allowed_parent_types=common_leaf_parents,
            qt_class_name="QTextEdit",
            description="Многострочное текстовое поле в plain-text режиме.",
        )
    )
    registry.register(
        WidgetTypeDefinition(
            type_name="QProgressBar",
            display_name="Progress Bar",
            category="leaf",
            editor_kind="leaf",
            palette_visible=True,
            palette_group="Numbers",
            creatable_by_user=True,
            name_prefix="progress_bar",
            default_size=(140, 24),
            property_schema=[
                _geometry_locked_property(),
                PropertyDefinition("value", "int", True, 0, "integer"),
                PropertyDefinition("minimum", "int", True, 0, "integer"),
                PropertyDefinition("maximum", "int", True, 100, "integer"),
                PropertyDefinition("text_visible", "bool", True, True, "checkbox"),
            ],
            allowed_parent_types=common_leaf_parents,
            qt_class_name="QProgressBar",
            description="Индикатор прогресса для отображения значения в диапазоне.",
        )
    )
    registry.register(
        WidgetTypeDefinition(
            type_name="QSlider",
            display_name="Slider",
            category="leaf",
            editor_kind="leaf",
            palette_visible=True,
            palette_group="Numbers",
            creatable_by_user=True,
            name_prefix="slider",
            default_size=(140, 24),
            property_schema=[
                _geometry_locked_property(),
                PropertyDefinition(
                    "orientation",
                    "str",
                    True,
                    "horizontal",
                    "dropdown",
                    allowed_values=["horizontal", "vertical"],
                ),
                PropertyDefinition("value", "int", True, 0, "integer"),
                PropertyDefinition("minimum", "int", True, 0, "integer"),
                PropertyDefinition("maximum", "int", True, 100, "integer"),
                PropertyDefinition("step", "int", True, 1, "integer"),
            ],
            allowed_parent_types=common_leaf_parents,
            qt_class_name="QSlider",
            description="Ползунок для выбора целого значения в заданном диапазоне.",
        )
    )
    registry.register(
        WidgetTypeDefinition(
            type_name="QDoubleSpinBox",
            display_name="Double Spin Box",
            category="leaf",
            editor_kind="leaf",
            palette_visible=True,
            palette_group="Numbers",
            creatable_by_user=True,
            name_prefix="double_spin_box",
            default_size=(110, 26),
            property_schema=[
                _geometry_locked_property(),
                PropertyDefinition("value", "float", True, 0.0, "float"),
                PropertyDefinition("minimum", "float", True, 0.0, "float"),
                PropertyDefinition("maximum", "float", True, 99.0, "float"),
                PropertyDefinition("step", "float", True, 1.0, "float"),
                PropertyDefinition("decimals", "int", True, 2, "integer"),
                PropertyDefinition("prefix", "str", True, "", "text"),
                PropertyDefinition("suffix", "str", True, "", "text"),
            ],
            allowed_parent_types=common_leaf_parents,
            qt_class_name="QDoubleSpinBox",
            description="Поле ввода дробного числа со стрелками, точностью и ограничениями диапазона.",
        )
    )
    registry.register(
        WidgetTypeDefinition(
            type_name="QSpinBox",
            display_name="Spin Box",
            category="leaf",
            editor_kind="leaf",
            palette_visible=True,
            palette_group="Numbers",
            creatable_by_user=True,
            name_prefix="spin_box",
            default_size=(100, 26),
            property_schema=[
                _geometry_locked_property(),
                PropertyDefinition("value", "int", True, 0, "integer"),
                PropertyDefinition("minimum", "int", True, 0, "integer"),
                PropertyDefinition("maximum", "int", True, 99, "integer"),
                PropertyDefinition("step", "int", True, 1, "integer"),
                PropertyDefinition("prefix", "str", True, "", "text"),
                PropertyDefinition("suffix", "str", True, "", "text"),
            ],
            allowed_parent_types=common_leaf_parents,
            qt_class_name="QSpinBox",
            description="Поле ввода целого числа со стрелками и ограничениями диапазона.",
        )
    )
    registry.register(
        WidgetTypeDefinition(
            type_name="QLabel",
            display_name="Label",
            category="leaf",
            editor_kind="leaf",
            palette_visible=True,
            palette_group="Basic",
            creatable_by_user=True,
            name_prefix="label",
            default_size=(120, 30),
            property_schema=[
                _geometry_locked_property(),
                PropertyDefinition("text", "str", True, "Label", "line_edit"),
            ],
            allowed_parent_types=common_leaf_parents,
            qt_class_name="QLabel",
            description="Статическая текстовая надпись.",
        )
    )
    registry.register(
        WidgetTypeDefinition(
            type_name="QPushButton",
            display_name="Push Button",
            category="leaf",
            editor_kind="leaf",
            palette_visible=True,
            palette_group="Basic",
            creatable_by_user=True,
            name_prefix="push_button",
            default_size=(140, 36),
            property_schema=[
                _geometry_locked_property(),
                PropertyDefinition("text", "str", True, "Button", "line_edit"),
            ],
            allowed_parent_types=common_leaf_parents,
            qt_class_name="QPushButton",
            description="Обычная кнопка действия.",
        )
    )
    registry.register(
        WidgetTypeDefinition(
            type_name="QLineEdit",
            display_name="Line Edit",
            category="leaf",
            editor_kind="leaf",
            palette_visible=True,
            palette_group="Basic",
            creatable_by_user=True,
            name_prefix="line_edit",
            default_size=(180, 32),
            property_schema=[
                _geometry_locked_property(),
                PropertyDefinition("text", "str", False, "", "line_edit"),
                PropertyDefinition("placeholder", "str", False, "Enter text", "line_edit"),
            ],
            allowed_parent_types=common_leaf_parents,
            qt_class_name="QLineEdit",
            description="Однострочное текстовое поле.",
        )
    )
    registry.register(
        WidgetTypeDefinition(
            type_name="QCheckBox",
            display_name="Check Box",
            category="leaf",
            editor_kind="leaf",
            palette_visible=True,
            palette_group="Basic",
            creatable_by_user=True,
            name_prefix="check_box",
            default_size=(140, 28),
            property_schema=[
                _geometry_locked_property(),
                PropertyDefinition("text", "str", False, "Check", "line_edit"),
                PropertyDefinition("checked", "bool", False, False, "checkbox"),
            ],
            allowed_parent_types=common_leaf_parents,
            qt_class_name="QCheckBox",
            description="Независимый логический переключатель.",
        )
    )
    registry.register(
        WidgetTypeDefinition(
            type_name="QRadioButton",
            display_name="Radio Button",
            category="leaf",
            editor_kind="leaf",
            palette_visible=True,
            palette_group="Basic",
            creatable_by_user=True,
            name_prefix="radio_button",
            default_size=(140, 28),
            property_schema=[
                _geometry_locked_property(),
                PropertyDefinition("text", "str", False, "Radio", "line_edit"),
                PropertyDefinition("checked", "bool", False, False, "checkbox"),
            ],
            allowed_parent_types=common_leaf_parents,
            qt_class_name="QRadioButton",
            description="Элемент выбора из взаимоисключающей группы.",
        )
    )
    registry.register(
        WidgetTypeDefinition(
            type_name="QComboBox",
            display_name="Combo Box",
            category="leaf",
            editor_kind="leaf",
            palette_visible=True,
            palette_group="Basic",
            creatable_by_user=True,
            name_prefix="combo_box",
            default_size=(160, 30),
            property_schema=[
                _geometry_locked_property(),
                PropertyDefinition("items", "list[str]", False, ["One", "Two"], "string_list"),
                PropertyDefinition("current_index", "int", False, 0, "spinbox"),
                PropertyDefinition("editable", "bool", False, False, "checkbox"),
            ],
            allowed_parent_types=common_leaf_parents,
            qt_class_name="QComboBox",
            description="Выпадающий список со значениями для выбора.",
        )
    )

    return registry
