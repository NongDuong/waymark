"""add_admin_and_reports

Revision ID: 296feec7bf34
Revises: e5d4c3b2a1f0
Create Date: 2026-05-08 16:47:27.877205

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '296feec7bf34'
down_revision: Union[str, None] = 'e5d4c3b2a1f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands adjusted to protect PostGIS/Tiger geocoder tables ###
    op.create_table('reports',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('reporter_id', sa.UUID(), nullable=True),
        sa.Column('target_id', sa.UUID(), nullable=True),
        sa.Column('target_type', sa.SmallInteger(), nullable=True),
        sa.Column('reason', sa.String(length=100), nullable=True),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('status', sa.SmallInteger(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['reporter_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.add_column('users', sa.Column('is_admin', sa.Boolean(), nullable=True, server_default='false'))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands adjusted to protect PostGIS/Tiger geocoder tables ###
    op.drop_column('users', 'is_admin')
    op.drop_table('reports')
    # ### end Alembic commands ###
