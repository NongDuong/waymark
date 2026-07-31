"""replace in-app purchases with frontend-activated packages

Revision ID: j9k0l1m2n3o4
Revises: i8j9k0l1m2n3
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "j9k0l1m2n3o4"
down_revision: Union[str, None] = "i8j9k0l1m2n3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("users", "subscription_tier", new_column_name="package_id")
    op.alter_column("users", "subscription_expires_at", new_column_name="package_expires_at")
    # Existing `normal` users become NULL below, so remove NOT NULL/default first.
    op.alter_column(
        "users",
        "package_id",
        existing_type=sa.String(20),
        type_=sa.String(30),
        nullable=True,
        server_default=None,
    )
    op.execute(
        "UPDATE users SET package_id = CASE "
        "WHEN package_id = 'premium' THEN 'premium_package' "
        "WHEN package_id = 'standard' THEN 'standard_package' "
        "ELSE NULL END"
    )
    op.drop_table("in_app_purchases")


def downgrade() -> None:
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
        sa.Column("raw_verification", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("transaction_id"),
    )
    op.create_index("ix_in_app_purchases_user_id", "in_app_purchases", ["user_id"])
    op.execute(
        "UPDATE users SET package_id = CASE "
        "WHEN package_id = 'premium_package' THEN 'premium' "
        "WHEN package_id = 'standard_package' THEN 'standard' "
        "ELSE 'normal' END"
    )
    op.alter_column("users", "package_id", existing_type=sa.String(30), type_=sa.String(20), nullable=False, server_default="normal")
    op.alter_column("users", "package_id", new_column_name="subscription_tier")
    op.alter_column("users", "package_expires_at", new_column_name="subscription_expires_at")
