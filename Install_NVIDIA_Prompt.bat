@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title AI Generator - NVIDIA Prompt Support

if not exist ".venv\Scripts\python.exe" (
    echo Run Setup.bat before installing NVIDIA prompt support.
    pause
    exit /b 1
)

echo Installing CUDA-enabled PyTorch for compatible NVIDIA cards...
echo This download is large and can take several minutes.
".venv\Scripts\python.exe" -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
if errorlevel 1 goto :failed

echo Installing local prompt-editing packages...
".venv\Scripts\python.exe" -m pip install -U diffusers transformers accelerate safetensors sentencepiece
if errorlevel 1 goto :failed

echo.
echo NVIDIA prompt support was installed successfully.
echo The prompt model will download the first time Prompt Edit is enabled.
pause
exit /b 0

:failed
echo.
echo ERROR: NVIDIA prompt support could not be installed.
echo Update the NVIDIA driver and confirm that Setup.bat completed first.
pause
exit /b 1
