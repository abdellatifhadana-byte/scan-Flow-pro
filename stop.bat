@echo off
chcp 65001 >nul
echo ====================================
echo   ScanFlow Pro - Stopping...
echo ====================================
echo.

echo Stopping Backend (Python)...
taskkill /FI "WINDOWTITLE eq ScanFlow Backend*" /T /F >nul 2>&1

echo Stopping Frontend (Node.js)...
taskkill /FI "WINDOWTITLE eq ScanFlow Frontend*" /T /F >nul 2>&1

REM Kill any remaining Python/Node processes on specific ports
echo Cleaning up ports...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8001') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :3000') do taskkill /F /PID %%a >nul 2>&1

echo.
echo [OK] ScanFlow Pro stopped successfully
echo.
pause
