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

Simple tenancy: send `X-Username: player` (default). Campaigns/characters are scoped to that username.

## Frontend startup

```bash
cd frontend
copy .env.example .env
npm install
npm run dev
```

UI: http://127.0.0.1:5173

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

Integration checks cover memory recall, engine authority (gold/HP), dice gating, combat, persistence, and ownership.

## AI provider configuration

1. Implement `LLMProvider` (`generate`, `generate_structured`, `stream`) under `backend/app/ai/`.
2. Wire it in `app/ai/factory.py` based on `LLM_PROVIDER`.
3. Keep returning validated `DMResponse` JSON. The GameEngine still applies or rejects every `state_change`.

Built-in providers:
- `mock` — offline/deterministic (tests)
- `groq` — set `LLM_PROVIDER=groq`, `GROQ_API_KEY`, and `GROQ_MODEL` (default `openai/gpt-oss-20b`)

## Play loop

1. Create campaign  
2. Create character  
3. Enter game (or **Resume Last Session** / **Continue**)  
4. Act → WS streams narration → engine applies legal changes → UI updates from `state_snapshot`

The AI tells the story. The GameEngine controls reality. The database remembers the world.
