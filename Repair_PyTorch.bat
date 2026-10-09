@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title AI Generator - Repair PyTorch
color 0E

set "PYTHON_EXE=%CD%\Scripts\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=%CD%\.venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" (
    where python >nul 2>nul
    if errorlevel 1 (
        echo ERROR: Python was not found. Run Setup.bat first.
        goto failed
    )
    set "PYTHON_EXE=python"
)

echo ============================================================
echo              AI Generator - PyTorch Repair
echo ============================================================
echo Python: %PYTHON_EXE%
echo.
echo This repairs only Torch packages in this Python installation.
echo AI Generator projects, models, configuration, and output files
echo are not changed.
echo.

echo [1/4] Removing the mismatched Torch package records...
"%PYTHON_EXE%" -m pip uninstall -y torch torchvision torchaudio >nul 2>nul

echo [2/4] Removing leftover mixed Torch module files...
"%PYTHON_EXE%" -c "import glob,os,shutil,sysconfig; root=sysconfig.get_paths()['purelib']; names=('torch','torchvision','torchaudio','functorch','torchgen'); [shutil.rmtree(os.path.join(root,n),ignore_errors=True) for n in names]; patterns=('torch-*.dist-info','torchvision-*.dist-info','torchaudio-*.dist-info','functorch-*.dist-info'); [shutil.rmtree(p,ignore_errors=True) for pat in patterns for p in glob.glob(os.path.join(root,pat))]"
if errorlevel 1 goto failed

echo [3/4] Installing one matched CUDA 12.8 PyTorch set...
"%PYTHON_EXE%" -m pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cu128 torch torchvision torchaudio
if errorlevel 1 goto failed

echo [4/4] Applying the Torch setuptools limit and verifying CUDA...
"%PYTHON_EXE%" -m pip install --upgrade "setuptools<82"
if errorlevel 1 goto failed
"%PYTHON_EXE%" -c "import torch,torchvision,torchaudio; ok=torch.cuda.is_available(); print('Torch:',torch.__version__); print('Torchvision:',torchvision.__version__); print('Torchaudio:',torchaudio.__version__); print('CUDA build:',torch.version.cuda); print('CUDA available:',ok); print('GPU:',torch.cuda.get_device_name(0) if ok else 'not detected')"
if errorlevel 1 goto failed

echo.
echo PyTorch repair completed successfully.
if /i not "%~1"=="nopause" pause
exit /b 0

:failed
echo.
echo ERROR: PyTorch repair did not complete.
echo Confirm that Windows has internet access and enough free disk space,
echo then run this file again.
if /i not "%~1"=="nopause" pause
exit /b 1
