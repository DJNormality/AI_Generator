@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
title AI Generator - 3D Reconstruction Setup
color 0A

echo ============================================================
echo        AI Generator - 3D Reconstruction Setup
echo ============================================================
echo.

set "PYTHON_EXE=%CD%\Scripts\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=%CD%\.venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" (
    where python >nul 2>nul
    if errorlevel 1 (
        echo ERROR: Python was not found.
        echo Run Setup.bat first, then run this file again.
        pause
        exit /b 1
    )
    set "PYTHON_EXE=python"
)

echo Python: %PYTHON_EXE%
echo.
echo [1/4] Installing the local reconstruction packages...
"%PYTHON_EXE%" -m pip install --upgrade "setuptools<82"
if errorlevel 1 (
    echo ERROR: Could not apply the required setuptools version.
    pause
    exit /b 1
)
"%PYTHON_EXE%" -m pip install --upgrade "transformers" "accelerate" "safetensors" "trimesh" "huggingface_hub"
if errorlevel 1 (
    echo.
    echo ERROR: Package installation failed.
    pause
    exit /b 1
)

"%PYTHON_EXE%" -c "import torch; from torch._subclasses.fake_tensor import is_fake_tensor; print(torch.__version__)" >nul 2>nul
if errorlevel 1 (
    echo.
    echo A mismatched or incomplete PyTorch installation was detected.
    echo Starting the automatic CUDA 12.8 repair...
    call "%CD%\Repair_PyTorch.bat" nopause
    if errorlevel 1 (
        echo ERROR: PyTorch could not be repaired.
        pause
        exit /b 1
    )
)

if not exist "%CD%\models" mkdir "%CD%\models"
if not exist "%CD%\tools" mkdir "%CD%\tools"

set "DEPTH_DIR=%CD%\models\Depth-Anything-V2-Small-hf"
echo.
echo [2/4] Checking the Depth Anything V2 model...
if exist "%DEPTH_DIR%\model.safetensors" if exist "%DEPTH_DIR%\config.json" goto depth_ready
echo Downloading Depth Anything V2 Small to:
echo %DEPTH_DIR%
"%PYTHON_EXE%" -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='depth-anything/Depth-Anything-V2-Small-hf', local_dir=r'%DEPTH_DIR%')"
if errorlevel 1 (
    echo.
    echo WARNING: The model download failed. Check the internet connection,
    echo then run this setup again. COLMAP setup will continue.
) else (
    echo Model download complete.
)
:depth_ready
> "%CD%\tools\depth_model_location.txt" echo %DEPTH_DIR%

echo.
echo [3/4] Looking for a complete COLMAP installation...
set "COLMAP_LAUNCHER="
set "COLMAP_ROOT="
for %%D in ("%CD%\tools\COLMAP" "%CD%\COLMAP" "C:\Program Files\COLMAP" "C:\COLMAP") do (
    if not defined COLMAP_LAUNCHER call :CHECK_COLMAP "%%~fD"
)

if not defined COLMAP_LAUNCHER (
    echo.
    echo COLMAP was not found automatically.
    echo Extract the COMPLETE COLMAP Windows folder. Do not move colmap.exe alone.
    echo You can paste its folder path below, or press ENTER to skip it.
    set /p "COLMAP_ROOT=COLMAP folder: "
    if defined COLMAP_ROOT call :CHECK_COLMAP "!COLMAP_ROOT!"
)

if defined COLMAP_LAUNCHER (
    > "%CD%\tools\colmap_location.txt" echo !COLMAP_LAUNCHER!
    echo COLMAP launcher: !COLMAP_LAUNCHER!
    if defined QT_PLATFORM_DIR echo Qt plugin folder: !QT_PLATFORM_DIR!
) else (
    echo COLMAP was skipped or its complete folder was not found.
    echo Panorama Depth will still work for the Autohome interior images.
)

echo.
echo [4/4] Verifying the installation...
"%PYTHON_EXE%" -c "import torch; print('Torch:',torch.__version__); print('CUDA build:',torch.version.cuda); print('CUDA available:',torch.cuda.is_available()); print('GPU:',torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'not detected')"
if errorlevel 1 (
    echo ERROR: PyTorch could not be imported.
    echo Run Repair_PyTorch.bat, then run this setup again.
    pause
    exit /b 1
)
"%PYTHON_EXE%" -c "import transformers, safetensors, trimesh; print('Transformers:',transformers.__version__); print('Safetensors and Trimesh: ready')"
if errorlevel 1 (
    echo ERROR: The 3D reconstruction support packages could not be imported.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo Setup complete.
echo.
echo For the supplied Autohome panorama:
echo   Models ^> Create ^> Engine ^> Panorama depth
echo.
echo Use COLMAP only for photos or video where the camera physically moves.
echo ============================================================
pause
exit /b 0

:CHECK_COLMAP
set "CHECK_ROOT=%~1"
if not exist "!CHECK_ROOT!" exit /b 0
if exist "!CHECK_ROOT!\COLMAP.bat" set "COLMAP_LAUNCHER=!CHECK_ROOT!\COLMAP.bat"
if not defined COLMAP_LAUNCHER if exist "!CHECK_ROOT!\bin\colmap.exe" set "COLMAP_LAUNCHER=!CHECK_ROOT!\bin\colmap.exe"
if not defined COLMAP_LAUNCHER if exist "!CHECK_ROOT!\colmap.exe" set "COLMAP_LAUNCHER=!CHECK_ROOT!\colmap.exe"
if not defined COLMAP_LAUNCHER exit /b 0
set "QT_PLATFORM_DIR="
for /f "delims=" %%Q in ('dir /s /b "!CHECK_ROOT!\qwindows.dll" 2^>nul') do if not defined QT_PLATFORM_DIR set "QT_PLATFORM_DIR=%%~dpQ"
if not defined QT_PLATFORM_DIR (
    echo WARNING: Found COLMAP but qwindows.dll is missing from !CHECK_ROOT!
    echo Download or extract the complete COLMAP Windows package.
    set "COLMAP_LAUNCHER="
)
exit /b 0
