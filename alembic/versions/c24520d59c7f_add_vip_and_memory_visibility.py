"""add_vip_and_memory_visibility

Revision ID: c24520d59c7f
Revises: 9fad584cab97
Create Date: 2026-05-10 16:36:24.380714

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c24520d59c7f'
down_revision: Union[str, None] = '9fad584cab97'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add columns to memories and users tables
    op.add_column('memories', sa.Column('visibility_expires_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('is_vip', sa.Boolean(), server_default='false', nullable=False))
    
    # Backfill visibility_expires_at for existing memories as posted_at + 30 days
    op.execute("UPDATE memories SET visibility_expires_at = posted_at + INTERVAL '30 days' WHERE visibility_expires_at IS NULL")


def downgrade() -> None:
    op.drop_column('users', 'is_vip')
    op.drop_column('memories', 'visibility_expires_at')
