# Form Constructor

Desktop form constructor for `PySide6`.

The project provides:
- a visual editor for building widget trees
- a JSON document format for saved forms
- Python export to runnable `PySide6` source
- Python import back into the internal document model
- smoke tests for the editor, document pipeline, and conversion flow

## Project Layout

```text
form_constructor/
  app/            Application bootstrap
  canvas/         Visual canvas and item views
  controller/     Editing orchestration and signals
  conversion/     Python export/import
  document/       Document model and validation
  factory/        Runtime widget creation
  registry/       Built-in widget catalog and schemas
  serialization/  JSON read/write
  ui/             Main windows and property editors
  utils/          Shared helpers
tests/            Smoke and round-trip tests
dox/              Historical notes and planning documents
```

## Requirements

- Python 3.11+
- `PySide6`
- `pytest`

## Install

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e .[dev]
```

Or from Windows Explorer / `cmd`:

```bat
setup_windows_env.bat
```

## Run

```powershell
python -m form_constructor.main
```

Or via the console script:

```powershell
form-constructor
```

Or from the project root on Windows:

```bat
run_form_constructor.bat
```

## Test

For headless environments, use the Qt offscreen backend:

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
python -m pytest -q
```

Or from the project root on Windows:

```bat
run_tests.bat
```

## Current Status

The repository is now versioned from a clean baseline commit and uses:
- `main` for the stable baseline
- feature branches for further work

The current architecture cleanup stage is complete:
- `DocumentController` delegates file I/O through `document_io_service.py`
- `FormDocument` delegates widget property normalization through `property_normalizer.py`
- `PythonImporter` reuses the shared property normalizer for supported widget-state normalization
- `WidgetFactory` is now flatter and grouped around clearer runtime-application helpers
- `PropertyPanel` is leaner and delegates editor configuration to `PropertyEditorFactory`
- editor save/export paths now validate the active document before file operations
- property editor parse errors are surfaced immediately in the editor message log
- `WidgetRegistry` exposes grouped palette helpers for safer future catalog expansion

## Architecture Boundaries

The intended responsibility split is:
- `controller/`: editor orchestration, selection flow, UI-facing commands
- `document/`: document state, mutation rules, property normalization, validation
- `factory/`: runtime widget creation and application of already-normalized state
- `conversion/`: format translation and diagnostics for Python import/export
- `ui/`: editor widgets, interaction wiring, schema-driven editing

In practical terms:
- `WidgetPropertyNormalizer` is the main place for coercing raw widget property values
- `DocumentValidator` is the main place for rejecting invalid document state
- `WidgetFactory` should apply state, not redefine validation rules
- importer/exporter should translate data and surface diagnostics, not own duplicate business rules when a shared normalizer already exists

## Notes

- The editor currently targets `QWidget` and `QDialog` roots.
- The widget catalog is registry-driven in `form_constructor/registry/builtins.py`.
- Historical planning files in `dox/` are preserved as project context.
