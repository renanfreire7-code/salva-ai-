@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel% equ 0 (
    py -3 diagnose_access.py
) else (
    python diagnose_access.py
)
echo.
pause
endlocal
