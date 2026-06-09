@echo off
REM EditClone — Premiere Pro CEP Debug Mode Enabler (Windows)
REM Allows Premiere Pro to load unsigned (locally installed) CEP extensions.
REM
REM Run this once before installing the CEP panel.
REM No Administrator rights required — writes to HKCU (current user only).
REM Safe to run multiple times.

echo EditClone -- Enable CEP Debug Mode (Windows)
echo ==============================================
echo.
echo Setting PlayerDebugMode = 1 for CSXS 9-12...
echo (covers Premiere Pro CC 2019 through Premiere Pro 2025)
echo.

for %%V in (9 10 11 12) do (
    reg add "HKCU\Software\Adobe\CSXS.%%V" /v PlayerDebugMode /t REG_SZ /d 1 /f >nul 2>&1
    echo   HKCU\Software\Adobe\CSXS.%%V  PlayerDebugMode = 1
)

echo.
echo Done. Debug mode is now enabled.
echo.
echo Verify with:
echo   reg query "HKCU\Software\Adobe\CSXS.11" /v PlayerDebugMode
echo.
echo To disable debug mode later (re-enable signature enforcement):
echo   for %%V in (9 10 11 12) do reg delete "HKCU\Software\Adobe\CSXS.%%V" /v PlayerDebugMode /f
echo.
pause
