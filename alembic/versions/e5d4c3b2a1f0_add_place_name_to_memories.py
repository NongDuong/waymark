"""Add place_name column to memories

Revision ID: e5d4c3b2a1f0
Revises: f3a2b1c0d9e8
Create Date: 2026-05-07 22:01:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5d4c3b2a1f0'
down_revision: Union[str, None] = 'f3a2b1c0d9e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if column exists before adding to avoid errors
    # (using a raw SQL approach for robustness in this specific case)
    op.execute('ALTER TABLE memories ADD COLUMN IF NOT EXISTS place_name VARCHAR(255)')


def downgrade() -> None:
    op.drop_column('memories', 'place_name')
