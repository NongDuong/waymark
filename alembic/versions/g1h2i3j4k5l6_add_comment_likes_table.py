"""Add comment_likes table

Revision ID: g1h2i3j4k5l6
Revises: f7a8b9c0d1e2
Create Date: 2026-05-21 11:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'g1h2i3j4k5l6'
down_revision: Union[str, None] = 'f7a8b9c0d1e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'comment_likes',
        sa.Column('comment_id', sa.UUID(), sa.ForeignKey('comments.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('user_id', sa.UUID(), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('comment_likes')
