@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title AI Generator - Build Windows EXE

echo.
echo ============================================================
echo   AI Generator - Windows EXE Builder
echo ============================================================
echo.

set "PYTHON_EXE="
set "PYTHON_ARGS="
if exist "Scripts\python.exe" set "PYTHON_EXE=%CD%\Scripts\python.exe"
if not defined PYTHON_EXE if exist ".venv\Scripts\python.exe" set "PYTHON_EXE=%CD%\.venv\Scripts\python.exe"
if not defined PYTHON_EXE where py >nul 2>nul && set "PYTHON_EXE=py" && set "PYTHON_ARGS=-3.13"
if not defined PYTHON_EXE where python >nul 2>nul && set "PYTHON_EXE=python"

if not defined PYTHON_EXE (
    echo ERROR: Python was not found.
    echo Run Setup.bat first, then run Build_EXE.bat again.
    pause
    exit /b 1
)

if not exist "main.py" (
    echo ERROR: main.py must be beside Build_EXE.bat.
    pause
    exit /b 1
)
if not exist "AI_Generator.spec" (
    echo ERROR: AI_Generator.spec is missing.
    pause
    exit /b 1
)

echo Python command: "%PYTHON_EXE%" %PYTHON_ARGS%
echo Checking the numerical libraries required by InsightFace...
"%PYTHON_EXE%" %PYTHON_ARGS% -c "import numpy, scipy, scipy.special, scipy.spatial, sklearn, skimage; print('SciPy numerical stack is healthy.')" >nul 2>nul
if errorlevel 1 (
    echo SciPy is damaged or incompatible with this Python installation.
    echo Reinstalling compatible precompiled Python 3.13 wheels...
    "%PYTHON_EXE%" %PYTHON_ARGS% -m pip install --disable-pip-version-check --no-cache-dir --only-binary=:all: --upgrade --force-reinstall "numpy>=2,<3" scipy scikit-learn scikit-image
    if errorlevel 1 goto :failed
)

echo Verifying InsightFace imports before starting PyInstaller...
"%PYTHON_EXE%" %PYTHON_ARGS% -c "import scipy, insightface; print('InsightFace import passed:', insightface.__version__)"
if errorlevel 1 (
    echo ERROR: InsightFace still cannot import. The EXE build was stopped so it does not produce an incomplete application.
    goto :failed
)

echo Installing the EXE builder without upgrading project dependencies...
"%PYTHON_EXE%" %PYTHON_ARGS% -m pip install --disable-pip-version-check "pyinstaller>=6.16"
if errorlevel 1 goto :failed

if not exist "resources" mkdir "resources"
if not exist "resources\AI_Generator.ico" if exist "icon_resources\AI_Generator.ico" copy /y "icon_resources\AI_Generator.ico" "resources\AI_Generator.ico" >nul
if not exist "resources\AI_Generator.png" if exist "icon_resources\AI_Generator.png" copy /y "icon_resources\AI_Generator.png" "resources\AI_Generator.png" >nul

echo.
echo Building the no-console one-folder application...
"%PYTHON_EXE%" %PYTHON_ARGS% -m PyInstaller --noconfirm --clean "AI_Generator.spec"
if errorlevel 1 goto :failed

if exist "models" xcopy "models" "dist\AI_Generator\models\" /E /I /Y >nul
if exist "tools" xcopy "tools" "dist\AI_Generator\tools\" /E /I /Y >nul
if exist "config.example.json" copy /y "config.example.json" "dist\AI_Generator\config.example.json" >nul
if exist "README.md" copy /y "README.md" "dist\AI_Generator\README.md" >nul

echo Creating AI_Generator_Windows_EXE.zip...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference='Stop'; $zip=Join-Path (Get-Location) 'AI_Generator_Windows_EXE.zip'; if(Test-Path $zip){Remove-Item $zip -Force}; Compress-Archive -Path 'dist\AI_Generator\*' -DestinationPath $zip -CompressionLevel Optimal"
if errorlevel 1 goto :failed

echo.
echo BUILD COMPLETE
echo EXE folder: %CD%\dist\AI_Generator
echo Program:    %CD%\dist\AI_Generator\AI Generator.exe
echo ZIP:        %CD%\AI_Generator_Windows_EXE.zip
echo.
pause
exit /b 0

:failed
echo.
echo BUILD FAILED. Review the error above.
echo The existing project files were not removed.
pause
exit /b 1
