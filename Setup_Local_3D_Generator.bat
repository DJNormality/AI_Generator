@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title AI Generator - Install Local 3D Generator
echo ============================================================
echo        AI Generator - Offline 3D Reconstruction Setup
echo ============================================================
echo.
echo This installs Stable Fast 3D separately under tools\stable-fast-3d.
echo It will not change AI Generator's main Python environment.
echo Internet is required for installation and the first model download.
echo.
where git >nul 2>nul || (echo ERROR: Git for Windows is required.& pause & exit /b 1)
where uv >nul 2>nul
if errorlevel 1 (
  powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex" || (echo ERROR: uv installation failed.& pause & exit /b 1)
  set "PATH=%USERPROFILE%\.local\bin;%PATH%"
)
if not exist "tools" mkdir "tools"
if not exist "tools\stable-fast-3d\.git" (
  git clone https://github.com/Stability-AI/stable-fast-3d.git "tools\stable-fast-3d" || (echo ERROR: Download failed.& pause & exit /b 1)
)
pushd "tools\stable-fast-3d"
if not exist ".venv\Scripts\python.exe" call uv venv --python 3.11 .venv
call uv pip install --python ".venv\Scripts\python.exe" torch torchvision --index-url https://download.pytorch.org/whl/cu121 || (popd & echo ERROR: PyTorch installation failed.& pause & exit /b 1)
call uv pip install --python ".venv\Scripts\python.exe" -r requirements.txt || (popd & echo ERROR: 3D dependencies failed to install.& pause & exit /b 1)
call uv pip install --python ".venv\Scripts\python.exe" huggingface_hub || (popd & echo ERROR: Hugging Face tools failed to install.& pause & exit /b 1)
echo.
echo The model requires accepting its license once on Hugging Face.
echo Visit the stabilityai/stable-fast-3d model page, accept access,
echo then paste a READ token into the login prompt below.
".venv\Scripts\hf.exe" auth login
popd
echo.
echo Setup complete. The first reconstruction downloads the model weights.
echo Later reconstructions can run offline from the local cache.
pause
