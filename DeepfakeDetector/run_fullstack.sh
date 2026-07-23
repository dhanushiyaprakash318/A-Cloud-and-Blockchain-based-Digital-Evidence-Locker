#!/bin/bash

# Kill child processes on exit
trap "kill 0" EXIT

echo "=================================================="
echo "  DEEPFAKE DETECTIVE - LINUX LAUNCHER"
echo "=================================================="
echo ""

echo "[1/4] Installing Backend Dependencies..."
pip install -r backend/requirements.txt
if [ $? -ne 0 ]; then
    echo "Error installing python libs."
    exit 1
fi

echo ""
echo "[2/4] Installing Frontend Dependencies..."
cd frontend
if [ ! -d "node_modules" ]; then
    echo "Installing Node Modules..."
    npm install
fi
cd ..

echo ""
echo "[3/4] Starting Servers..."
echo ""
echo "   - Backend: http://localhost:8000"
echo "   - Frontend: http://localhost:3000"
echo ""

# Start backend
cd backend
python main.py &
BACKEND_PID=$!
cd ..

# Start frontend
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo "System Launching..."
echo "Press Ctrl+C to stop both servers."

wait
