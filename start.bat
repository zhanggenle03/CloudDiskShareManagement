@echo off
cd /d "%~dp0"

:: Check Python
python --version >nul 2>&1 || python3 --version >nul 2>&1 || (
    echo Python not found. Please install Python 3.8+
    pause
    exit
)

:: Install dependencies (含 pystray 和 Pillow 支持系统托盘)
pip install flask flask-cors pystray Pillow -q

:: Stop old service
if exist "app.pid" (
    for /f %%i in ('type "app.pid"') do taskkill /F /PID %%i 2>nul
    del /f "app.pid"
)

:: Start service（托盘图标由 app.py 自动启动）
echo Starting backend service (tray icon will appear in system tray)...
start /b pythonw backend\app.py

echo Done! The app icon is in your system tray.
echo Right-click the tray icon to open browser or exit.
timeout /t 2 >nul
exit /b 0
