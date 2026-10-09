@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
title AI Generator - Complete Music Setup

set "PYTHON_EXE=%CD%\Scripts\python.exe"
set "FFMPEG_ROOT=%CD%\tools\ffmpeg"
set "FFMPEG_BIN=%FFMPEG_ROOT%\bin"
set "FFMPEG_ZIP=%TEMP%\AI_Generator_ffmpeg-release-essentials.zip"
set "FFMPEG_URL=https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"

echo ============================================================
echo  AI Generator - Complete Music and Video Support Installer
echo ============================================================
echo.

if not exist "%PYTHON_EXE%" (
    echo ERROR: Scripts\python.exe was not found.
    echo Place this installer in the main AI_Generator folder.
    goto :failed
)

echo [1/5] Updating installer tools...
"%PYTHON_EXE%" -m pip install --upgrade "pip<26" "setuptools<82" wheel
if errorlevel 1 goto :failed

echo.
echo [2/5] Installing required audio plugins...
"%PYTHON_EXE%" -m pip install --upgrade "pydub>=0.25.1" "audioop-lts" "imageio-ffmpeg" pygame sounddevice send2trash
if errorlevel 1 goto :failed

echo.
echo [3/5] Checking local FFmpeg...
if exist "%FFMPEG_BIN%\ffmpeg.exe" if exist "%FFMPEG_BIN%\ffprobe.exe" goto :ffmpeg_ready
where ffmpeg >nul 2>nul
if not errorlevel 1 goto :system_ffmpeg

echo FFmpeg was not found. Downloading the Windows essentials build...
if not exist "%FFMPEG_ROOT%" mkdir "%FFMPEG_ROOT%"
if not exist "%FFMPEG_BIN%" mkdir "%FFMPEG_BIN%"

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -UseBasicParsing -Uri '%FFMPEG_URL%' -OutFile '%FFMPEG_ZIP%'"
if errorlevel 1 (
    echo PowerShell download failed. Trying Windows curl...
    curl.exe -L --fail --retry 3 -o "%FFMPEG_ZIP%" "%FFMPEG_URL%"
    if errorlevel 1 goto :ffmpeg_failed
)

echo Extracting FFmpeg into AI Generator...
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -Command ^
  "Expand-Archive -LiteralPath '%FFMPEG_ZIP%' -DestinationPath '%FFMPEG_ROOT%' -Force"
if errorlevel 1 goto :ffmpeg_failed

for /r "%FFMPEG_ROOT%" %%F in (ffmpeg.exe) do copy /y "%%F" "%FFMPEG_BIN%\ffmpeg.exe" >nul
for /r "%FFMPEG_ROOT%" %%F in (ffprobe.exe) do copy /y "%%F" "%FFMPEG_BIN%\ffprobe.exe" >nul
for /r "%FFMPEG_ROOT%" %%F in (ffplay.exe) do copy /y "%%F" "%FFMPEG_BIN%\ffplay.exe" >nul

if not exist "%FFMPEG_BIN%\ffmpeg.exe" goto :ffmpeg_failed
if not exist "%FFMPEG_BIN%\ffprobe.exe" goto :ffmpeg_failed
set "PATH=%FFMPEG_BIN%;%PATH%"
goto :ffmpeg_ready

:system_ffmpeg
echo A system FFmpeg installation was found.
goto :ffmpeg_ready

:ffmpeg_failed
echo ERROR: FFmpeg could not be downloaded or extracted.
echo Download ffmpeg-release-essentials.zip manually from:
echo %FFMPEG_URL%
echo Then place ffmpeg.exe and ffprobe.exe in:
echo %FFMPEG_BIN%
goto :failed

:ffmpeg_ready
echo FFmpeg is ready.
"%FFMPEG_BIN%\ffmpeg.exe" -version >nul 2>nul
if errorlevel 1 ffmpeg -version >nul 2>nul
if errorlevel 1 goto :ffmpeg_failed

echo.
echo [4/5] Installing the Demucs vocal-separation plugin...
"%PYTHON_EXE%" -c "import demucs" >nul 2>nul
if not errorlevel 1 (
    echo Demucs is already installed.
) else (
    "%PYTHON_EXE%" -m pip install demucs
    if errorlevel 1 (
        echo WARNING: Demucs could not be installed. Core audio tools will still work.
        echo You can retry later with: Scripts\python.exe -m pip install demucs
    ) else (
        echo Demucs installed successfully.
    )
)

echo.
echo [5/5] Verifying all required components...
set "PATH=%FFMPEG_BIN%;%PATH%"
"%PYTHON_EXE%" -c "import sys, shutil, audioop, pygame, sounddevice, send2trash; from pydub import AudioSegment; assert shutil.which('ffmpeg'); assert shutil.which('ffprobe'); print('Music, playback, recording, and Recycle Bin support are ready.'); print('Python:', sys.executable); print('FFmpeg:', shutil.which('ffmpeg')); print('FFprobe:', shutil.which('ffprobe'))"
if errorlevel 1 goto :failed

for /f %%V in ('"%PYTHON_EXE%" -c "import sys; print(sys.version_info.minor)"') do set "PY_MINOR=%%V"
if !PY_MINOR! GTR 11 (
    echo.
    echo NOTE: Basic Pitch AI is not installed because it supports Python 3.7-3.11.
    echo AI Generator's built-in MIDI detection remains available on Python 3.13.
) else (
    "%PYTHON_EXE%" -c "import basic_pitch" >nul 2>nul
    if errorlevel 1 "%PYTHON_EXE%" -m pip install basic-pitch
)

echo.
echo ============================================================
echo  Installation completed successfully.
echo  Close and restart AI Generator before using Music or Videos.
echo ============================================================
pause
exit /b 0

:failed
echo.
echo Installation did not complete. Copy the full error above for support.
pause
exit /b 1
