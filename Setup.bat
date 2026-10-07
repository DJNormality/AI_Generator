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
py -3.13 -c "import sys" >nul 2>&1 && set "PYTHON_CMD=py -3.13"
if not defined PYTHON_CMD python -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 13) else 1)" >nul 2>&1 && set "PYTHON_CMD=python"

if not defined PYTHON_CMD (
    echo ERROR: Python was not found.
    echo.
    echo Install 64-bit Python 3.13 from https://www.python.org/downloads/
    echo During installation, enable "Add Python to PATH".
    pause
    exit /b 1
)

if exist ".venv\Scripts\python.exe" (
    echo NOTE: An older .venv installation was found.
    echo This installer now uses the main AI Generator directory instead.
    echo The .venv folder will not be changed and can be removed after setup succeeds.
    echo.
)

if not exist "Scripts\python.exe" goto :create_environment
if not exist "pyvenv.cfg" goto :repair_environment
echo [1/4] Existing main-directory Python environment found.
goto :environment_ready

:repair_environment
echo [1/4] The Python environment is incomplete: pyvenv.cfg is missing.
echo Repairing the main-directory Python environment...
%PYTHON_CMD% -m venv .
if errorlevel 1 goto :failed
goto :environment_ready

:create_environment
echo [1/4] Creating the Python environment in the main directory...
%PYTHON_CMD% -m venv .
if errorlevel 1 goto :failed

:environment_ready

echo [2/4] Updating the package installer...
"Scripts\python.exe" -m pip install --upgrade pip wheel "setuptools==81.0.0"
if errorlevel 1 goto :failed

echo Installing Python 3.13-compatible numeric wheels...
"Scripts\python.exe" -m pip install --upgrade --no-cache-dir --only-binary=:all: "numpy>=2,<3" "ml_dtypes==0.6.0"
if errorlevel 1 goto :failed

echo [3/4] Installing AI Generator requirements...
"Scripts\python.exe" -m pip install -r requirements.txt
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
echo Models are downloaded when their associated options are first enabled.
echo ============================================================
pause
exit /b 0

:failed
echo.
echo ERROR: Setup did not complete.
echo Check the message above, confirm the internet connection, and run
echo Setup.bat again. Existing main-directory packages can be reused.
pause
exit /b 1
