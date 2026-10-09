@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title AI Generator - Configure Tripo API Key
echo ============================================================
echo             Configure Tripo API Key
echo ============================================================
echo.
echo The key will be stored in your Windows user environment as
echo TRIPO_API_KEY. It is not written into AI Generator source code.
echo Input is hidden while you type or paste it.
echo.
powershell -NoProfile -ExecutionPolicy Bypass -Command "$s=Read-Host 'Paste Tripo API key' -AsSecureString; $b=[Runtime.InteropServices.Marshal]::SecureStringToBSTR($s); try{$v=[Runtime.InteropServices.Marshal]::PtrToStringBSTR($b); if([string]::IsNullOrWhiteSpace($v)){exit 2}; [Environment]::SetEnvironmentVariable('TRIPO_API_KEY',$v,'User'); Write-Host 'Tripo API key saved for this Windows user.' -ForegroundColor Green} finally {[Runtime.InteropServices.Marshal]::ZeroFreeBSTR($b)}"
if errorlevel 1 (
    echo ERROR: The Tripo API key was not saved.
) else (
    echo.
    echo Restart AI Generator so it can read the new key.
)
pause
