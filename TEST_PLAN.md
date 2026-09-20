# Test Plan

## Always run

```bash
cd backend && pytest -q
cd frontend && npm run build
```

## Layers

| Layer | What |
|-------|------|
| Unit | Dice, clock, carry rules, gating, mechanical fallbacks |
| Engine | HP, XP, inventory, equip, consume, quests, combat, time, NPCs, stock, knowledge, containers |
| Invariants | Negative currency/qty, double quest reward, dead NPC nearby, time rewind |
| API / auth | JWT, cross-user isolation |
| Integration | Action pipeline with mock LLM |
| Simulation | Headless player loop (`scripts/simulate_player.py`) |
| Frontend | Production build (typecheck via `tsc -b`) plus `npm test` (vitest) |

## Invariant scenarios (must stay green)

- Damage/heal clamp; temp HP absorbs first
- XP up only; level from thresholds
- Unique item no duplicate; consume without possession fails
- Equip without possession fails; one weapon slot
- Over-encumbered add_item rejected
- Complete quest twice: second rejected, XP not doubled
- Spend more gold than owned rejected
- Dead NPC not in nearby; cannot teleport
- Time cannot go Day 3 → Day 1
- Combat already active: second start rejected
- Merchant buy without stock / absent NPC rejected
- NPC secrets never appear in DM context until learn_fact
- Relationship trust/fear/respect appear on nearby NPCs
- Time steps raise hunger/thirst; food lowers hunger
- One move and one strike per player combat turn
- Opening enemies act, then whose_turn is the player; off-turn move/attack is rejected
- Locked container loot rejected; unlock then loot grants items
- Melee vs range_ft>5 rejected without a ranged weapon
- Death: three fails while at 0 HP → dead; heal rejected
- Hidden traps/rumors never appear in DM context until spotted/heard
- NPC knowledge packet bodies stay off the prompt until share_knowledge
- Distant enemies close before they melee; range comes from the 8×8 grid
- Undiscovered locations stay off the map until travel
- Entering a trapped room deals trap damage once
- Enemy with higher initiative damages the player on combat start

## Simulation

Mock LLM + real engine (`simulate_session` plus a longer `play_session` through GameplayService). Mixed actions including impossible ones. Fail if invariants break, invented legendary loot appears, or dice-in-prose leaks into narration.

## Live (optional, in the default suite)

Marked `@pytest.mark.live`. Skip if `GROQ_API_KEY` is missing or Groq/Cerebras return 429/402. SD-Turbo generates one 64×64 PNG when `storage/models/sd-turbo` has weights; otherwise skip. Default pytest still uses mock LLM and mock images for everything else.
