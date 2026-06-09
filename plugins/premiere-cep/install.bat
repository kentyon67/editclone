@echo off
REM EditClone — Premiere Pro CEP Extension Installer (Windows)
REM Copies the CEP panel to Adobe's extension directory.
REM Run as a normal user (no Administrator required for HKCU registry keys).

setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "EXTENSION_ID=com.editclone.premiere"
set "DEST_DIR=%APPDATA%\Adobe\CEP\extensions\%EXTENSION_ID%"

echo EditClone -- Premiere Pro CEP Installer
echo =========================================

REM ---- 1. Enable unsigned extension loading (debug mode) ----
echo.
echo [1/3] Enabling unsigned extension loading...

REM Set PlayerDebugMode for CSXS versions 9 through 12 (covers Premiere CC 2022-2025)
for %%V in (9 10 11 12) do (
    reg add "HKCU\Software\Adobe\CSXS.%%V" /v PlayerDebugMode /t REG_SZ /d 1 /f >nul 2>&1
    echo       Set HKCU\Software\Adobe\CSXS.%%V PlayerDebugMode = 1
)
echo       Done.

REM ---- 2. Create destination directory ----
echo.
echo [2/3] Creating extension directory...
if exist "%DEST_DIR%" (
    echo       Removing existing installation: %DEST_DIR%
    rmdir /s /q "%DEST_DIR%"
)
mkdir "%DEST_DIR%"

REM ---- 3. Copy extension files ----
echo.
echo [3/3] Copying extension files to: %DEST_DIR%
xcopy /E /I /Y "%SCRIPT_DIR%." "%DEST_DIR%\" >nul

REM Remove installer scripts from installed copy (not needed inside Premiere)
if exist "%DEST_DIR%\install.sh"         del /q "%DEST_DIR%\install.sh"
if exist "%DEST_DIR%\install.bat"        del /q "%DEST_DIR%\install.bat"
if exist "%DEST_DIR%\debug-enable.sh"   del /q "%DEST_DIR%\debug-enable.sh"
if exist "%DEST_DIR%\debug-enable.bat"  del /q "%DEST_DIR%\debug-enable.bat"

echo.
echo Installation complete.
echo.
echo Next steps:
echo   1. Quit Premiere Pro if it is running
echo   2. Re-open Premiere Pro
echo   3. Go to Window ^> Extensions ^> EditClone
echo.
echo   If the panel does not appear:
echo     - Confirm Premiere Pro version is CC 2019 (v13.0) or later
echo     - Verify registry: reg query "HKCU\Software\Adobe\CSXS.11" /v PlayerDebugMode
echo     - Check extension directory: dir "%DEST_DIR%"
echo.
echo API URL:  https://editclone-production.up.railway.app
echo Web app:  https://editclone.vercel.app
echo.
pause
