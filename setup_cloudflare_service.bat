@echo off
REM Setup Cloudflare Named Tunnel as a Persistent Windows Service
cd /d "%~dp0"

if "%~1"=="" (
    echo [ERROR] Please provide your Cloudflare Tunnel Token as an argument:
    echo Usage: setup_cloudflare_service.bat ^<TUNNEL_TOKEN^>
    echo Or run 'cloudflared.exe tunnel login' to set up via Cloudflare CLI.
    exit /b 1
)

echo [*] Installing Cloudflared Persistent Service...
cloudflared.exe service install %1
if %ERRORLEVEL% EQU 0 (
    echo [SUCCESS] Cloudflared Windows Service installed and started!
    echo It will automatically start with Windows and maintain connection.
) else (
    echo [NOTE] If administrator privileges were needed, run this script as Administrator.
)
