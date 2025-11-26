@echo off
chcp 65001 >nul
echo ====================================
echo ScanFlow Pro - Installation Script
echo ====================================
echo.

REM Check if running as administrator
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] This script requires administrator privileges.
    echo Please right-click and select "Run as Administrator"
    pause
    exit /b 1
)

echo [1/7] Checking Python installation...
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please download and install Python 3.11+ from: https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)
echo [OK] Python found

echo.
echo [2/7] Checking Node.js installation...
node --version >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] Node.js is not installed or not in PATH
    echo Please download and install Node.js from: https://nodejs.org/
    pause
    exit /b 1
)
echo [OK] Node.js found

echo.
echo [3/7] Checking MongoDB installation...
mongod --version >nul 2>&1
if %errorLevel% neq 0 (
    echo [WARNING] MongoDB is not installed or not in PATH
    echo You can download MongoDB from: https://www.mongodb.com/try/download/community
    echo.
    echo Or use MongoDB Cloud (Atlas) - update backend/.env with your connection string
    echo.
    set /p CONTINUE="Continue without MongoDB? (y/n): "
    if /i not "%CONTINUE%"=="y" exit /b 1
) else (
    echo [OK] MongoDB found
)

echo.
echo [4/7] Installing Tesseract OCR...
tesseract --version >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] Tesseract OCR is not installed
    echo.
    echo Please download and install from:
    echo https://github.com/UB-Mannheim/tesseract/wiki
    echo.
    echo Download: tesseract-ocr-w64-setup-5.3.3.20231005.exe
    echo.
    echo After installation, add Tesseract to PATH:
    echo - Default path: C:\Program Files\Tesseract-OCR
    echo - Add to System Environment Variables
    echo.
    pause
    exit /b 1
)
echo [OK] Tesseract OCR found

echo.
echo [5/7] Installing Python dependencies...
cd backend
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)
call venv\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt
if %errorLevel% neq 0 (
    echo [ERROR] Failed to install Python dependencies
    pause
    exit /b 1
)
deactivate
cd ..
echo [OK] Python dependencies installed

echo.
echo [6/7] Installing Node.js dependencies...
cd frontend
call npm install -g yarn
call yarn install
if %errorLevel% neq 0 (
    echo [ERROR] Failed to install Node.js dependencies
    pause
    exit /b 1
)
cd ..
echo [OK] Node.js dependencies installed

echo.
echo [7/7] Setting up environment files...
if not exist "backend\.env" (
    echo Creating backend/.env...
    (
        echo MONGO_URL=mongodb://localhost:27017
        echo DB_NAME=scanflow_pro
        echo HOST=0.0.0.0
        echo PORT=8001
    ) > backend\.env
    echo [OK] Created backend/.env
) else (
    echo [OK] backend/.env already exists
)

if not exist "frontend\.env" (
    echo Creating frontend/.env...
    (
        echo REACT_APP_BACKEND_URL=http://localhost:8001
    ) > frontend\.env
    echo [OK] Created frontend/.env
) else (
    echo [OK] frontend/.env already exists
)

echo.
echo ====================================
echo Installation Complete!
echo ====================================
echo.
echo Next steps:
echo 1. Make sure MongoDB is running (if using local MongoDB)
echo 2. Run start.bat to launch the application
echo.
pause
