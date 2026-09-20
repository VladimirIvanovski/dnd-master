# D&D Master

A persistent, text-first fantasy RPG with an **AI Dungeon Master**. You type what your character does in plain language. An LLM narrates the scene and voices the NPCs. A deterministic **Game Engine** decides what actually happens, and **PostgreSQL** remembers the world between sessions.

> The AI tells the story. The Game Engine controls reality. The database remembers the world.

It is built to run **on your own PC** and be shared with friends over a public HTTPS link through **Tailscale Funnel**. You don't need a cloud server, and API keys never leave your machine.

---

## Table of contents

1. [What it does](#what-it-does)
2. [Tech stack](#tech-stack)
3. [Architecture](#architecture)
4. [How a turn works](#how-a-turn-works-the-core-loop)
5. [The Game Engine: why the AI can't cheat](#the-game-engine-why-the-ai-cant-cheat)
6. [The AI layer: providers and failover](#the-ai-layer-providers-and-failover)
7. [Memory: how the world remembers](#memory-how-the-world-remembers)
8. [Database](#database)
9. [Image generation](#image-generation)
10. [Auth, security and rate limits](#auth-security-and-rate-limits)
11. [Frontend](#frontend)
12. [Running it locally (development)](#running-it-locally-development)
13. [Hosting for friends (Tailscale Funnel)](#hosting-for-friends-tailscale-funnel)
14. [Environment variables](#environment-variables)
15. [Testing](#testing)
16. [Project structure](#project-structure)
17. [Design docs](#design-docs)
18. [Troubleshooting](#troubleshooting)

---

## What it does

- **Create an account**, then a **campaign**. Give it a one-line pitch or leave it blank for a random one.
- The server generates a **campaign brief and "DNA"**: tone, themes, a starting location, a starter NPC, seeded rumors and an opening narration.
- **Create a character** (race, class, six ability scores).
- **Play**: type any action, or tap one of three suggested actions. The DM narrates, NPCs talk, dice are rolled when needed, and your HP, gold, inventory, quests, location, time and weather update.
- **Come back later** with *Continue / Resume Last Session*. Everything is persisted, including the scene log.
- **Visuals**: location art, NPC and character portraits, item icons and a world map. They are generated locally on your CPU with SD-Turbo, or shown as placeholders.

Systems in the engine include HP/temp HP, XP and levels, gold/silver/copper, inventory with weight and unique items, equipment slots and AC, conditions, stamina/hunger/thirst, resting, death saves, grid combat with initiative, range and cover, traps, lockable containers, merchants with stock, faction reputation, NPC schedules, rumors, NPC knowledge topics, a day/period clock, weather, and named save/load checkpoints.

---

## Tech stack

| Layer | Tech |
|---|---|
| Backend | Python 3.10+, **FastAPI**, Uvicorn, Pydantic v2 |
| Database | **PostgreSQL 16 + pgvector** (Docker), SQLAlchemy 2, **Alembic** migrations |
| LLM | **Cerebras** and/or **Groq** (OpenAI-compatible APIs), plus an offline **mock** provider |
| Images | **SD-Turbo** via HuggingFace Diffusers on CPU, plus a mock placeholder provider |
| Auth | JWT (HS256, PyJWT) + bcrypt password hashing |
| Rate limiting | slowapi |
| Frontend | **React 19**, TypeScript, **Vite 6**, **Tailwind CSS 4**, **Zustand**, React Router 7, three.js (3D dice) |
| Hosting | Single process on your PC, exposed with **Tailscale Funnel** |
| Tests | pytest (backend), Vitest (frontend) |

---

## Architecture

```
Browser (React + Zustand)
   │   REST  /api/*        (auth, campaigns, characters, state, assets)
   │   WebSocket /ws/gameplay?token=...   (player actions, streamed narration)
   ▼
FastAPI  (app/main.py) ─── also serves the built React app from frontend/dist
   │
   ▼
GameplayService  (app/services/gameplay.py)   ← the turn pipeline
   ├── GameStateLoader   loads the full authoritative state from the DB
   ├── MemoryService     short-term events + long-term vector memories
   ├── EventDirector     decides whether "something happens" this turn
   ├── DMService         builds the prompt, calls the LLM, validates JSON
   ├── GameEngine        validates + applies every proposed state change
   └── VisualOrchestrator queues image jobs for new places/NPCs/items
   │
   ▼
PostgreSQL + pgvector        storage/assets/*.png (generated images)
```

API routes stay thin. All game logic lives in services and the engine.

---

## How a turn works (the core loop)

When you send an action over the WebSocket, `GameplayService.handle_action` runs:

1. **Load state.** Character, location, nearby NPCs, inventory, quests, combat and world state are loaded from the DB.
2. **Shortcuts (no LLM):**
   - `sys:` commands from UI buttons (`sys:ask:<npc>:<topic>`, `sys:move:dx:dy`, `sys:save:<name>`, `sys:load:<name>`, …) go straight to the engine. They are instant and free.
   - **Immediate refusals.** If you try to "use my sword" without owning one, or talk when nobody is there, the server refuses without calling the LLM.
3. **Build context.** It collects recent events, retrieves relevant long-term memories, asks the EventDirector for an optional event hint, and decides whether the environment needs re-describing.
4. **Pass 1: the LLM DM** returns strict JSON (`DMResponse`): narration, dialogue, proposed `state_changes`, quest/NPC updates, memory candidates, suggested actions and optional **dice requests**.
5. **Dice.** If the DM asked for a check, the **engine** rolls with a cryptographically secure RNG (`SecureRandom`) and computes success against the DC.
6. **Pass 2 (only if dice were rolled).** The DM is called again with the real results and rewrites the narration to match success or failure. This happens in the same request, so the client never makes a second call.
7. **Gating.** Changes marked `requires_success` are dropped if the check failed. For example, you don't get the loot if you failed to pick the lock.
8. **Apply.** `GameEngine.apply_state_changes` validates each change and applies it or rejects it with a reason.
9. **Persist.** Events, memories, narrative meta and scene-log beats are saved, and everything is committed in one transaction.
10. **Images.** New locations, NPCs or items queue image jobs. Workers start *after* the commit so they can see the rows.
11. **Respond.** Narration is streamed in chunks (`narration_chunk`), then a final `result` arrives with the full **`state_snapshot`**. The UI re-renders from that snapshot, so the client never computes game state itself.

Dice prose such as "you rolled a 17" or "DC 15" is scrubbed from the narration (`app/ai/quality.py`). Numbers belong in the dice UI, not the story.

---

## The Game Engine: why the AI can't cheat

`app/game/engine.py` is the single source of truth for mechanics. The LLM can only **propose** changes from a fixed whitelist (`GameEngine.ALLOWED_ACTIONS`: `apply_damage`, `gain_gold`, `add_item`, `move_to_location`, `start_combat`, `advance_time`, `loot_container`, `save_checkpoint`, … about 60 in total). Each proposal is checked against the rules:

- Currency and item quantities are never negative, and gold gains are capped per turn.
- HP stays in `0..max_hp`. Temp HP absorbs damage first.
- XP never decreases, and level always matches the XP thresholds.
- You can't equip, consume, sell or remove an item you don't have. Unique items don't stack. There is one item per equipment slot.
- Carry weight is limited by Strength.
- Time never goes backwards. Quests can't pay out twice. Dead NPCs stay dead. Combat can't start twice.
- In combat, it must actually be your turn and targets must be in range.

Anything invalid lands in `rejected_changes`. If *nothing* valid was applied, the player sees *"That doesn't work: …"*. `assert_invariants()` is used in tests to check these guarantees after long simulated sessions.

Supporting modules:

| File | Role |
|---|---|
| `game/rules.py` | Carry capacity, slots, AC, conditions, vitals ticking, weather penalties |
| `game/worldkit.py` | Pure helpers stored in JSONB: traps, containers, merchant stock, rumors, NPC knowledge topics, grid distance, death saves, checkpoints |
| `game/clock.py` | `"Day N, Period"` clock (Dawn → Midnight, 8 periods), monotonic time checks |
| `game/dice.py` | Dice notation parser, d20, skill checks, secure RNG |
| `game/event_director.py` | Picks occasional events (ambush, stranger, weather…) by location tags and pacing, so the world has "quiet turns" too |
| `game/campaign_dna.py` | Random or pitch-derived campaign identity (tone, theme, conflict style) |
| `game/scene_context.py` | Decides when the environment should be described again, to avoid repeating the room description every turn |
| `game/simulation.py` | Headless auto-play used to stress-test engine invariants |

---

## The AI layer: providers and failover

- `ai/provider.py` defines the replaceable `LLMProvider` interface (`generate`, `generate_structured`, `stream`). Game logic never depends on a specific model.
- `ai/groq_provider.py` is an OpenAI-compatible HTTP client. It is used for **both Groq and Cerebras**, just with different base URLs and keys.
- `ai/mock_provider.py` is a deterministic offline DM used by tests and `LLM_PROVIDER=mock`.
- `ai/context_builder.py` + `ai/prompts/system.py` build the system prompt and the turn prompt. The prompt includes state, memories, DNA, the director note, dice results and **only the facts the player knows**. NPC secrets are filtered out so the DM can't leak them.
- `ai/dm_service.py` calls the LLM, validates the JSON against `DMResponse`, and falls back to a safe neutral line if the output is malformed.

### Failover chain (the free-tier trick)

`ai/fallback_provider.py` + `ai/factory.py` wrap several models in a chain. If one returns **429 / 402 / 404 / 5xx**, times out, or returns invalid JSON, the next one is tried automatically:

| `LLM_PROVIDER` | Order tried |
|---|---|
| `cerebras` | Cerebras gpt-oss-120b → Groq gpt-oss-120b → Cerebras gpt-oss-20b → Groq gpt-oss-20b → Groq Llama-3.3-70B → Groq Qwen |
| `groq` | Groq gpt-oss-120b → gpt-oss-20b → Llama-3.3-70B → Qwen → Cerebras 120b |
| `mock` | Offline, no keys needed |

Models without a configured key are skipped. This lets the game survive on free-tier rate limits by spreading load across two providers. If *everything* fails, the player sees a friendly "providers unavailable, try again in a moment" message.

---

## Memory: how the world remembers

There are two layers (`services/memory.py`):

1. **Short-term.** The last ~12 rows from the `events` table (player actions, narration, engine events) go into every prompt.
2. **Long-term.** The DM proposes `memory_candidates` with an importance from 1 to 10. Candidates with importance ≥ 4 are embedded and stored in `memories.embedding` (a **pgvector** column). Near-duplicates (cosine distance < 0.08) are skipped.

On each turn, memories are retrieved by **cosine similarity** (pgvector `cosine_distance`) to the action plus the current location. They are then **re-ranked**:

```
score = 0.40·similarity + 0.20·importance + 0.15·recency
      + 0.10·NPC-present + 0.10·same-location + 0.05·active-quest
      + keyword bonus (≤ 0.25)
```

and the top 6 go into the prompt.

> **Note:** embeddings are currently generated by `services/embedding.py` as a deterministic **hash-based pseudo-embedding**. It works offline, is free and is stable, but it isn't semantically meaningful, so in practice the recency, keyword, entity and location terms do most of the work. Swapping in a real embedding model only requires changing `EmbeddingService.embed()` (keep `EMBEDDING_DIMENSIONS` in sync with the column size).

---

## Database

**PostgreSQL 16 with the pgvector extension**, run by `docker-compose.yml` (image `pgvector/pgvector:pg16`, data kept in the `pgdata` Docker volume, port 5432, user/password `dnd`/`dnd`, database `dnd_master`).

The schema is managed by **Alembic** (`backend/migrations/versions/`):

| Migration | Adds |
|---|---|
| `0001_initial` | `vector` extension and core tables |
| `0002_user_password` | Password hashes on users |
| `0003_currency` | Silver/copper |
| `0004_visual_assets` | Image asset and job tables |
| `0005_engine_vitals` | Engine vitals (stamina/hunger/thirst etc.) |

### Tables

| Table | Holds |
|---|---|
| `users` | Accounts (bcrypt password hash) |
| `campaigns` | Owner, name, pitch, **`world_state` JSONB** (DNA, tone, clock, weather, flags, rumors, faction rep, checkpoints, narrative pacing) |
| `characters` | Stats, HP, XP, currency, current location, `extra` JSONB (conditions, vitals, death saves, known facts) |
| `locations` | Hierarchical places (`parent_id`), features, tags, coordinates, `extra` JSONB (lighting, containers, traps, locks) |
| `npcs` | Personality, goals, location, alive flag, knowledge and secrets, schedules, merchant stock |
| `items` / `character_items` | Item definitions and who owns how many (equipped, durability) |
| `quests` / `quest_objectives` | Quest state and objectives |
| `relationships` | Character ↔ NPC trust/affinity |
| `events` | Append-only log of every turn: short-term memory and the scene-log history for *Continue* |
| `memories` | Long-term memories with a `vector(1536)` embedding |
| `combat_sessions` / `combatants` | Initiative order, turn, grid position, cover, range |
| `stored_assets`, `asset_generation_jobs`, `location_visuals`, `npc_appearances`, `character_appearances`, `item_visuals` | The image pipeline |

**Design trick:** fixed, frequently queried fields are real columns. Flexible, evolving world details (traps, stock, rumors, conditions) live in **JSONB `extra` / `world_state`** columns, so new mechanics usually don't need a migration.

**Ownership:** every campaign has an `owner_id`. Every character, state, asset and WebSocket request checks that the campaign belongs to the logged-in user (`api/security.py`), so user A can never read or play user B's data.

---

## Image generation

`app/visual/` generates art **asynchronously** so gameplay is never blocked:

1. When a location, NPC, item, character or campaign is created, `VisualOrchestrator` builds a prompt (`visual/prompts.py`) and a **visual state hash** (SHA-256 of the entity's visual description).
2. An `asset_generation_jobs` row is queued, unless a job with the same entity, type and hash already exists. That dedupe means the same scene is never generated twice.
3. After the DB commit, a **background thread** picks up the job. Concurrency is capped by `IMAGE_MAX_CONCURRENT`, which defaults to 1 so the CPU isn't swamped.
4. The provider generates a PNG. The image bytes are hashed too, and identical images are reused instead of stored twice.
5. Files are saved to `backend/storage/assets/<campaign>/<hash>.png` and served through `/api/assets/{id}` (with an ownership check). The UI polls `/api/jobs/{id}` until the image is ready.

Sizes per type (`visual/types.py`): location art 704×448, world map 768×448, portraits 256², item icons 128², small icons 64². SD-Turbo runs in **1–2 steps**, which is fast enough on CPU.

Providers:
- `IMAGE_MODEL=mock` draws deterministic coloured placeholder PNGs. It needs no model and is used in tests.
- `IMAGE_MODEL=sd-turbo` (or `stabilityai/sd-turbo`) runs a local SD-Turbo from `IMAGE_MODEL_PATH`. The model is loaded once and kept in RAM. If the folder is missing, it **falls back to mock automatically**.

`backend/storage/` is git-ignored because it holds models and generated images.

---

## Auth, security and rate limits

- **Register/login** with `POST /api/auth/register` and `/api/auth/login`. Both return a JWT (HS256, 7-day default lifetime).
- REST calls send `Authorization: Bearer <token>`. The WebSocket connects to `/ws/gameplay?token=<token>`, and a bad token closes it with code `4401`.
- The token is stored in the browser's `localStorage` (`dnd-token`).
- **API keys live only in `backend/.env`.** The frontend is built with empty `VITE_*` URLs and never receives a secret.
- **CORS** allows `CORS_ORIGINS` plus any `https://*.ts.net` origin (Tailscale).
- **Rate limits** (slowapi, per IP): 120/min by default, 10/min on auth, 30/min on gameplay, 5/min on image regeneration.
- `.gitignore` excludes `.env`, `frontend/.env`, `*.key`, `*.crt` (Tailscale TLS certs), `storage/`, `node_modules/`, `.venv/` and `dist/`.

> ⚠️ Set a long random `JWT_SECRET` in `backend/.env` before exposing the game publicly. The code default is `change-me-in-production`, and anyone who knows it can forge logins. For example:
> `python -c "import secrets; print(secrets.token_urlsafe(48))"`

---

## Frontend

`frontend/src/`:

| Folder | Contents |
|---|---|
| `pages/` | `LoginPage`, `HomePage` (campaign list, Continue), `CreateCampaignPage`, `CreateCharacterPage`, `GamePage` |
| `components/game/` | Story stage, scene log, narration (typewriter reveal), dialogue, NPC panel, journal, action input |
| `components/…` | Character sheet, inventory, quests, combat grid, 3D dice (three.js + sounds), map, visuals |
| `stores/` | **Zustand**: `gameStore` (game state from `state_snapshot`) and `uiStore` (panels, toasts, docks) |
| `api/` | Typed REST clients; `client.ts` adds the bearer token |
| `lib/gameplaySocket.ts` | WebSocket client with auto-reconnect; picks `ws://` or `wss://` from the page protocol |
| `lib/*.test.ts` | Vitest unit tests (combat grid, HUD, reveal, sys actions) |

**Same-origin trick:** when `VITE_API_BASE_URL` / `VITE_WS_BASE_URL` are empty, the app calls relative `/api` and connects the WebSocket to the current host. In dev, Vite proxies `/api`, `/ws` and `/health` to `127.0.0.1:8000` (`vite.config.ts`). In production, FastAPI serves the built app, so one URL and one port covers everything. That is what makes Tailscale Funnel's single HTTPS URL work.

---

## Running it locally (development)

### Requirements

- **Docker Desktop** (for Postgres)
- **Python 3.10+**
- **Node.js 20+**
- An API key from **Cerebras** (https://cloud.cerebras.ai) and/or **Groq** (https://console.groq.com). Both have free tiers. You can also start with `LLM_PROVIDER=mock` and no keys.

### 1. Start the database

```bash
docker compose up -d
```

### 2. Backend

```bash
cd backend
python -m venv .venv
# Windows:   .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env          # Windows: copy .env.example .env
# edit .env: add CEREBRAS_API_KEY and/or GROQ_API_KEY, set JWT_SECRET

alembic upgrade head           # create/upgrade tables
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- API docs: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/health (should show `"database": true`)

### 3. Frontend (hot reload)

```bash
cd frontend
cp .env.example .env           # leave the values empty
npm install
npm run dev
```

Open **http://127.0.0.1:5173**, register, create a campaign and a character, and play.

### 4. (Optional) Real images with SD-Turbo

```bash
cd backend
pip install torch --index-url https://download.pytorch.org/whl/cpu
python scripts/download_sd_turbo.py --out storage/models/sd-turbo
```

Then set `IMAGE_MODEL=sd-turbo` and `IMAGE_MODEL_PATH=storage/models/sd-turbo` in `backend/.env` and restart. The download is a few GB. Each image takes a few seconds on CPU.

---

## Hosting for friends (Tailscale Funnel)

The whole game (DB + API + UI) runs **on your PC on one port**. Tailscale Funnel gives it a public `https://<machine>.<tailnet>.ts.net` URL with automatic TLS and `wss://` support. You don't need port forwarding, a domain or a cloud server.

### 1. One-time setup

- Do the backend setup above (venv, `pip install`, `.env`, `alembic upgrade head`).
- Install Tailscale (https://tailscale.com/download), log in, and enable **Funnel** for your tailnet in the admin console.

### 2. Start the game

From the repo root:

```powershell
.\start-game.ps1                 # Windows
```
```bash
chmod +x start-game.sh && ./start-game.sh   # macOS / Linux
```

The script:
1. runs `docker compose up -d` (Postgres),
2. builds the frontend with **empty** `VITE_API_BASE_URL` / `VITE_WS_BASE_URL` (same-origin, so no URLs or secrets are baked in),
3. starts Uvicorn on `0.0.0.0:$PORT` (default 8000), serving `/api`, `/ws` **and** the built UI from `frontend/dist`.

Check it at http://127.0.0.1:8000.

> The script doesn't run migrations. After pulling new code, run `alembic upgrade head` in `backend/` first.

### 3. Expose it

In another terminal:

```powershell
tailscale funnel --bg 8000       # same port as PORT
tailscale funnel status          # prints the public https://…ts.net URL
```

Send that URL to your friends. Each person registers their own account. The game stays up while your PC and `start-game` are running.

Stop sharing:

```powershell
tailscale funnel reset
```

---

## Environment variables

### Backend: `backend/.env` (never commit this file)

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg://dnd:dnd@localhost:5432/dnd_master` | SQLAlchemy URL |
| `LLM_PROVIDER` | `mock` | `cerebras`, `groq` or `mock` |
| `CEREBRAS_API_KEY` | – | Cerebras key |
| `CEREBRAS_MODEL` / `CEREBRAS_FALLBACK_MODEL` | `gpt-oss-120b` / `gpt-oss-20b` | Cerebras models |
| `CEREBRAS_BASE_URL` | `https://api.cerebras.ai/v1` | |
| `GROQ_API_KEY` | – | Groq key |
| `GROQ_MODEL` | `openai/gpt-oss-120b` | Primary Groq model |
| `GROQ_FALLBACK_MODEL`, `_2`, `_3` | gpt-oss-20b, llama-3.3-70b-versatile, qwen | Fallback chain |
| `GROQ_BASE_URL` | `https://api.groq.com/openai/v1` | |
| `JWT_SECRET` | `change-me-in-production` | **Change this.** Signs login tokens |
| `JWT_EXPIRE_MINUTES` | `10080` (7 days) | Token lifetime |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Allowed dev origins |
| `CORS_ORIGIN_REGEX` | `https://.*\.ts\.net` | Allows Tailscale URLs |
| `HOST` / `PORT` | `0.0.0.0` / `8000` | Bind address |
| `SERVE_FRONTEND` / `FRONTEND_DIST` | `true` / `../frontend/dist` | Serve the built SPA from FastAPI |
| `RATE_LIMIT_DEFAULT` / `_AUTH` / `_GAMEPLAY` | `120/minute` / `10/minute` / `30/minute` | Per-IP limits |
| `IMAGE_GENERATION_ENABLED` | `true` | Turn art off entirely |
| `IMAGE_MODEL` | `mock` | `mock` or `sd-turbo` |
| `IMAGE_MODEL_PATH` | `storage/models/sd-turbo` | Local model folder |
| `IMAGE_DEVICE` | `cpu` | `cpu` or `cuda` |
| `IMAGE_MAX_CONCURRENT` | `1` | Parallel image workers |
| `ASSET_STORAGE_PATH` | `storage/assets` | Where PNGs are saved |
| `EMBEDDING_DIMENSIONS` | `1536` | Must match the `memories.embedding` column |
| `LOG_LEVEL`, `DEBUG`, `APP_NAME` | | Misc |

### Frontend: `frontend/.env`

| Variable | Purpose |
|---|---|
| `VITE_API_BASE_URL` | Leave **empty** for same-origin `/api` (recommended) |
| `VITE_WS_BASE_URL` | Leave **empty** for same-host `ws://` / `wss://` |

Never put API keys in `VITE_*` variables. Everything in them is compiled into public JavaScript.

---

## Testing

> ⚠️ **The backend tests wipe the database.** `tests/conftest.py` runs `Base.metadata.drop_all()` / `create_all()` on whatever `DATABASE_URL` points to. Use a separate test database so your campaigns survive:
>
> ```bash
> docker compose exec db createdb -U dnd dnd_test
> # PowerShell: $env:DATABASE_URL="postgresql+psycopg://dnd:dnd@localhost:5432/dnd_test"
> DATABASE_URL=postgresql+psycopg://dnd:dnd@localhost:5432/dnd_test pytest -q
> ```

```bash
cd backend
pytest -q                 # forces LLM_PROVIDER=mock and IMAGE_MODEL=mock
pytest -m live            # optional: hits real Groq / SD-Turbo if configured
python -m scripts.simulate_player   # headless auto-play + invariant check
```

```bash
cd frontend
npm test                  # Vitest unit tests
npm run build             # type-check + production build
```

Coverage includes engine invariants, the clock, dice, combat, world systems, memory recall, dice gating, LLM failover, DM output quality (no dice prose, no secret leaks), JWT auth, cross-user isolation, WebSocket auth, visual job dedupe and concurrent multi-user play. See `TEST_PLAN.md`.

---

## Project structure

```
.
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app, CORS, rate limit, SPA serving, /health
│   │   ├── core/              # settings (.env), logging, rate limiter
│   │   ├── api/               # thin routes: auth, campaigns, characters, gameplay, assets, websocket
│   │   ├── services/          # gameplay pipeline, campaign creation, memory, auth, embeddings
│   │   ├── game/              # engine + rules, clock, dice, worldkit, event director, DNA, simulation
│   │   ├── ai/                # LLM providers, failover, prompts, context builder, DM service
│   │   ├── visual/            # image jobs, providers, prompts, storage
│   │   ├── database/          # SQLAlchemy models, repositories, session
│   │   └── schemas/           # Pydantic request/response/state models
│   ├── migrations/            # Alembic
│   ├── scripts/               # SD-Turbo download, smoke/e2e checks, simulated player
│   ├── tests/
│   ├── storage/               # (git-ignored) models + generated images
│   └── .env.example
├── frontend/
│   ├── src/                   # pages, components, stores, api, lib
│   ├── vite.config.ts         # dev proxy to backend
│   └── .env.example
├── docker-compose.yml         # Postgres 16 + pgvector
├── start-game.ps1 / .sh       # one-command build + serve (for Funnel)
└── *.md                       # design docs (below)
```

---

## Design docs

| Doc | About |
|---|---|
| `GAME_DESIGN.md` | Premise, pillars and live systems |
| `ENGINE_RULES.md` | What the engine owns and its invariants |
| `NARRATION_SPEC.md` | How the DM should write |
| `IMMERSION_SPEC.md` | Keeping the world believable |
| `UI_UX_SPEC.md` | UI layout and behaviour |
| `ASSETS.md` | Art sources and licensing |
| `TEST_PLAN.md` | What is tested and how |
| `ROADMAP.md` | Phase status |

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `/health` shows `database: false` | Start Docker Desktop and run `docker compose up -d` |
| `relation … does not exist` | `cd backend && alembic upgrade head` |
| "No LLM API keys configured" | Add `CEREBRAS_API_KEY` or `GROQ_API_KEY`, or use `LLM_PROVIDER=mock` |
| "Cerebras and Groq are both unavailable" | Every model in the chain is rate-limited. Wait a minute, or add the other provider's key |
| Images are only coloured placeholders | `IMAGE_MODEL=mock`, or the SD-Turbo folder is missing. Run `scripts/download_sd_turbo.py` |
| Friends get a blank page or WebSocket errors | Use `start-game` (same-origin build), keep `VITE_*` empty, and check `tailscale funnel status` |
| My campaigns disappeared after running tests | The tests ran against your main DB. See [Testing](#testing) |
| Port 5432 already in use | Another Postgres is running. Stop it or change the port in `docker-compose.yml` and `DATABASE_URL` |
