# Roadmap

Statuses: `NOT_STARTED` | `IN_PROGRESS` | `TESTING` | `COMPLETE` | `BLOCKED`

Engine authority first. Do not mark COMPLETE until the listed slice exists in code **and** has tests. A green pytest run is not the same as a finished game.

## Phase 1 — Engine correctness

**Status:** TESTING

Done: HP/max/temp HP, unconscious, XP/level, currency, inventory uniqueness, consume/equip possession, slots, AC, encumbrance, conditions, no double quest pay, time monotonic, dead NPCs, combat start once, flee, named checkpoints (`save_checkpoint` / `load_checkpoint`), durability wear, silver/copper spend, invariants.

**Tests:** `test_engine_invariants.py`, `test_clock.py`, `test_game_core.py`

## Phase 2 — Character simulation

**Status:** TESTING

Done: stamina / hunger / thirst tick with `advance_time`; food/drink consume; rest; resistances; death saves (`dead` after 3 fails).

Done also: `exhausted` applies −2 to d20 checks and extra travel vitals; rest still clears it.

**Tests:** `test_world_systems.py`, `test_worldkit.py`

## Phase 3 — Living NPCs

**Status:** TESTING

Done: nearby living only; no dead teleport; relationship scores on GameState; schedules; merchant stock; knowledge packets.

Done also: topic and rumor buttons send `share_knowledge` / `hear_rumor` without waiting on the DM.

## Phase 4 — Living world

**Status:** TESTING

Done: `buy_item` / `sell_item` vs stock; faction rep; engine rumor tables; `hear_rumor` does not leak unheard text.

Done also: storm/rain/heat tax travel vitals; storm/fog/blizzard penalize d20 checks.

## Phase 5 — Physical world

**Status:** TESTING

Done: locks, containers, lighting, traps (spot / disarm / enter springs).

## Phase 6 — Advanced combat

**Status:** TESTING

Done: initiative, grid range, close-then-melee, ranged shots, wounded fallback, turn lock, one move + one strike.

Done also: click-to-move / strike and End turn on the player’s turn.

## Phase 7 — Story intelligence

**Status:** TESTING

Done: secrets stay off GameState/DM prompt; packets expose ids until `share_knowledge`.

## Phase 8 — AI DM quality

**Status:** IN_PROGRESS

Done: prompt rules, two-pass dice rewrite, dialogue dedupe, empty-scene talk refusal, unknown speakers stripped, no spawn-from-dialogue.

Done also: invented weapons/armor need `source=gift|loot|reward`; missing-item and empty-room talk refuse before the LLM.

Not done: live Groq/OpenAI flavor still depends on a key. Pytest now has `live` tests that skip without GROQ_API_KEY / SD-Turbo weights. No huge narration eval suite.

## Phase 9 — Visual assets

**Status:** TESTING

Done: mock/SD-Turbo pipeline, license catalog, location/NPC/item jobs, world-map job + map panel.

Gap: art quality depends on the image backend. Tests use the mock provider.

## Phase 10 — UI/UX

**Status:** TESTING

Done: three-column layout, typewriter + Space skip, `role="log"`, vitals/gear/death saves, combat grid flags, map list + optional art, toasts for loot/quests/level-up, inventory filters.

Done also: vitest coverage for HUD, combat cell intents, typewriter skip, sys-action labels. Journal save/load checkpoints.

## Simulation

**Status:** TESTING — `app/game/simulation.py`

A short legal/illegal action script, not a long playthrough.

## Stop condition

**Not reached.** Phases 2–10 are implemented enough to play and test, not fully accepted as a finished product.
