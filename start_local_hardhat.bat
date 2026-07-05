@echo off
setlocal
set ROOT_DIR=%~dp0
cd /d "%ROOT_DIR%blockchain"
start "Hardhat Node" cmd /k npx hardhat node
ping 127.0.0.1 -n 6 > nul
npx hardhat run scripts/deploy.js --network localhost
cd /d "%ROOT_DIR%backend"
uvicorn app:app --reload
