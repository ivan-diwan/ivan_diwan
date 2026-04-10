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

## Notes

- The editor currently targets `QWidget` and `QDialog` roots.
- The widget catalog is registry-driven in `form_constructor/registry/builtins.py`.
- Historical planning files in `dox/` are preserved as project context.
