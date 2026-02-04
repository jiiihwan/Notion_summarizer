@echo off
chcp 65001 > NUL
REM cd /d "%~dp0"
REM echo Notion AI Summarizer Starting...
".\venv\Scripts\python.exe" main.py
pause
