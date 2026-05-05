@echo off
REM CyberBot Frontend Startup Script (Windows)
REM This script sets up and starts the Angular frontend

echo ========================================
echo CyberBot Frontend - Windows Startup
echo ========================================
echo.

REM Check Node installation
node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js is not installed or not in PATH
    echo Please install Node.js 18+ from https://nodejs.org
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('node --version') do set NODE_VERSION=%%i
echo [✓] Node.js found: %NODE_VERSION%
echo.

REM Check npm installation
npm --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: npm is not installed
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('npm --version') do set NPM_VERSION=%%i
echo [✓] npm found: %NPM_VERSION%
echo.

REM Navigate to Frontend directory
cd /d "%~dp0\Frontend"
echo [✓] Working directory: %cd%
echo.

REM Check if node_modules exists
if not exist "node_modules" (
    echo [→] Installing dependencies (this may take a few minutes)...
    call npm install
    if errorlevel 1 (
        echo ERROR: npm install failed
        pause
        exit /b 1
    )
    echo [✓] Dependencies installed
    echo.
) else (
    echo [✓] Dependencies already installed
    echo.
)

REM Start the development server
echo ========================================
echo [✓] STARTING ANGULAR DEVELOPMENT SERVER
echo ========================================
echo.
echo Frontend will run on: http://127.0.0.1:4200
echo.
echo Login URLs:
echo   - User:  http://127.0.0.1:4200/user-login
echo   - Admin: http://127.0.0.1:4200/admin-login
echo   - Chat:  http://127.0.0.1:4200/chat
echo.
echo Press CTRL+C to stop the server
echo.

call npm start

pause
