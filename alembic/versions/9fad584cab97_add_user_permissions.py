"""add_user_permissions

Revision ID: 9fad584cab97
Revises: 296feec7bf34
Create Date: 2026-05-08 17:27:27.865302

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '9fad584cab97'
down_revision: Union[str, None] = '296feec7bf34'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Safely only add the permissions JSONB column to users table
    op.add_column('users', sa.Column('permissions', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    # Safely only drop the permissions JSONB column from users table
    op.drop_column('users', 'permissions')
