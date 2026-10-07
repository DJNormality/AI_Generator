@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title AI Generator - NVIDIA Prompt Support

if not exist "Scripts\python.exe" (
    echo Run Setup.bat before installing NVIDIA prompt support.
    pause
    exit /b 1
)

echo Installing CUDA-enabled PyTorch for compatible NVIDIA cards...
echo This download is large and can take several minutes.
"Scripts\python.exe" -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
if errorlevel 1 goto :failed

echo Installing local prompt-editing packages...
"Scripts\python.exe" -m pip install -U "transformers>=5.17" accelerate safetensors sentencepiece
if errorlevel 1 goto :failed

echo Installing the current Diffusers build for Qwen Image 2.1...
"Scripts\python.exe" -m pip install -U "git+https://github.com/huggingface/diffusers.git"
if errorlevel 1 goto :failed

echo Applying the PyTorch-compatible setuptools version...
"Scripts\python.exe" -m pip install --upgrade "setuptools==81.0.0"
if errorlevel 1 goto :failed

echo.
echo NVIDIA prompt support was installed successfully.
echo The selected prompt model will download the first time it is enabled.
echo Qwen Image 2.1 is about 33 GB and requires the complete repository.
pause
exit /b 0

:failed
echo.
echo ERROR: NVIDIA prompt support could not be installed.
echo Update the NVIDIA driver and confirm that Setup.bat completed first.
pause
exit /b 1
