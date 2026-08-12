#!/usr/bin/env bash
# Start the full game server on this PC (for local play or Tailscale Funnel).
# Usage (from repo root):
#   ./start-game.sh
#   PORT=8000 ./start-game.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

export PORT="${PORT:-8000}"
HOST_BIND="${HOST:-0.0.0.0}"

echo "==> Ensuring Postgres (docker compose)..."
docker compose up -d

echo "==> Building frontend (same-origin API/WS — no secrets in the client)..."
cd frontend
if [[ ! -d node_modules ]]; then
  npm install
fi
export VITE_API_BASE_URL=
export VITE_WS_BASE_URL=
npm run build
cd ..

echo "==> Starting API + UI on http://${HOST_BIND}:${PORT} ..."
cd backend
if [[ ! -x .venv/bin/python ]]; then
  echo "Missing backend/.venv — create it and pip install -r requirements.txt first." >&2
  exit 1
fi
exec .venv/bin/python -m uvicorn app.main:app --host "$HOST_BIND" --port "$PORT"
