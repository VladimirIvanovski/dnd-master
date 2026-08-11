"""Initial schema with pgvector memories.

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("username", sa.String(64), nullable=False),
        sa.Column("display_name", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.create_table(
        "campaigns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("world_state", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("current_time", sa.String(64), nullable=False, server_default="Day 1, Morning"),
        sa.Column("weather", sa.String(64), nullable=False, server_default="Clear"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_campaigns_owner_id", "campaigns", ["owner_id"])

    op.create_table(
        "locations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("campaigns.id"), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("location_type", sa.String(64), nullable=False, server_default="settlement"),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("locations.id"), nullable=True),
        sa.Column("tags", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("extra", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_locations_campaign_id", "locations", ["campaign_id"])

    op.create_table(
        "characters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("campaigns.id"), nullable=False),
        sa.Column("location_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("locations.id"), nullable=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("race", sa.String(64), nullable=False, server_default="Human"),
        sa.Column("class_name", sa.String(64), nullable=False, server_default="Fighter"),
        sa.Column("level", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("xp", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("hp", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("max_hp", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("ac", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("gold", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("strength", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("dexterity", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("constitution", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("intelligence", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("wisdom", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("charisma", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("background", sa.Text(), nullable=False, server_default=""),
        sa.Column("extra", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_characters_user_id", "characters", ["user_id"])
    op.create_index("ix_characters_campaign_id", "characters", ["campaign_id"])
    op.create_index("ix_characters_location_id", "characters", ["location_id"])

    op.create_table(
        "items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("campaigns.id"), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("item_type", sa.String(64), nullable=False, server_default="misc"),
        sa.Column("value_gold", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("weight", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("properties", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_items_campaign_id", "items", ["campaign_id"])

    op.create_table(
        "character_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("character_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("characters.id"), nullable=False),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("items.id"), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("equipped", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("character_id", "item_id", name="uq_character_item"),
    )
    op.create_index("ix_character_items_character_id", "character_items", ["character_id"])
    op.create_index("ix_character_items_item_id", "character_items", ["item_id"])

    op.create_table(
        "npcs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("campaigns.id"), nullable=False),
        sa.Column("location_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("locations.id"), nullable=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("title", sa.String(128), nullable=False, server_default=""),
        sa.Column("personality", sa.Text(), nullable=False, server_default=""),
        sa.Column("goals", sa.Text(), nullable=False, server_default=""),
        sa.Column("fears", sa.Text(), nullable=False, server_default=""),
        sa.Column("motivations", sa.Text(), nullable=False, server_default=""),
        sa.Column("knowledge", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("secrets", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("faction", sa.String(128), nullable=False, server_default=""),
        sa.Column("is_alive", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("hp", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("max_hp", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("ac", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("extra", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_npcs_campaign_id", "npcs", ["campaign_id"])
    op.create_index("ix_npcs_location_id", "npcs", ["location_id"])

    op.create_table(
        "quests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("campaigns.id"), nullable=False),
        sa.Column("character_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("characters.id"), nullable=True),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("giver_npc_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("npcs.id"), nullable=True),
        sa.Column("reward_xp", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reward_gold", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("extra", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_quests_campaign_id", "quests", ["campaign_id"])
    op.create_index("ix_quests_character_id", "quests", ["character_id"])
    op.create_index("ix_quests_status", "quests", ["status"])

    op.create_table(
        "quest_objectives",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("quest_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("quests.id"), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("is_completed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_quest_objectives_quest_id", "quest_objectives", ["quest_id"])

    op.create_table(
        "events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("campaigns.id"), nullable=False),
        sa.Column("character_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("characters.id"), nullable=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("location_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("locations.id"), nullable=True),
        sa.Column("importance", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_events_campaign_id", "events", ["campaign_id"])
    op.create_index("ix_events_character_id", "events", ["character_id"])
    op.create_index("ix_events_event_type", "events", ["event_type"])
    op.create_index("ix_events_location_id", "events", ["location_id"])
    op.create_index("ix_events_created_at", "events", ["created_at"])

    op.create_table(
        "memories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("campaigns.id"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("importance", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("entity_ids", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("location_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("locations.id"), nullable=True),
        sa.Column("quest_ids", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("events.id"), nullable=True),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column("extra", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_memories_campaign_id", "memories", ["campaign_id"])
    op.create_index("ix_memories_content_hash", "memories", ["content_hash"])
    op.create_index("ix_memories_location_id", "memories", ["location_id"])
    op.create_index("ix_memories_created_at", "memories", ["created_at"])

    op.create_table(
        "relationships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("character_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("characters.id"), nullable=False),
        sa.Column("npc_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("npcs.id"), nullable=False),
        sa.Column("trust", sa.Float(), nullable=False, server_default="0"),
        sa.Column("fear", sa.Float(), nullable=False, server_default="0"),
        sa.Column("respect", sa.Float(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("character_id", "npc_id", name="uq_character_npc_rel"),
    )
    op.create_index("ix_relationships_character_id", "relationships", ["character_id"])
    op.create_index("ix_relationships_npc_id", "relationships", ["npc_id"])

    op.create_table(
        "combat_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("campaigns.id"), nullable=False),
        sa.Column("location_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("locations.id"), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("round_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("extra", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_combat_sessions_campaign_id", "combat_sessions", ["campaign_id"])
    op.create_index("ix_combat_sessions_status", "combat_sessions", ["status"])

    op.create_table(
        "combatants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("combat_sessions.id"), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("combatant_type", sa.String(32), nullable=False),
        sa.Column("ref_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("initiative", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("hp", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("max_hp", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("ac", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("extra", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.create_index("ix_combatants_session_id", "combatants", ["session_id"])


def downgrade() -> None:
    op.drop_table("combatants")
    op.drop_table("combat_sessions")
    op.drop_table("relationships")
    op.drop_table("memories")
    op.drop_table("events")
    op.drop_table("quest_objectives")
    op.drop_table("quests")
    op.drop_table("npcs")
    op.drop_table("character_items")
    op.drop_table("items")
    op.drop_table("characters")
    op.drop_table("locations")
    op.drop_table("campaigns")
    op.drop_table("users")
