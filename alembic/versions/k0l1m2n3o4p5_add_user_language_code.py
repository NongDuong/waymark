"""add user language code

Revision ID: k0l1m2n3o4p5
Revises: j9k0l1m2n3o4
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "k0l1m2n3o4p5"
down_revision: Union[str, None] = "j9k0l1m2n3o4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("language_code", sa.String(10), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "language_code")
