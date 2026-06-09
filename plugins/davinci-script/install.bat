@echo off
REM EditClone — DaVinci Resolve Script Installer (Windows)
REM Copies editclone_import.py to the DaVinci Resolve Scripts\Utility directory.

setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "SRC=%SCRIPT_DIR%editclone_import.py"
set "DEST_DIR=%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility"

echo EditClone -- DaVinci Resolve Script Installer
echo ==============================================

REM Verify source file exists
if not exist "%SRC%" (
    echo ERROR: editclone_import.py not found at: %SRC%
    pause
    exit /b 1
)

REM Create destination directory if it doesn't exist
if not exist "%DEST_DIR%" (
    echo Creating directory: %DEST_DIR%
    mkdir "%DEST_DIR%"
)

REM Copy the script
echo Installing to: %DEST_DIR%
copy /Y "%SRC%" "%DEST_DIR%\editclone_import.py"

if errorlevel 1 (
    echo ERROR: Failed to copy file. Check permissions.
    pause
    exit /b 1
)

echo.
echo Installation complete.
echo.
echo Next steps:
echo   1. Open DaVinci Resolve
echo   2. Go to Workspace ^> Scripts ^> Utility ^> editclone_import
echo   3. On first run, enter your API URL and token when prompted
echo.
echo API URL:  https://editclone-production.up.railway.app
echo Token:    Get from https://editclone.vercel.app/ja/account (API Keys section)
echo.
pause
