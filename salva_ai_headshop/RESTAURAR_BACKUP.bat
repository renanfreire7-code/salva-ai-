@echo off
cd /d "%~dp0"
py restaurar_backup.py
if errorlevel 1 pause
