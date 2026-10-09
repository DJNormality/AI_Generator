@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
title AI Generator - ACE-Step Local Server
if not exist "tools\ACE-Step-1.5" (
  echo ACE-Step is not installed. Run Setup_ACE_Step_Local.bat first.
  pause
  exit /b 1
)
set "ACESTEP_CONFIG_PATH=acestep-v15-turbo"
set "ACESTEP_LM_MODEL_PATH=acestep-5Hz-lm-0.6B"
set "ACESTEP_LM_BACKEND=pt"
set "ACESTEP_OFFLOAD_TO_CPU=true"
set "ACESTEP_LM_OFFLOAD_TO_CPU=true"
set "ACESTEP_INIT_LLM=false"
set "ACESTEP_API_HOST=127.0.0.1"
set "ACESTEP_API_PORT=8001"
set "UV_EXE="
for /f "delims=" %%I in ('where uv 2^>nul') do if not defined UV_EXE set "UV_EXE=%%I"
if not defined UV_EXE if exist "%USERPROFILE%\.local\bin\uv.exe" set "UV_EXE=%USERPROFILE%\.local\bin\uv.exe"
if not defined UV_EXE if exist "%USERPROFILE%\.cargo\bin\uv.exe" set "UV_EXE=%USERPROFILE%\.cargo\bin\uv.exe"
if not defined UV_EXE (
  echo uv could not be found. Run Setup_ACE_Step_Local.bat again.
  pause
  exit /b 1
)
pushd "tools\ACE-Step-1.5"
call "!UV_EXE!" run acestep-api
popd
