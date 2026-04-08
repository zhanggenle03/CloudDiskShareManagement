@echo off
cd /d "%~dp0"

:: Check Python
python --version >nul 2>&1 || python3 --version >nul 2>&1 || (
    echo Python not found. Please install Python 3.8+
    pause
    exit
)

:: Install dependencies
pip install flask flask-cors -q

:: Stop old service
if exist "app.pid" (
    for /f %%i in ('type "app.pid"') do taskkill /F /PID %%i 2>nul
    del /f "app.pid"
)

:: Start service
echo Starting backend service...
start /b pythonw backend\app.py

:: Open launch page
echo Opening launch page...
cd frontend
start launch.html
cd ..

echo Done!
timeout /t 2 >nul
exit /b 0
