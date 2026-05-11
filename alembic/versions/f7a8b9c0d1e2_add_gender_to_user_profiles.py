"""add_gender_to_user_profiles

Revision ID: f7a8b9c0d1e2
Revises: c24520d59c7f
Create Date: 2026-05-11 08:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f7a8b9c0d1e2'
down_revision: Union[str, None] = 'c24520d59c7f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add gender column to user_profiles table
    op.add_column('user_profiles', sa.Column('gender', sa.String(length=20), nullable=True))


def downgrade() -> None:
    # Drop gender column from user_profiles table
    op.drop_column('user_profiles', 'gender')
