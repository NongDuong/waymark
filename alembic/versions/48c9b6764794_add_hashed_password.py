"""add hashed_password

Revision ID: 48c9b6764794
Revises: 0001_init
Create Date: 2026-05-06 07:29:25.453405

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from geoalchemy2 import Geography

# revision identifiers, used by Alembic.
revision: str = '48c9b6764794'
down_revision: Union[str, None] = '0001_init'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('hashed_password', sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'hashed_password')
