@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 goto :fail
)

echo Upgrading pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :fail

echo Installing project with dev dependencies...
".venv\Scripts\python.exe" -m pip install -e .[dev]
if errorlevel 1 goto :fail

echo Environment is ready.
goto :end

:fail
echo Setup failed.
exit /b 1

:end
endlocal
