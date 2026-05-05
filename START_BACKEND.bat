@echo off
REM CyberBot Backend Startup Script (Windows)
REM This script sets up and starts the FastAPI backend

echo ========================================
echo CyberBot Backend - Windows Startup
echo ========================================
echo.

REM Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.9+ from https://www.python.org
    pause
    exit /b 1
)

echo [✓] Python found
echo.

REM Navigate to Backend directory
cd /d "%~dp0\Backend"
echo [✓] Working directory: %cd%
echo.

REM Check if venv exists
if not exist "venv" (
    echo [!] Virtual environment not found. Creating...
    python -m venv venv
    echo [✓] Virtual environment created
    echo.
)

REM Activate virtual environment
echo [→] Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)
echo [✓] Virtual environment activated
echo.

REM Install/upgrade dependencies
echo [→] Checking dependencies...
pip install -r ..\requirements.txt -q
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)
echo [✓] Dependencies installed
echo.

REM Initialize database
if not exist "cybersecurity.db" (
    echo [→] Initializing database...
    python init_db.py
    if errorlevel 1 (
        echo ERROR: Database initialization failed
        pause
        exit /b 1
    )
    echo [✓] Database initialized
    echo.
)

REM Check ChromaDB
echo [→] Checking ChromaDB...
python check_db.py
echo [✓] ChromaDB check complete
echo.

REM Start the server
echo ========================================
echo [✓] STARTING FASTAPI SERVER
echo ========================================
echo.
echo Server will run on: http://127.0.0.1:8000
echo API Docs: http://127.0.0.1:8000/docs
echo.
echo Press CTRL+C to stop the server
echo.

python main.py

pause
