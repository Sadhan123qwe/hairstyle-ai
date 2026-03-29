@echo off
title HairStyle AI - Server
echo ============================================
echo    HairStyle AI - Starting Application
echo    Author: S.Thiruselvam | Roll: 23COS263
echo ============================================
echo.

REM Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    echo [INFO] Activating virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo [INFO] No virtual environment found. Using system Python.
)

REM Check if MongoDB is running (optional check)
echo [INFO] Make sure MongoDB is running on localhost:27017
echo.

REM Start the Flask app
echo [INFO] Starting Flask application on http://localhost:5000
echo [INFO] Press CTRL+C to stop the server.
echo.

REM Fix for MediaPipe + newer protobuf compatibility
set PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python

python app.py

pause
