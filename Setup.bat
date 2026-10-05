@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title AI Generator - First-Time Setup

echo ============================================================
echo                  AI GENERATOR SETUP
echo ============================================================
echo.

if not exist "main.py" (
    echo ERROR: main.py was not found in this folder.
    echo Extract the complete AI Generator package before running setup.
    pause
    exit /b 1
)

if not exist "requirements.txt" (
    echo ERROR: requirements.txt was not found in this folder.
    pause
    exit /b 1
)

set "PYTHON_CMD="
py -3.11 -c "import sys" >nul 2>&1 && set "PYTHON_CMD=py -3.11"
if not defined PYTHON_CMD py -3.12 -c "import sys" >nul 2>&1 && set "PYTHON_CMD=py -3.12"
if not defined PYTHON_CMD python -c "import sys" >nul 2>&1 && set "PYTHON_CMD=python"

if not defined PYTHON_CMD (
    echo ERROR: Python was not found.
    echo.
    echo Install 64-bit Python 3.11 from https://www.python.org/downloads/
    echo During installation, enable "Add Python to PATH".
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo [1/4] Creating a private Python environment...
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 goto :failed
) else (
    echo [1/4] Existing Python environment found.
)

echo [2/4] Updating the package installer...
".venv\Scripts\python.exe" -m pip install --upgrade pip setuptools wheel
if errorlevel 1 goto :failed

echo [3/4] Installing AI Generator requirements...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :failed

echo [4/4] Creating application folders...
for %%D in (models resources source target result temp_processing) do (
    if not exist "%%D" mkdir "%%D"
)

echo.
echo ============================================================
echo Setup completed successfully.
echo.
echo Run Run.bat to start AI Generator.
echo Run Install_NVIDIA_Prompt.bat only if local prompt editing is needed.
echo Run Configure_Cloud_API_Key.bat to enable optional Cloud prompt editing.
echo Run Configure_HuggingFace_Token.bat to enable Qwen Cloud editing.
echo Run Configure_A2E_API_Token.bat to enable A2E prompt editing.
echo Models are downloaded when their associated options are first enabled.
echo ============================================================
pause
exit /b 0

:failed
echo.
echo ERROR: Setup did not complete.
echo Check the message above, confirm the internet connection, and run
echo Setup.bat again. The existing .venv can be reused.
pause
exit /b 1
