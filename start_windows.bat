@echo off
echo ===================================================
echo   Digital Evidence Locker - Windows Startup Script
echo ===================================================

echo.
echo [1/5] Checking prerequisites...
set PYCMD=
where python >nul 2>&1 && set PYCMD=python
if not defined PYCMD (
    where py >nul 2>&1 && set PYCMD=py
)
if not defined PYCMD (
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
echo [2/5] Setting up Backend (shared venv also used by Deepfake service)...
cd backend
if not exist venv (
    echo Creating Python virtual environment...
    %PYCMD% -m venv venv
)
echo Installing backend dependencies...
venv\Scripts\pip.exe install -r requirements.txt
cd ..

echo.
echo [3/5] Setting up Deepfake Detection Service...
echo Installing Deepfake service dependencies into the same venv (this may take a while on first run)...
backend\venv\Scripts\pip.exe install -r DeepfakeDetector\backend\requirements.txt

echo.
echo [4/5] Setting up Frontend...
cd frontend
if not exist node_modules (
    echo Installing frontend dependencies - this may take a while...
    call npm install
)
cd ..

echo.
echo [5/5] Starting All Services...
echo.
start "Divel Backend (8046)" cmd /k "cd backend && call venv\Scripts\activate && uvicorn main:app --reload --port 8046"
start "Divel Deepfake Service (8001)" cmd /k "cd DeepfakeDetector\backend && call ..\..\backend\venv\Scripts\activate && uvicorn main:app --port 8001"
start "Divel Frontend (5173)" cmd /k "cd frontend && npm run dev"

echo.
echo ===================================================
echo   System Started Successfully!
echo   Backend:          http://localhost:8046
echo   API Docs:         http://localhost:8046/docs
echo   Deepfake Service: http://localhost:8001
echo   Frontend:         http://localhost:5173
echo.
echo   Demo Logins:
echo     Police:    polaris    / polaris123
echo     Forensics: forensics  / forensics123
echo     Judge:     judge      / judge123
echo.
echo   Note: the Deepfake service downloads its model from
echo   Hugging Face on first request, so an internet
echo   connection is needed at least once.
echo ===================================================
echo.
pause
