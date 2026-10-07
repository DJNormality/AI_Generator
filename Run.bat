@echo off
setlocal EnableExtensions
cd /d "%~dp0"

if not exist "Scripts\pythonw.exe" goto :run_setup
if not exist "pyvenv.cfg" goto :run_setup
goto :environment_ready

:run_setup
    echo AI Generator has not been installed yet.
    echo Starting setup or repairing an incomplete Python environment...
    call "Setup.bat"
    if errorlevel 1 exit /b 1

:environment_ready

if not exist "main.py" (
    echo ERROR: main.py was not found.
    pause
    exit /b 1
)

start "" "Scripts\pythonw.exe" "main.py"
exit /b 0
