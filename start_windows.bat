@echo off
echo ===================================================
echo   Digital Evidence Locker - Windows Startup Script
echo ===================================================

echo.
echo [1/4] Checking prerequisites...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python is not installed or not in PATH.
    pause
    exit /b
)
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Node.js is not installed or not in PATH.
    pause
    exit /b
)

echo.
echo [2/4] Setting up Backend...
cd backend
if not exist venv (
    echo Creating Python virtual environment...
    python -m venv venv
)

echo Activating virtual environment...
call venv\Scripts\activate

echo Installing backend dependencies...
pip install -r requirements.txt

echo Starting Backend Server (New Window)...
start "Divel Backend" cmd /k "call venv\Scripts\activate && uvicorn main:app --reload --port 8046"

cd ..

echo.
echo [3/4] Setting up Frontend...
cd frontend

echo Installing frontend dependencies (this may take a while)...
call npm install

echo.
echo [4/4] Starting Frontend Server...
echo The application will open in a new browser window shortly.
start "Divel Frontend" cmd /k "npm run dev"

cd ..

echo.
echo ===================================================
echo   System Started Successfully!
echo   Backend: http://localhost:8046
echo   Frontend: http://localhost:5173
echo ===================================================
echo.
pause
