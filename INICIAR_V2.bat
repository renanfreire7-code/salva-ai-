@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel% equ 0 (
    py -3 -m salva_ai_v2
) else (
    python -m salva_ai_v2
)
if errorlevel 1 (
    echo.
    echo Nao foi possivel iniciar. Verifique se o Python 3 com Tkinter esta instalado.
    pause
)
endlocal
