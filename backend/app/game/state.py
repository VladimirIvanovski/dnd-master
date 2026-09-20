from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.database.repositories import (
    CampaignRepository,
    CharacterRepository,
    CombatRepository,
    InventoryRepository,
    LocationRepository,
    NPCRepository,
    QuestRepository,
    RelationshipRepository,
)
from app.game.rules import (
    carry_capacity,
    conditions_from_extra,
    item_weight,
    vitals_from_extra,
)
from app.game.worldkit import (
    cell_pos,
    cover_bonus,
    death_saves,
    heard_topics,
    heard_rumors,
    known_facts,
    lighting_of,
    normalize_stock,
    public_containers,
    public_topics,
    public_traps,
    range_ft,
    unheard_rumor_ids,
    checkpoint_names,
    public_world_state,
)
from app.schemas.state import (
    CharacterState,
    CombatantState,
    CombatState,
    GameState,
    InventoryEntry,
    LocationState,
    NPCState,
    PlaceView,
    QuestState,
)


class GameStateLoader:
    def __init__(self, db: Session):
        self.db = db
        self.campaigns = CampaignRepository(db)
        self.characters = CharacterRepository(db)
        self.inventory = InventoryRepository(db)
        self.locations = LocationRepository(db)
        self.npcs = NPCRepository(db)
        self.quests = QuestRepository(db)
        self.combat = CombatRepository(db)
        self.relationships = RelationshipRepository(db)

    def load(self, campaign_id: uuid.UUID, character_id: uuid.UUID) -> GameState:
        campaign = self.campaigns.get(campaign_id)
        if not campaign:
            raise ValueError("Campaign not found")
        character = self.characters.get(character_id)
        if not character or character.campaign_id != campaign_id:
            raise ValueError("Character not found in campaign")

        location = None
        nearby: list[NPCState] = []
        if character.location_id:
            loc = self.locations.get(character.location_id)
            if loc:
                location = LocationState(
                    id=loc.id,
                    name=loc.name,
                    description=loc.description,
                    location_type=loc.location_type,
                    lighting=lighting_of(loc.extra),
                    containers=public_containers(loc.extra),
                    traps=public_traps(loc.extra),
                )
                nearby = []
                for n in self.npcs.nearby(loc.id):
                    rel = self.relationships.get(character_id, n.id)
                    nearby.append(
                        NPCState(
                            id=n.id,
                            name=n.name,
                            title=n.title,
                            personality=n.personality,
                            is_alive=n.is_alive,
                            faction=n.faction or "",
                            stock=normalize_stock((n.extra or {}).get("stock")),
                            topics=public_topics(n.knowledge, n.secrets),
                            asked=heard_topics(character.extra, n.id),
                            trust=float(rel.trust) if rel else 0,
                            fear=float(rel.fear) if rel else 0,
                            respect=float(rel.respect) if rel else 0,
                        )
                    )

        inv_rows = self.inventory.list_for_character(character_id)
        inventory = [
            InventoryEntry(
                item_id=row.item_id,
                name=row.item.name,
                quantity=row.quantity,
                equipped=row.equipped,
                item_type=row.item.item_type,
                durability=getattr(row, "durability", None),
                weight=item_weight(row.item),
            )
            for row in inv_rows
        ]
        carry_used = sum(e.weight * e.quantity for e in inventory)
        vitals = vitals_from_extra(character.extra)
        saves = death_saves(character.extra)
        factions = (campaign.world_state or {}).get("factions") or {}
        world_state = public_world_state(campaign.world_state)
        world_state["rumors"] = [
            {"id": row.get("id"), "text": row.get("text"), "heard": True}
            for row in (world_state.get("rumors") or [])
            if isinstance(row, dict) and row.get("heard")
        ]

        quests = [
            QuestState(
                id=q.id,
                title=q.title,
                description=q.description,
                status=q.status,
                objectives=[o.description for o in q.objectives],
            )
            for q in self.quests.active_for_campaign(campaign_id, character_id)
        ]

        combat_state = None
        active = self.combat.active_for_campaign(campaign_id)
        if active:
            fighters = [c for c in active.combatants if c.is_active]
            fighters.sort(key=lambda c: c.initiative, reverse=True)
            idx = int((active.extra or {}).get("turn_index", 0))
            whose = fighters[idx % len(fighters)].name if fighters else ""
            extra = active.extra or {}
            combat_state = CombatState(
                id=active.id,
                status=active.status,
                round_number=active.round_number,
                whose_turn=whose,
                can_move=not bool(extra.get("turn_moved")),
                can_strike=not bool(extra.get("turn_struck")),
                combatants=[
                    CombatantState(
                        id=c.id,
                        name=c.name,
                        combatant_type=c.combatant_type,
                        hp=c.hp,
                        max_hp=c.max_hp,
                        ac=c.ac + cover_bonus(c.extra),
                        initiative=c.initiative,
                        cover=cover_bonus(c.extra),
                        range_ft=range_ft(c.extra),
                        x=cell_pos(c.extra)[0],
                        y=cell_pos(c.extra)[1],
                    )
                    for c in active.combatants
                ],
            )

        return GameState(
            campaign_id=campaign.id,
            campaign_name=campaign.name,
            character=CharacterState(
                id=character.id,
                name=character.name,
                race=character.race,
                class_name=character.class_name,
                level=character.level,
                xp=character.xp,
                hp=character.hp,
                max_hp=character.max_hp,
                temp_hp=int(getattr(character, "temp_hp", 0) or 0),
                ac=character.ac,
                gold=character.gold,
                silver=getattr(character, "silver", 0) or 0,
                copper=getattr(character, "copper", 0) or 0,
                abilities={
                    "strength": character.strength,
                    "dexterity": character.dexterity,
                    "constitution": character.constitution,
                    "intelligence": character.intelligence,
                    "wisdom": character.wisdom,
                    "charisma": character.charisma,
                },
                conditions=conditions_from_extra(character.extra),
                stamina=vitals["stamina"],
                hunger=vitals["hunger"],
                thirst=vitals["thirst"],
                carry_weight=carry_used,
                carry_capacity=carry_capacity(character.strength),
                known_facts=known_facts(character.extra),
                death_saves_success=saves["success"],
                death_saves_fail=saves["fail"],
            ),
            current_location=location,
            nearby_npcs=nearby,
            inventory=inventory,
            active_quests=quests,
            world_state=world_state,
            current_time=campaign.current_time,
            weather=campaign.weather,
            combat=combat_state,
            factions=factions if isinstance(factions, dict) else {},
            heard_rumors=heard_rumors(campaign.world_state),
            unheard_rumor_ids=unheard_rumor_ids(campaign.world_state),
            checkpoints=checkpoint_names(campaign.world_state),
            known_locations=[
                PlaceView(
                    id=place.id,
                    name=place.name,
                    location_type=place.location_type or "settlement",
                    here=character.location_id == place.id,
                )
                for place in self.locations.list_for_campaign(campaign_id)
            ],
        )
