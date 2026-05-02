"""add_cleaning_tasks_table

Revision ID: 1143063c5c1c
Revises: 20260418cleanreq
Create Date: 2026-05-02 22:37:06.922271

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '1143063c5c1c'
down_revision: Union[str, Sequence[str], None] = '20260418cleanreq'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'cleaning_tasks',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('room_id', sa.UUID(), nullable=False),
        sa.Column('assigned_to_user_id', sa.UUID(), nullable=False),
        sa.Column('assigned_by_user_id', sa.UUID(), nullable=False),
        sa.Column('status', sa.Enum('pending', 'in_progress', 'completed', 'cancelled', name='cleaningtaskstatus'), nullable=False),
        sa.Column('cleaning_type', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['assigned_by_user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['assigned_to_user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['room_id'], ['rooms.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('cleaning_tasks')
    sa.Enum(name='cleaningtaskstatus').drop(op.get_bind(), checkfirst=False)
