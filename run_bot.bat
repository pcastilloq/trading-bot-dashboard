@echo off
cd /d "%~dp0"
call .venv\Scripts\activate
python src\alert_bot.py
pause
