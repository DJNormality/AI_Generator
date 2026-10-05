@echo off
setlocal
title Configure A2E API Token

echo AI Generator - A2E API Token
echo =============================
echo.
echo Paste a NEW token from https://video.a2e.ai/account/token
echo The token will be stored in your Windows user environment.
echo Nothing will appear while you paste or type it.
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command "$secure = Read-Host 'A2E API token' -AsSecureString; $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure); try { $token = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr); if ([string]::IsNullOrWhiteSpace($token)) { throw 'No token was entered.' }; [Environment]::SetEnvironmentVariable('A2E_API_TOKEN', $token.Trim(), 'User'); Write-Host 'A2E_API_TOKEN saved successfully.' -ForegroundColor Green } finally { if ($ptr -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) } }"

if errorlevel 1 (
    echo.
    echo The token was not saved.
    pause
    exit /b 1
)

echo.
echo Completely close and reopen AI Generator before selecting A2E.
pause
endlocal
