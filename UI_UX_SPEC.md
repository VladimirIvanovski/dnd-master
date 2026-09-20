# UI / UX Spec

## Priority

Story + action first. Sheets and docks second. Never bury "what do you do?" under chrome.

## Layout

Three columns on large screens: character/people/pack | story + act | location + art. Top bar: place, time, weather, system panels, connection.

## Story

- Typewriter + dust glyph reveal for new beats; click/Space skips.
- Paragraphs and sparse `**bold**`.
- Dice results appear in the log before narration.
- Empty story: "The scene awaits your first action."

## Actions

Exactly three grounded suggestions plus a custom line. Disabled while the DM is resolving. Keyboard: skip reveal without stealing the input field.

## Sheets

- Character: HP (and temp HP), AC, XP, coins, abilities, equipped gear, conditions.
- Inventory: empty state, filters, select-to-detail (click again collapses).
- Quests / journal: empty and error states.
- Combat: distinct combat layout, not a spreadsheet dump.

## Feedback

Toasts for loot, quests, level-up. Connection dot. Loading copy in plain language. Errors retryable.

## Accessibility

Buttons have labels. Story log is `role="log"`. Don't trap keyboard in docks.
