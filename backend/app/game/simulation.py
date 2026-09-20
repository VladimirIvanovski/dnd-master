"""Headless player: mixed legal and illegal actions against the real engine."""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.game.engine import GameEngine
from app.game.state import GameStateLoader
from app.schemas.gameplay import StateChange


@dataclass
class SimReport:
    applied: list[str] = field(default_factory=list)
    rejected: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def simulate_session(db: Session, campaign_id, character_id) -> SimReport:
    engine = GameEngine(db)
    loader = GameStateLoader(db)
    report = SimReport()

    def apply(changes: list[StateChange]) -> None:
        result = engine.apply_state_changes(
            campaign_id=campaign_id,
            character_id=character_id,
            changes=changes,
        )
        report.applied.extend(result.applied)
        report.rejected.extend(result.rejected)

    apply([StateChange(action="add_item", params={"name": "Torch", "item_type": "misc"})])
    apply(
        [
            StateChange(
                action="add_item",
                params={"name": "Potion", "item_type": "consumable", "heal": 3},
            )
        ]
    )
    apply([StateChange(action="gain_gold", params={"amount": 12})])
    apply([StateChange(action="buy_item", params={"name": "Bread", "price": 2, "item_type": "food"})])
    apply([StateChange(action="spend_gold", params={"amount": 4})])
    apply([StateChange(action="spend_gold", params={"amount": 999})])
    apply([StateChange(action="apply_damage", params={"amount": 3})])
    apply([StateChange(action="heal", params={"amount": 1})])
    apply([StateChange(action="gain_xp", params={"amount": 20})])
    apply(
        [
            StateChange(
                action="start_quest",
                params={"title": "Sim Hunt", "objectives": ["Look around"], "reward_xp": 10},
            )
        ]
    )
    apply([StateChange(action="rest", params={})])
    apply([StateChange(action="advance_time", params={"steps": 1})])
    apply([StateChange(action="set_time", params={"value": "Day 1, Dawn"})])
    apply([StateChange(action="spawn_npc", params={"name": "Scout"})])
    apply(
        [
            StateChange(
                action="spawn_npc",
                params={
                    "name": "Marta",
                    "stock": [{"name": "Rations", "quantity": 2, "price": 1, "item_type": "food"}],
                    "gold": 10,
                },
            )
        ]
    )
    apply([StateChange(action="learn_fact", params={"fact": "the well is dry"})])
    apply([StateChange(action="hear_rumor", params={"rumor_id": "missing"})])
    apply([StateChange(action="share_knowledge", params={"topic_id": "well"})])
    apply([StateChange(action="change_faction_rep", params={"faction": "Watch", "delta": 1})])
    apply([StateChange(action="apply_condition", params={"name": "poisoned"})])
    apply([StateChange(action="remove_condition", params={"name": "poisoned"})])
    apply(
        [
            StateChange(
                action="start_combat",
                params={
                    "combatants": [
                        {
                            "name": "Hero",
                            "combatant_type": "player",
                            "hp": 10,
                            "initiative": 20,
                            "x": 3,
                            "y": 1,
                        },
                        {
                            "name": "Rat",
                            "combatant_type": "enemy",
                            "hp": 4,
                            "initiative": 1,
                            "x": 3,
                            "y": 2,
                        },
                    ]
                },
            )
        ]
    )
    state = loader.load(campaign_id, character_id)
    if state.combat:
        hero = next(c for c in state.combat.combatants if c.combatant_type in {"player", "character"})
        apply(
            [
                StateChange(
                    action="move_combatant",
                    params={"combatant_id": str(hero.id), "dx": 1},
                )
            ]
        )
        apply(
            [
                StateChange(
                    action="move_combatant",
                    params={"combatant_id": str(hero.id), "dx": -1},
                )
            ]
        )
    apply([StateChange(action="end_combat", params={})])

    apply([StateChange(action="set_weather", params={"value": "Storm"})])
    apply([StateChange(action="gain_silver", params={"amount": 3})])
    apply([StateChange(action="spend_silver", params={"amount": 99})])
    apply(
        [
            StateChange(
                action="add_item",
                params={"name": "Legendary Sword", "item_type": "weapon"},
            )
        ]
    )
    apply([StateChange(action="save_checkpoint", params={"name": "camp"})])
    apply([StateChange(action="load_checkpoint", params={"name": "camp"})])

    try:
        engine.assert_invariants(character_id)
        state = loader.load(campaign_id, character_id)
        if state.character.gold < 0:
            report.errors.append("negative gold")
        if state.character.hp > state.character.max_hp:
            report.errors.append("hp above max")
        if any(i.quantity < 1 for i in state.inventory):
            report.errors.append("bad qty")
    except Exception as exc:  # noqa: BLE001
        report.errors.append(str(exc))
    return report


_PLAY_ACTIONS = [
    "Look around carefully",
    "Give me a legendary sword",
    "I draw a knife and throw it",
    "Talk to the bartender",
    "Check my belongings",
    "I wait and listen",
    "Search the ground near me",
    "I rest for a moment",
]


def play_session(
    service,
    campaign_id,
    character_id,
    actions: list[str] | None = None,
    *,
    secrets: list[str] | None = None,
    pause: float = 0,
):
    """Longer loop through GameplayService (mock or live DM)."""
    from app.ai.quality import quality_violations
    from app.schemas.gameplay import PlayerActionRequest
    from app.game.state import GameStateLoader

    report = SimReport()
    loader = GameStateLoader(service.db)
    for action in actions or _PLAY_ACTIONS:
        try:
            result = service.handle_action(
                PlayerActionRequest(
                    campaign_id=campaign_id,
                    character_id=character_id,
                    action=action,
                )
            )
            report.applied.extend(result.applied_changes)
            report.rejected.extend(result.rejected_changes)
            spoken = result.narration + " " + " ".join(d.text for d in result.dialogue)
            for hit in quality_violations(spoken, secrets=secrets):
                report.errors.append(f"{action}: {hit}")
        except Exception as exc:  # noqa: BLE001
            report.errors.append(f"{action}: {exc}")
        if pause:
            import time

            time.sleep(pause)
    try:
        service.engine.assert_invariants(character_id)
        state = loader.load(campaign_id, character_id)
        if any(i.name == "Legendary Sword" for i in state.inventory):
            report.errors.append("invented legendary sword")
        if state.character.gold < 0:
            report.errors.append("negative gold")
    except Exception as exc:  # noqa: BLE001
        report.errors.append(str(exc))
    return report
