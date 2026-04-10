@echo off
setlocal

cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m form_constructor.main
    goto :end
)

where py >nul 2>nul
if %errorlevel%==0 (
    py -m form_constructor.main
    goto :end
)

python -m form_constructor.main

:end
endlocal
