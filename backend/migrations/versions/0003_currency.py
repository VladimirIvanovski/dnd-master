"""Add silver and copper currency columns.

Revision ID: 0003_currency
Revises: 0002_user_password
Create Date: 2026-08-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_currency"
down_revision: Union[str, None] = "0002_user_password"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "characters",
        sa.Column("silver", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "characters",
        sa.Column("copper", sa.Integer(), nullable=False, server_default="0"),
    )
    op.alter_column("characters", "silver", server_default=None)
    op.alter_column("characters", "copper", server_default=None)
    # New characters start broke; zero existing starter gold too.
    op.execute(sa.text("UPDATE characters SET gold = 0"))


def downgrade() -> None:
    op.drop_column("characters", "copper")
    op.drop_column("characters", "silver")
