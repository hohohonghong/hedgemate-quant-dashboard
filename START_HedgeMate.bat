@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
  py -3 run.py
) else (
  python run.py
)

echo.
echo If the browser did not open, check the URL printed above.
pause
