# Game Design

Source of truth: the running FastAPI + React implementation. This document describes **what the game is**, not a wishlist.

## Premise

D&D Master is a persistent, text-first fantasy RPG. The player speaks actions in natural language. An LLM Dungeon Master narrates and *proposes* changes. The **Game Engine** is the only authority for HP, XP, inventory, currency, quests, combat, NPCs, time, and weather.

The player should experience a world that remembers them — not a chat that forgets.

## Pillars

1. **Engine authority** — fiction never overwrites mechanics.
2. **Persistence** — campaigns, characters, locations, NPCs, quests, and memories survive restart.
3. **Player agency** — suggested actions are optional; custom actions are always attempted.
4. **Fair refusals** — impossible actions fail in fiction *and* in state (no invented knife, no talking to empty air as if someone is there).
5. **Quiet world** — not every turn is a crisis.

## Core loop

Create account → campaign → character → act → engine resolves → UI updates from `state_snapshot` → repeat.

Turns may request dice. The server rolls, then the DM rewrites narration to match SUCCESS/FAILURE. Rewards marked `requires_success` are dropped on failure.

## Player-facing systems (live)

- Character: race, class, level, XP thresholds, HP/max HP, AC, six abilities, gold/silver/copper
- Inventory: named items, quantities, equipped flag, types
- Quests: start, update, complete (XP/gold rewards)
- NPCs: one starter NPC, nearby living NPCs only, relationships (trust/fear/respect)
- Combat: session, 8×8 grid, turn lock, one move + one strike, end + rewards
- Travel: move between discovered campaign locations
- Time, weather, vitals (stamina / hunger / thirst)
- Memory recall (pgvector) + event log / journal
- Location/NPC/item/world-map art (SD-Turbo or mock)
- Auth isolation between users

## Design constraints

- Numbers belong in the UI (dice formula, HP bar, XP). Narration stays fictional.
- LLM JSON must match `DMResponse`. Illegal `state_changes` are rejected, not applied.
- Prefer small legal changes over large invented ones.

## Economy

You cannot spend coins you do not have. Merchant stock is engine-owned.

## Time and weather

Campaign time and weather are fields. Time steps tick hunger, thirst, and stamina. Storm/rain/heat tax travel; storm/fog penalize checks. Narration must not rewind the clock. Named checkpoints restore HP, location, time, weather, and inventory.
