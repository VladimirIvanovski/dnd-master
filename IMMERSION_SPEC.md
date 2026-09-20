# Immersion Spec

The player should feel they live in a world, not that they are prompting a model.

## Realism check

After each mechanic: could this happen in a game world? Does the engine model it? If only the LLM claimed it, the claim is a bug.

Order: **state → simulation → result → narration**.

## Persistence

Leaving and returning (or restarting the server) must show the same HP, inventory, quests, NPC liveness, location, time, and journal beats.

## People

- Nearby list is living NPCs at the current location.
- Dead or absent people are not conversation partners.
- Relationships (trust / fear / respect) are stored numbers, not vibes.

## Body and gear

HP, temp HP, conditions, encumbrance, and equipped slots are engine state and should appear in the sheet — not only in prose.

## Economy

You cannot spend coins you do not have. Merchants and regional prices are later milestones; until then, do not narrate a purchase the engine did not apply.

## Time and weather

Campaign time and weather are fields. Narration should match them when they matter (night, rain) and must not rewind the clock.
