# Engine Rules

The LLM never mutates rows directly. `GameEngine.apply_state_changes` validates every proposal.

## Authority

| Domain | Owner |
|--------|--------|
| Dice totals, success vs DC | Engine |
| HP, max HP, temp HP | Engine |
| XP, level | Engine |
| Gold / silver / copper | Engine |
| Inventory quantity, uniqueness, weight | Engine |
| Equipment slots, AC from gear | Engine |
| Quest status and rewards | Engine |
| Combat session | Engine |
| NPC alive/location | Engine |
| Time / weather | Engine |
| NPC alive/location/schedule | Engine |
| Merchant stock | Engine |
| Player known facts vs NPC secrets | Engine (context filter) |
| Lighting / containers | Engine |
| Faction reputation | Engine |
| Narration / dialogue | LLM (flavor only) |

## Invariants

- Currency and item quantities are never negative.
- HP is `0 <= hp <= max_hp`. Temp HP is `>= 0` and absorbs damage first.
- XP never decreases. Level is at least 1 and matches XP thresholds.
- Unique items do not stack. You cannot own a second copy.
- You cannot equip, consume, or remove an item you do not possess.
- One item per equipment slot (weapon, armor, shield, accessory).
- Carry weight cannot exceed `strength * 15` (minimum 30).
- Completing a quest twice does not grant rewards twice.
- Dead NPCs are not nearby and cannot be moved as if alive.
- NPC `secrets` are never loaded into GameState or the DM prompt. Knowledge packets expose topic ids only until `share_knowledge`.
- Merchant `buy_item` with `npc_id` requires stock, presence, and gold.
- Locked containers cannot be looted until `unlock_container`.
- Hidden traps are not in GameState/DM context. `disarm_trap` requires `spot_trap`. Entering a room springs the first armed trap.
- Unheard rumors are stripped from the state snapshot. The engine seeds rumor ids; `hear_rumor` copies the text into known facts.
- Combat uses an 8×8 grid (5 ft/cell). Melee foes close in; ranged foes shoot from afar; wounded foes may fall back into cover. Range is computed from position.
- `move_combatant` and `damage_combatant` (via state changes) only succeed on that combatant's turn. One move and one strike per turn. Opening enemy initiative beats resolve, then whose_turn is the player.
- Time steps raise hunger/thirst and lower stamina; food/drink consume lowers hunger/thirst. Exhausted applies when vitals are worn (−2 on d20, extra travel ticks). Storm/rain/heat add travel ticks; storm/fog/blizzard penalize checks.
- Undiscovered locations are omitted from `known_locations` until the player travels there.
- On an enemy's turn (combat start or `advance_turn`), melee deals 1–3, ranged 1–2, or they move instead.
- Melee `damage_combatant` fails when the target `range_ft` is over 5 and no ranged weapon is equipped.
- Named checkpoints (`save_checkpoint` / `load_checkpoint`) restore HP, coins, location, time, weather, and inventory. Rejected during combat. Payloads stay off the DM snapshot.
- Combat cannot start if a session is already active.

## Damage

1. Subtract from temp HP.
2. Remainder subtracts from HP, floored at 0.
3. HP 0 is unconscious (condition `unconscious`). Further damage while down is a failed death save. Three fails add `dead`. Heal/rest do not revive the dead.
4. `damage_type` is reduced by `extra.resistances` (0 immune … 1 none) before temp HP.

## Healing

Healing restores HP up to max HP. It does not create temp HP unless `temp_hp` is set explicitly.

## XP

Thresholds: 0, 300, 900, 2700, 6500, 14000. Crossing a threshold increases level and max HP by 5 and fills HP.

## Allowed state actions

See `GameEngine.ALLOWED_ACTIONS` (damage, heal, items, equip/consume, currency, travel, quests, NPCs, combat, time, weather, conditions, rest).

Unknown actions are rejected.
