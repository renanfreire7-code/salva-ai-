@echo off
title Bar Simples
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
    echo Nao foi possivel iniciar o Bar Simples. Leia a mensagem acima.
    pause
)
endlocal
