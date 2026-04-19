"""add cleaning_requests table, cleaner role, api_keys.room_id

Revision ID: 20260418cleanreq
Revises: fd4bc78ceafe
Create Date: 2026-04-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260418cleanreq"
down_revision: Union[str, Sequence[str], None] = "fd4bc78ceafe"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Extend UserRole enum with 'cleaner' (Postgres-only). Must run outside txn.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'cleaner'")

    # 2. Add room_id to api_keys
    op.add_column(
        "api_keys",
        sa.Column("room_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_api_keys_room_id",
        "api_keys",
        "rooms",
        ["room_id"],
        ["id"],
    )

    # 3. Create cleaning_requests table
    op.create_table(
        "cleaning_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("room_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("rooms.id"), nullable=False),
        sa.Column("api_key_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("api_keys.id"), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("pending", "fulfilled", "cancelled", name="cleaningrequeststatus"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("requested_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("fulfilled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "fulfilled_by_cleaning_record_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cleaning_records.id"),
            nullable=True,
        ),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
    )

    # 4. Partial unique index: one pending request per room
    op.create_index(
        "uq_cleaning_requests_pending_room",
        "cleaning_requests",
        ["room_id"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.create_index(
        "ix_cleaning_requests_status_requested_at",
        "cleaning_requests",
        ["status", "requested_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_cleaning_requests_status_requested_at", table_name="cleaning_requests")
    op.drop_index("uq_cleaning_requests_pending_room", table_name="cleaning_requests")
    op.drop_table("cleaning_requests")
    sa.Enum(name="cleaningrequeststatus").drop(op.get_bind(), checkfirst=True)
    op.drop_constraint("fk_api_keys_room_id", "api_keys", type_="foreignkey")
    op.drop_column("api_keys", "room_id")
    # Note: cannot remove a value from a Postgres enum; cleaner role stays.
