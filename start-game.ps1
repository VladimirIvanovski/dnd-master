# Start the full game server on this PC (for local play or Tailscale Funnel).
# Usage (from repo root):
#   .\start-game.ps1
#   $env:PORT=8000; .\start-game.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

if (-not $env:PORT -or $env:PORT.Trim() -eq "") {
  $env:PORT = "8000"
}
$HostBind = if ($env:HOST -and $env:HOST.Trim() -ne "") { $env:HOST } else { "0.0.0.0" }

Write-Host "==> Ensuring Postgres (docker compose)..."
docker compose up -d

Write-Host "==> Building frontend (same-origin API/WS — no secrets in the client)..."
Push-Location frontend
if (-not (Test-Path "node_modules")) {
  npm install
}
# Empty VITE_* => relative /api and same-host WebSocket (works behind Funnel HTTPS/WSS)
$env:VITE_API_BASE_URL = ""
$env:VITE_WS_BASE_URL = ""
npm run build
Pop-Location

Write-Host "==> Starting API + UI on http://${HostBind}:$($env:PORT) ..."
Push-Location backend
if (-not (Test-Path ".venv\Scripts\python.exe")) {
  throw "Missing backend\.venv — create it and pip install -r requirements.txt first."
}
& .\.venv\Scripts\python.exe -m uvicorn app.main:app --host $HostBind --port $env:PORT
Pop-Location
