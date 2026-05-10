"""init

Revision ID: 0001_init
Revises: 
Create Date: 2026-05-06 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from geoalchemy2 import Geography

# revision identifiers, used by Alembic.
revision: str = '0001_init'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # enable postgis
    op.execute('CREATE EXTENSION IF NOT EXISTS postgis;')

    # create users table
    op.create_table('users',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('status', sa.SmallInteger(), nullable=True),
    sa.Column('username', sa.String(length=30), nullable=True),
    sa.Column('primary_email', sa.String(length=255), nullable=True),
    sa.Column('primary_phone', sa.String(length=20), nullable=True),
    sa.Column('email_verified_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('phone_verified_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('username')
    )
    
    # create user_profiles table
    op.create_table('user_profiles',
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('display_name', sa.String(length=80), nullable=True),
    sa.Column('avatar_media_id', sa.UUID(), nullable=True),
    sa.Column('bio', sa.String(length=300), nullable=True),
    sa.Column('home_city', sa.String(length=120), nullable=True),
    sa.Column('country_code', sa.String(length=2), nullable=True),
    sa.Column('followers_count', sa.Integer(), nullable=True),
    sa.Column('following_count', sa.Integer(), nullable=True),
    sa.Column('total_likes_received', sa.Integer(), nullable=True),
    sa.Column('memories_count', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('user_id')
    )

    # create places table
    op.create_table('places',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('provider', sa.String(length=30), nullable=True),
    sa.Column('provider_place_id', sa.String(length=128), nullable=True),
    sa.Column('name', sa.String(length=255), nullable=True),
    sa.Column('address_text', sa.String(length=500), nullable=True),
    sa.Column('country_code', sa.String(length=2), nullable=True),
    sa.Column('admin1', sa.String(length=120), nullable=True),
    sa.Column('admin2', sa.String(length=120), nullable=True),
    sa.Column('location', Geography(geometry_type='POINT', srid=4326, from_text='ST_GeomFromEWKT', name='geometry'), nullable=True),
    sa.Column('geohash', sa.String(length=16), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )

    # create memories table
    op.create_table('memories',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=True),
    sa.Column('place_id', sa.UUID(), nullable=True),
    sa.Column('place_snapshot_id', sa.UUID(), nullable=True),
    sa.Column('privacy_level', sa.SmallInteger(), nullable=True),
    sa.Column('visibility_status', sa.SmallInteger(), nullable=True),
    sa.Column('caption', sa.Text(), nullable=True),
    sa.Column('mood_code', sa.String(length=32), nullable=True),
    sa.Column('location', Geography(geometry_type='POINT', srid=4326, from_text='ST_GeomFromEWKT', name='geometry'), nullable=True),
    sa.Column('geohash', sa.String(length=16), nullable=True),
    sa.Column('taken_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('posted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('comment_policy', sa.SmallInteger(), nullable=True),
    sa.Column('language_code', sa.String(length=8), nullable=True),
    sa.ForeignKeyConstraint(['place_id'], ['places.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('memories')
    op.drop_table('places')
    op.drop_table('user_profiles')
    op.drop_table('users')
    op.execute('DROP EXTENSION IF EXISTS postgis;')
