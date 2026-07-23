@echo off
title Deepfake Detective Fullstack Launcher
color 0A

echo ==================================================
echo   DEEPFAKE DETECTIVE - POLICE GRADE FORENSICS
echo ==================================================
echo.

echo [1/4] Installing Backend Dependencies...
pip install -r backend/requirements.txt
if %errorlevel% neq 0 (
    echo Error installing python libs.
    pause
    exit /b
)

echo.
echo [2/4] Initializing Frontend (First run may take time)...
cd frontend
if not exist node_modules (
    echo Installing Node Modules...
    call npm install
)
cd ..

echo.
echo [3/4] Starting Servers...
echo.
echo    - Backend: http://localhost:8000
echo    - Frontend: http://localhost:3000
echo.

start cmd /k "title BACKEND API & cd backend & python main.py"
start cmd /k "title FRONTEND UI & cd frontend & npm run dev"

echo System Launching... 
echo Please wait for both windows to initialize.
echo.
pause
