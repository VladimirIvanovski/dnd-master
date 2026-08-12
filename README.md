# D&D Master

AI-assisted D&D-style RPG. The **Game Engine** is the source of truth for mechanics. The **database** persists the world. The **LLM** narrates, roleplays, and *proposes* changes — it never mutates authoritative state directly.

## Architecture

```
Browser (React + Zustand)
        │  REST + WebSocket
        ▼
FastAPI
        │
        ▼
GameplayService → MemoryService / DMService / GameEngine
        │
        ▼
PostgreSQL + pgvector
```

## Folder structure

```
project/
├── backend/app/          # FastAPI app, game, AI, services, API
├── backend/migrations/   # Alembic
├── backend/tests/
├── frontend/src/         # React UI, api/, stores/, components/
├── docker-compose.yml    # Postgres + pgvector
└── README.md
```

## Requirements

- Docker (Postgres/pgvector)
- Python 3.10+
- Node.js 20+ (or portable Node)

## Environment variables

### Backend (`backend/.env`)

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | SQLAlchemy URL (`postgresql+psycopg://...`) |
| `LLM_PROVIDER` | `mock` or `groq` |
| `GROQ_API_KEY` | Groq API key (server-side only) |
| `GROQ_MODEL` | e.g. `openai/gpt-oss-20b` |
| `GROQ_BASE_URL` | Default `https://api.groq.com/openai/v1` |
| `EMBEDDING_DIMENSIONS` | Vector size (default 1536) |
| `CORS_ORIGINS` | Comma-separated frontend origins |
| `JWT_SECRET` | Secret for signing access tokens (required in production) |
| `JWT_EXPIRE_MINUTES` | Access token lifetime (default 7 days) |
| `IMAGE_MODEL` | `mock` or `sd-turbo` |
| `IMAGE_MODEL_PATH` | Local SD-Turbo folder (`storage/models/sd-turbo`) |
| `IMAGE_DEVICE` | `cpu` (default) |
| `OPENAI_API_KEY` | Optional, for a future real provider |
| `LOG_LEVEL` | Logging level |

### Frontend (`frontend/.env`)

| Variable | Purpose |
|----------|---------|
| `VITE_API_BASE_URL` | Backend HTTP base (`http://127.0.0.1:8000`) |
| `VITE_WS_BASE_URL` | Backend WS base (`ws://127.0.0.1:8000`) |

Secrets stay server-side. The frontend never receives API keys.

## Database setup

```bash
docker compose up -d
```

## Migrations

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
alembic upgrade head
```

## Backend startup

```bash
cd backend
.\.venv\Scripts\activate   # or source .venv/bin/activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

API docs: http://127.0.0.1:8000/docs  
Health: http://127.0.0.1:8000/health

**Auth:** register/login via `/api/auth/*` to get a JWT. Send `Authorization: Bearer <token>` on REST calls and `?token=` on `/ws/gameplay`. Campaigns, characters, and world data are owned per user — User A cannot access User B’s data. Groq keys stay server-side only.

## Frontend startup

```bash
cd frontend
copy .env.example .env
npm install
npm run dev
```

UI: http://127.0.0.1:5173

## Play with friends (Tailscale Funnel)

Run the **entire game on your PC** (Postgres + API + built UI on one port), then expose that port with Tailscale Funnel. API keys stay in `backend/.env` only — the browser never receives them.

### 1. Start the game locally

From the repo root (Windows):

```powershell
.\start-game.ps1
```

Or with an explicit port:

```powershell
$env:PORT = "8000"
.\start-game.ps1
```

Linux / macOS:

```bash
chmod +x start-game.sh
PORT=8000 ./start-game.sh
```

This will:
- start Postgres via Docker
- build the frontend with empty `VITE_API_BASE_URL` / `VITE_WS_BASE_URL` (same-origin `/api` + `wss://` under Funnel)
- run FastAPI on `0.0.0.0:$PORT` and serve the UI from `frontend/dist`

Local check: http://127.0.0.1:8000/health

### 2. Start Tailscale Funnel

In another terminal (Tailscale installed and logged in):

```powershell
tailscale funnel --bg 8000
```

(Use the same port as `PORT` above.)

### 3. Get the public HTTPS URL

```powershell
tailscale funnel status
```

Copy the HTTPS URL Tailscale prints (typically `https://<your-machine>.<tailnet>.ts.net/`).

### 4. Share that URL with another player

Send them the HTTPS link. While `start-game` is running on your PC, they can open it and play. WebSockets use `wss://` on the same host automatically.

Stop Funnel when done:

```powershell
tailscale funnel reset
```

## Docker

`docker-compose.yml` runs **Postgres 16 + pgvector** only. App processes run locally for simple development.

## Testing

```bash
cd backend
pytest -q
```

```bash
cd frontend
npm run build
```

Integration checks cover memory recall, engine authority (gold/HP), dice gating, combat, persistence, JWT auth, cross-user isolation, WebSocket auth, and concurrent multi-user play.

## AI provider configuration

1. Implement `LLMProvider` (`generate`, `generate_structured`, `stream`) under `backend/app/ai/`.
2. Wire it in `app/ai/factory.py` based on `LLM_PROVIDER`.
3. Keep returning validated `DMResponse` JSON. The GameEngine still applies or rejects every `state_change`.

Built-in providers:
- `mock` — offline/deterministic (tests)
- `groq` — set `LLM_PROVIDER=groq`, `GROQ_API_KEY`, and `GROQ_MODEL` (default `openai/gpt-oss-20b`)

## Image generation (CPU)

Local **SD-Turbo** via Diffusers (1-step). Asset sizes: scene/map 512, portraits 256, items 128, icons 64.

```bash
cd backend
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
python scripts/download_sd_turbo.py --out storage/models/sd-turbo
```

Set in `.env`: `IMAGE_MODEL=sd-turbo`, `IMAGE_MODEL_PATH=storage/models/sd-turbo`, `IMAGE_DEVICE=cpu`. Use `IMAGE_MODEL=mock` for placeholders.

## Play loop

1. Create campaign  
2. Create character  
3. Enter game (or **Resume Last Session** / **Continue**)  
4. Act → WS streams narration → engine applies legal changes → UI updates from `state_snapshot`

The AI tells the story. The GameEngine controls reality. The database remembers the world.
