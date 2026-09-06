@echo off
chcp 65001 >nul
title VoicehackTool
cd /d "%~dp0"

echo Проверка зависимостей VoicehackTool...
python -c "import sounddevice, numpy, scipy, pyfiglet, pystyle" 2>nul
if %errorlevel% neq 0 (
    echo Установка необходимых библиотек...
    pip install -r requirements.txt
)

echo Запуск VoicehackTool...
python main.py

pause