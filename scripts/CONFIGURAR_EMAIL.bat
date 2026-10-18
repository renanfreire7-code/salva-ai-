@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel% equ 0 (
    py -3 scripts\configure_email.py
) else (
    python scripts\configure_email.py
)
echo.
pause
endlocal
