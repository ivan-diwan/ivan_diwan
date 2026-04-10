@echo off
setlocal

cd /d "%~dp0"
set QT_QPA_PLATFORM=offscreen

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m pytest -q
    goto :end
)

where py >nul 2>nul
if %errorlevel%==0 (
    py -m pytest -q
    goto :end
)

python -m pytest -q

:end
endlocal
