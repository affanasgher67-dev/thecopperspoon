@echo off
echo ========================================================
echo         RESTAURANT AGENT - SERVER STARTUP
echo ========================================================
echo.

echo.
echo Starting the web server...
echo.

.venv\Scripts\python.exe web.py --host=0.0.0.0 --port=8080 --debug

echo.
pause
