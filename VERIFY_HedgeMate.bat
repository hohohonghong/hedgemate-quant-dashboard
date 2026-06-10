@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
  py -3 verify.py
) else (
  python verify.py
)

pause
