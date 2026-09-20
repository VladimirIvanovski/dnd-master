# Asset catalog

Prefer reusable, license-cleared art. Do not drop commercial game rips into `storage/`.

| Category | Source | License | Notes |
|----------|--------|---------|-------|
| Generated location/NPC/item | Local SD-Turbo (`IMAGE_MODEL=sd-turbo`) | Model license (Stability SD-Turbo) + your output policy | Hashed jobs in `stored_assets` |
| Placeholders | `IMAGE_MODEL=mock` | Internal | Tests / offline |
| Generic item keys | `visual/types.py` GENERIC_ITEMS | Internal prompts | torch, sword, potion, etc. |

Machine-readable copy: `backend/app/visual/catalog.py`.

When adding a downloaded still, record: author, license, URL, local path, tags.

No third-party commercial packs are bundled in this repo.
