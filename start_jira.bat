@echo off
REM Set proper encoding for Windows
set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1

REM Launch the Jira application
cd /d "%~dp0"
python JiraTicketGUI_enhanced.py

pause