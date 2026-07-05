#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR/blockchain"

if ! command -v npx >/dev/null 2>&1; then
  echo "npx is required but was not found in PATH." >&2
  exit 1
fi

npx hardhat node > /tmp/divel-hardhat-node.log 2>&1 &
HARDHAT_PID=$!
sleep 5
npx hardhat run scripts/deploy.js --network localhost
cd "$ROOT_DIR/backend"
uvicorn app:app --reload

trap 'kill $HARDHAT_PID' EXIT
