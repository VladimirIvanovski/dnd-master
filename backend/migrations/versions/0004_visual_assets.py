"""Visual asset system tables + location visual fields.

Revision ID: 0004_visual_assets
Revises: 0003_currency
Create Date: 2026-08-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_visual_assets"
down_revision: Union[str, None] = "0003_currency"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "stored_assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("campaigns.id"), nullable=True),
        sa.Column("asset_type", sa.String(64), nullable=False),
        sa.Column("storage_key", sa.String(512), nullable=False),
        sa.Column("image_hash", sa.String(64), nullable=False),
        sa.Column("mime_type", sa.String(64), nullable=False, server_default="image/png"),
        sa.Column("width", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("height", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("file_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_library", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("library_key", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_stored_assets_campaign_id", "stored_assets", ["campaign_id"])
    op.create_index("ix_stored_assets_asset_type", "stored_assets", ["asset_type"])
    op.create_index("ix_stored_assets_image_hash", "stored_assets", ["image_hash"])
    op.create_unique_constraint("uq_stored_assets_storage_key", "stored_assets", ["storage_key"])
    op.create_unique_constraint("uq_stored_assets_library_key", "stored_assets", ["library_key"])

    op.create_table(
        "location_visuals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("location_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("locations.id"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("stored_asset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stored_assets.id"), nullable=True),
        sa.Column("prompt", sa.Text(), nullable=False, server_default=""),
        sa.Column("visual_state_hash", sa.String(64), nullable=False),
        sa.Column("generation_model", sa.String(128), nullable=False, server_default="mock"),
        sa.Column("generation_parameters", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_location_visuals_location_id", "location_visuals", ["location_id"])
    op.create_index("ix_location_visuals_visual_state_hash", "location_visuals", ["visual_state_hash"])

    op.add_column("locations", sa.Column("normalized_name", sa.String(128), nullable=False, server_default=""))
    op.add_column("locations", sa.Column("biome", sa.String(128), nullable=False, server_default=""))
    op.add_column("locations", sa.Column("terrain", sa.String(128), nullable=False, server_default=""))
    op.add_column("locations", sa.Column("architecture", sa.String(128), nullable=False, server_default=""))
    op.add_column("locations", sa.Column("atmosphere", sa.String(128), nullable=False, server_default=""))
    op.add_column("locations", sa.Column("weather", sa.String(64), nullable=False, server_default=""))
    op.add_column("locations", sa.Column("time_of_day", sa.String(64), nullable=False, server_default=""))
    op.add_column(
        "locations",
        sa.Column("important_features", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
    )
    op.add_column("locations", sa.Column("discovered", sa.Boolean(), nullable=False, server_default=sa.text("true")))
    op.add_column(
        "locations",
        sa.Column("coordinates", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.add_column(
        "locations",
        sa.Column("visual_style", sa.String(128), nullable=False, server_default="dark fantasy RPG"),
    )
    op.add_column("locations", sa.Column("visual_prompt", sa.Text(), nullable=False, server_default=""))
    op.add_column("locations", sa.Column("visual_state_hash", sa.String(64), nullable=False, server_default=""))
    op.add_column(
        "locations",
        sa.Column("active_visual_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column("locations", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_locations_normalized_name", "locations", ["normalized_name"])
    op.create_index("ix_locations_parent_id", "locations", ["parent_id"])
    op.execute(
        sa.text(
            "UPDATE locations SET normalized_name = lower(regexp_replace(name, '[^a-zA-Z0-9 ]', '', 'g')) "
            "WHERE normalized_name = '' OR normalized_name IS NULL"
        )
    )

    op.create_table(
        "asset_generation_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("campaigns.id"), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asset_type", sa.String(64), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False, server_default=""),
        sa.Column("model", sa.String(128), nullable=False, server_default="mock"),
        sa.Column("state", sa.String(32), nullable=False, server_default="PENDING"),
        sa.Column("visual_state_hash", sa.String(64), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text(), nullable=False, server_default=""),
        sa.Column("result_asset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stored_assets.id"), nullable=True),
        sa.Column("params", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "campaign_id",
            "entity_id",
            "asset_type",
            "visual_state_hash",
            name="uq_asset_job_entity_hash",
        ),
    )
    op.create_index("ix_asset_generation_jobs_campaign_id", "asset_generation_jobs", ["campaign_id"])
    op.create_index("ix_asset_generation_jobs_entity_id", "asset_generation_jobs", ["entity_id"])
    op.create_index("ix_asset_generation_jobs_state", "asset_generation_jobs", ["state"])

    op.create_table(
        "npc_appearances",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("npc_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("npcs.id"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("appearance", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("visual_state_hash", sa.String(64), nullable=False),
        sa.Column("stored_asset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stored_assets.id"), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_npc_appearances_npc_id", "npc_appearances", ["npc_id"])

    op.create_table(
        "character_appearances",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("character_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("characters.id"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("appearance", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("visual_state_hash", sa.String(64), nullable=False),
        sa.Column("stored_asset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stored_assets.id"), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_character_appearances_character_id", "character_appearances", ["character_id"])

    op.create_table(
        "item_visuals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("items.id"), nullable=True),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("campaigns.id"), nullable=True),
        sa.Column("library_key", sa.String(128), nullable=True),
        sa.Column("visual_meta", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("visual_state_hash", sa.String(64), nullable=False),
        sa.Column("stored_asset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stored_assets.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_item_visuals_item_id", "item_visuals", ["item_id"])
    op.create_index("ix_item_visuals_campaign_id", "item_visuals", ["campaign_id"])
    op.create_index("ix_item_visuals_library_key", "item_visuals", ["library_key"])


def downgrade() -> None:
    op.drop_table("item_visuals")
    op.drop_table("character_appearances")
    op.drop_table("npc_appearances")
    op.drop_table("asset_generation_jobs")
    op.drop_index("ix_locations_parent_id", "locations")
    op.drop_index("ix_locations_normalized_name", "locations")
    for col in (
        "updated_at",
        "active_visual_id",
        "visual_state_hash",
        "visual_prompt",
        "visual_style",
        "coordinates",
        "discovered",
        "important_features",
        "time_of_day",
        "weather",
        "atmosphere",
        "architecture",
        "terrain",
        "biome",
        "normalized_name",
    ):
        op.drop_column("locations", col)
    op.drop_table("location_visuals")
    op.drop_table("stored_assets")
