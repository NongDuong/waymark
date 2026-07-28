"""add in-app subscriptions

Revision ID: i8j9k0l1m2n3
Revises: h7i8j9k0l1m2
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "i8j9k0l1m2n3"
down_revision: Union[str, None] = "h7i8j9k0l1m2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column("users", sa.Column("subscription_tier", sa.String(20), nullable=False, server_default="normal"))
    op.add_column("users", sa.Column("subscription_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.create_table(
        "in_app_purchases",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("platform", sa.String(20), nullable=False),
        sa.Column("product_id", sa.String(255), nullable=False),
        sa.Column("transaction_id", sa.String(255), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("purchased_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_verification", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("transaction_id"),
    )
    op.create_index("ix_in_app_purchases_user_id", "in_app_purchases", ["user_id"])

def downgrade() -> None:
    op.drop_index("ix_in_app_purchases_user_id", table_name="in_app_purchases")
    op.drop_table("in_app_purchases")
    op.drop_column("users", "subscription_expires_at")
    op.drop_column("users", "subscription_tier")
