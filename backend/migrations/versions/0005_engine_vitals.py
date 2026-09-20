"""Visual skipped — engine vitals / inventory constraints.

Revision ID: 0005_engine_vitals
Revises: 0004_visual_assets
Create Date: 2026-08-21
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_engine_vitals"
down_revision: Union[str, None] = "0004_visual_assets"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "characters",
        sa.Column("temp_hp", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "character_items",
        sa.Column("durability", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("character_items", "durability")
    op.drop_column("characters", "temp_hp")
