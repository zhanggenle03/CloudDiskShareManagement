@echo off
cd /d "%~dp0"

::: Check Python
python --version >nul 2>&1 || python3 --version >nul 2>&1 || (
    echo Python not found. Please install Python 3.8+
    pause
    exit
)

::: Install backend dependencies
pip install flask flask-cors -q

::: Build Vue frontend if source exists
if exist "frontend-vue\package.json" (
    echo Building Vue frontend...
    cd frontend-vue
    call npm run build
    cd ..
    echo Vue frontend built to frontend-dist/
)

::: Stop old service
if exist "app.pid" (
    for /f %%i in ('type "app.pid"') do taskkill /F /PID %%i 2>nul
    del /f "app.pid"
)

::: Start service
echo Starting backend service...
start /b pythonw backend\app.py

::: Open browser
echo Opening app...
start http://127.0.0.1:5000/

echo Done!
timeout /t 2 >nul
exit /b 0
