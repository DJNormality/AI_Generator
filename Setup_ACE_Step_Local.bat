@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
title AI Generator - Install ACE-Step Local
echo ============================================================
echo       AI Generator - ACE-Step 1.5 Offline Music Setup
echo ============================================================
echo.
echo ACE-Step is installed separately under tools\ACE-Step-1.5.
echo It will not change AI Generator's Python 3.13 packages.
echo Internet is required for this first installation and model download.
echo.
if not exist "tools" mkdir "tools"
if not exist "tools\ACE-Step-1.5\pyproject.toml" (
  if exist "tools\ACE-Step-1.5" (
    set "ACE_BACKUP=tools\ACE-Step-1.5_incomplete_!RANDOM!"
    echo Preserving the incomplete folder as !ACE_BACKUP!...
    move "tools\ACE-Step-1.5" "!ACE_BACKUP!" >nul || (echo ERROR: Could not preserve the incomplete folder.& pause & exit /b 1)
  )
  echo Downloading the official ACE-Step source package...
  set "ACE_ZIP=%TEMP%\AI_Generator_ACE_Step_1_5.zip"
  set "ACE_TEMP=%CD%\tools\_ACE-Step-1.5-extract"
  if exist "!ACE_ZIP!" del /q "!ACE_ZIP!"
  if exist "!ACE_TEMP!" rmdir /s /q "!ACE_TEMP!"
  powershell -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -UseBasicParsing 'https://github.com/ace-step/ACE-Step-1.5/archive/refs/heads/main.zip' -OutFile $env:ACE_ZIP; Expand-Archive -LiteralPath $env:ACE_ZIP -DestinationPath $env:ACE_TEMP -Force" || (echo ERROR: ACE-Step download failed.& pause & exit /b 1)
  if not exist "!ACE_TEMP!\ACE-Step-1.5-main\pyproject.toml" (echo ERROR: Downloaded package is incomplete.& pause & exit /b 1)
  move "!ACE_TEMP!\ACE-Step-1.5-main" "tools\ACE-Step-1.5" >nul || (echo ERROR: Could not create tools\ACE-Step-1.5.& pause & exit /b 1)
  del /q "!ACE_ZIP!" >nul 2>nul
  rmdir /s /q "!ACE_TEMP!" >nul 2>nul
)
set "UV_EXE="
for /f "delims=" %%I in ('where uv 2^>nul') do if not defined UV_EXE set "UV_EXE=%%I"
if not defined UV_EXE if exist "%USERPROFILE%\.local\bin\uv.exe" set "UV_EXE=%USERPROFILE%\.local\bin\uv.exe"
if not defined UV_EXE if exist "%USERPROFILE%\.cargo\bin\uv.exe" set "UV_EXE=%USERPROFILE%\.cargo\bin\uv.exe"
if not defined UV_EXE (
  echo Installing uv for the separate ACE-Step environment...
  powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex" || (echo ERROR: uv installation failed.& pause & exit /b 1)
  if exist "%USERPROFILE%\.local\bin\uv.exe" set "UV_EXE=%USERPROFILE%\.local\bin\uv.exe"
  if not defined UV_EXE if exist "%USERPROFILE%\.cargo\bin\uv.exe" set "UV_EXE=%USERPROFILE%\.cargo\bin\uv.exe"
)
if not defined UV_EXE (echo ERROR: uv was installed but could not be located. Close this window and run setup again.& pause & exit /b 1)
pushd "tools\ACE-Step-1.5"
call "!UV_EXE!" sync || (popd & echo ERROR: ACE-Step dependencies failed to install.& pause & exit /b 1)
popd
echo.
echo ACE-Step is installed. Start_ACE_Step_Local.bat will download
echo the selected model on its first launch; later launches can be offline.
pause
