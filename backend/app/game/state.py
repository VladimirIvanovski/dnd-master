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
)
from app.schemas.state import (
    CharacterState,
    CombatantState,
    CombatState,
    GameState,
    InventoryEntry,
    LocationState,
    NPCState,
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
                )
                nearby = [
                    NPCState(
                        id=n.id,
                        name=n.name,
                        title=n.title,
                        personality=n.personality,
                        is_alive=n.is_alive,
                    )
                    for n in self.npcs.nearby(loc.id)
                ]

        inv_rows = self.inventory.list_for_character(character_id)
        inventory = [
            InventoryEntry(
                item_id=row.item_id,
                name=row.item.name,
                quantity=row.quantity,
                equipped=row.equipped,
                item_type=row.item.item_type,
            )
            for row in inv_rows
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
            combat_state = CombatState(
                id=active.id,
                status=active.status,
                round_number=active.round_number,
                combatants=[
                    CombatantState(
                        id=c.id,
                        name=c.name,
                        combatant_type=c.combatant_type,
                        hp=c.hp,
                        max_hp=c.max_hp,
                        ac=c.ac,
                        initiative=c.initiative,
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
            ),
            current_location=location,
            nearby_npcs=nearby,
            inventory=inventory,
            active_quests=quests,
            world_state=campaign.world_state or {},
            current_time=campaign.current_time,
            weather=campaign.weather,
            combat=combat_state,
        )
