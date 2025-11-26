@echo off
chcp 65001 >nul
title ScanFlow Pro
color 0A

echo ====================================
echo    ScanFlow Pro - Starting...
echo ====================================
echo.

REM Check if MongoDB is running (optional)
tasklist /FI "IMAGENAME eq mongod.exe" 2>NUL | find /I /N "mongod.exe">NUL
if %errorLevel% neq 0 (
    echo [WARNING] MongoDB is not running locally
    echo If using MongoDB Atlas, ignore this warning
    echo If using local MongoDB, please start MongoDB service first
    echo.
)

REM Start Backend
echo [1/3] Starting Backend Server...
cd backend
start "ScanFlow Backend" cmd /k "call venv\Scripts\activate.bat && python server.py"
cd ..
timeout /t 3 >nul

REM Start Frontend
echo [2/3] Starting Frontend Server...
cd frontend
start "ScanFlow Frontend" cmd /k "yarn start"
cd ..
timeout /t 5 >nul

REM Open browser
echo [3/3] Opening browser...
timeout /t 10 >nul
start http://localhost:3000

echo.
echo ====================================
echo ScanFlow Pro is now running!
echo ====================================
echo.
echo Backend:  http://localhost:8001
echo Frontend: http://localhost:3000
echo.
echo To stop the application:
echo - Close both command windows
echo   (ScanFlow Backend and ScanFlow Frontend)
echo.
echo Press any key to exit this window...
pause >nul
