@echo off
setlocal enabledelayedexpansion

echo ================================
echo Precision Crop Management System
echo ================================
echo.

echo Step 1: Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo Python not found. Please install Python 3.8 or higher.
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo OK Python !PYTHON_VERSION! found
echo.

echo Step 2: Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo Failed to install dependencies
    pause
    exit /b 1
)
echo OK Dependencies installed successfully
echo.

echo Step 3: Preparing templates directory...
if not exist "templates" (
    mkdir templates
    echo OK Templates directory created
) else (
    echo OK Templates directory exists
)
echo.

echo Step 4: Starting application...
echo Server will be available at: http://localhost:5000
echo.
echo Press Ctrl+C to stop the server
echo.

python app.py

pause
