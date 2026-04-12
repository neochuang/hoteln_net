"""add api_keys and cleaning_records tables

Revision ID: fd4bc78ceafe
Revises:
Create Date: 2026-04-11 22:14:55.267701

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'fd4bc78ceafe'
down_revision: Union[str, Sequence[str], None] = '0001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'api_keys',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('key_hash', sa.String(255), nullable=False),
        sa.Column('key_prefix', sa.String(8), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        'cleaning_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('room_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('rooms.id'), nullable=False),
        sa.Column('cleaning_type', sa.Enum('checkout', 'daily', name='cleaningtype'), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cleaned_by_name', sa.String(50), nullable=True),
        sa.Column('reported_via', sa.Enum('device', 'staff', name='reportedvia'), nullable=True),
        sa.Column('api_key_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('api_keys.id'), nullable=True),
        sa.Column('staff_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('cleaning_records')
    op.drop_table('api_keys')
    sa.Enum(name='cleaningtype').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='reportedvia').drop(op.get_bind(), checkfirst=True)
