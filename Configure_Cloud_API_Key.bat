@echo off
setlocal EnableExtensions
title AI Generator - Configure Cloud API Key

echo ============================================================
echo            AI GENERATOR CLOUD API KEY SETUP
echo ============================================================
echo.
echo The key will be entered with hidden input and stored in your
echo Windows user environment as OPENAI_API_KEY.
echo It will not be written to main.py or config.json.
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$secure = Read-Host 'Paste your OpenAI API key' -AsSecureString;" ^
  "$pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure);" ^
  "try {" ^
  "  $plain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer);" ^
  "  if ([string]::IsNullOrWhiteSpace($plain)) { throw 'No key was entered.' };" ^
  "  [Environment]::SetEnvironmentVariable('OPENAI_API_KEY', $plain, 'User');" ^
  "} finally {" ^
  "  if ($pointer -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer) }" ^
  "}"

if errorlevel 1 (
    echo.
    echo ERROR: The API key was not saved.
    pause
    exit /b 1
)

echo.
echo OPENAI_API_KEY was saved for this Windows user.
echo Close and reopen AI Generator before using Cloud prompt editing.
pause
exit /b 0
