@echo off
setlocal EnableDelayedExpansion

echo Moon Monitor - Setup and Launch Script
echo =====================================
echo.

REM Check for Python installation
python --version > nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher from https://www.python.org/
    pause
    exit /b 1
)

REM Check for Node.js installation
node --version > nul 2>&1
if errorlevel 1 (
    echo Error: Node.js is not installed or not in PATH
    echo Please install Node.js from https://nodejs.org/
    pause
    exit /b 1
)

REM Create necessary directories
if not exist "backend\secure" (
    echo Creating secure directory...
    mkdir "backend\secure"
)

REM Create Python virtual environment if it doesn't exist
if not exist "venv" (
    echo Creating Python virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo Error: Failed to create virtual environment
        pause
        exit /b 1
    )
)

REM Activate virtual environment and install requirements
echo Installing Python dependencies...
call venv\Scripts\activate
if errorlevel 1 (
    echo Error: Failed to activate virtual environment
    pause
    exit /b 1
)

pip install -r backend/requirements.txt
if errorlevel 1 (
    echo Error: Failed to install Python dependencies
    pause
    exit /b 1
)

REM Install frontend dependencies if node_modules doesn't exist
if not exist "frontend\node_modules" (
    echo Installing frontend dependencies...
    cd frontend
    call npm install
    if errorlevel 1 (
        echo Error: Failed to install frontend dependencies
        cd ..
        pause
        exit /b 1
    )
    cd ..
)

echo.
echo Setup completed successfully!
echo.
echo Starting services...
echo.

REM Create a default settings file if it doesn't exist
if not exist "backend\secure\settings.json" (
    echo Creating default settings file...
    echo {"slippage": 5, "priority_fee": 0.005} > backend\secure\settings.json
)

REM Create a default wallets file if it doesn't exist
if not exist "backend\secure\wallets.json" (
    echo Creating default wallets file...
    echo {"wallets": []} > backend\secure\wallets.json
)

REM Start backend server
echo Starting backend server...
start "Moon Monitor Backend" cmd /k "color 0B && echo Backend Server && echo ============== && echo. && call venv\Scripts\activate && cd backend && uvicorn main:app --reload"

REM Start frontend server
echo Starting frontend server...
start "Moon Monitor Frontend" cmd /k "color 0A && echo Frontend Server && echo ============== && echo. && cd frontend && npm run dev"

echo.
echo Moon Monitor is starting...
echo.
echo Access the application at:
echo Frontend: http://localhost:5173
echo Backend:  http://localhost:8000
echo.
echo Close this window to stop all services.
echo.

REM Keep the main window open - closing it will terminate child processes
pause 