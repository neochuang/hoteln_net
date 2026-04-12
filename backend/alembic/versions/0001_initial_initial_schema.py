"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-04-11 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0001_initial'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- users ---
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('username', sa.String(50), unique=True, index=True, nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(100), nullable=False),
        sa.Column('role', sa.Enum('admin', 'staff', 'readonly', name='userrole'), nullable=False, server_default='staff'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- guests ---
    op.create_table(
        'guests',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('first_name', sa.String(50), nullable=False),
        sa.Column('last_name', sa.String(50), nullable=False),
        sa.Column('id_type', sa.Enum('national_id', 'passport', 'other', name='idtype'), nullable=False),
        sa.Column('id_number', sa.String(50), nullable=False),
        sa.Column('phone', sa.String(20), nullable=False),
        sa.Column('email', sa.String(100), nullable=True),
        sa.Column('nationality', sa.String(50), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- room_types ---
    op.create_table(
        'room_types',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(50), unique=True, nullable=False),
        sa.Column('capacity', sa.Integer(), nullable=False),
        sa.Column('base_price', sa.Numeric(10, 2), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
    )

    # --- rooms ---
    op.create_table(
        'rooms',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('room_number', sa.String(10), unique=True, index=True, nullable=False),
        sa.Column('floor', sa.Integer(), nullable=False),
        sa.Column('room_type_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('room_types.id'), nullable=False),
        sa.Column('status', sa.Enum('available', 'occupied', 'cleaning', 'maintenance', name='roomstatus'), nullable=False, server_default='available'),
        sa.Column('notes', sa.Text(), nullable=True),
    )

    # --- reservations ---
    op.create_table(
        'reservations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('guest_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('guests.id'), nullable=False),
        sa.Column('room_type_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('room_types.id'), nullable=False),
        sa.Column('room_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('rooms.id'), nullable=True),
        sa.Column('check_in_date', sa.Date(), nullable=False),
        sa.Column('check_out_date', sa.Date(), nullable=False),
        sa.Column('num_guests', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('confirmed', 'checked_in', 'checked_out', 'cancelled', name='reservationstatus'), nullable=False, server_default='confirmed'),
        sa.Column('includes_breakfast', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('breakfast_guests', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_price', sa.Numeric(10, 2), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- checkin_records ---
    op.create_table(
        'checkin_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('reservation_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('reservations.id'), unique=True, nullable=False),
        sa.Column('room_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('rooms.id'), nullable=False),
        sa.Column('checked_in_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('checked_in_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('checked_out_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('checked_out_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
    )

    # --- breakfast_records ---
    op.create_table(
        'breakfast_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('reservation_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('reservations.id'), nullable=False),
        sa.Column('guest_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('guests.id'), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('meal_time', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('is_extra_purchase', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('extra_price', sa.Numeric(10, 2), nullable=True),
        sa.Column('recorded_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.UniqueConstraint('reservation_id', 'guest_id', 'date', name='uq_breakfast_per_guest_per_day'),
    )


def downgrade() -> None:
    op.drop_table('breakfast_records')
    op.drop_table('checkin_records')
    op.drop_table('reservations')
    op.drop_table('rooms')
    op.drop_table('room_types')
    op.drop_table('guests')
    op.drop_table('users')
    for enum_name in ['userrole', 'idtype', 'roomstatus', 'reservationstatus']:
        sa.Enum(name=enum_name).drop(op.get_bind(), checkfirst=True)
