@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title AI Generator - Configure Hugging Face Token

echo ============================================================
echo            AI GENERATOR QWEN CLOUD TOKEN SETUP
echo ============================================================
echo.
echo Create a Hugging Face access token at:
echo https://huggingface.co/settings/tokens
echo.
echo The token is entered with hidden input and stored in your
echo Windows user environment as HF_TOKEN.
echo It is not written to main.py or config.json.
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command "$secure = Read-Host 'Paste your Hugging Face token' -AsSecureString; $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure); try { $token = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr); if ([string]::IsNullOrWhiteSpace($token)) { throw 'No token was entered.' }; [Environment]::SetEnvironmentVariable('HF_TOKEN', $token, 'User'); Write-Host ''; Write-Host 'HF_TOKEN saved successfully.' -ForegroundColor Green } finally { if ($ptr -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) } }"

if errorlevel 1 (
    echo.
    echo ERROR: The token was not saved.
    pause
    exit /b 1
)

echo.
echo Completely close and reopen AI Generator before using Qwen Cloud.
pause
