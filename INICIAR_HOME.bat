@echo off
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Instale o Python pelo python.org
  pause
  exit /b 1
)
py -m pip show PySide6 >nul 2>nul
if errorlevel 1 py -m pip install -r requirements.txt
py home.py
if errorlevel 1 pause
