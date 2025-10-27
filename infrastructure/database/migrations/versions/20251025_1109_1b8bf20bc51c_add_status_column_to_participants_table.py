"""add status column to participants table

Revision ID: 1b8bf20bc51c
Revises: 6de3554a44cd
Create Date: 2025-10-25 11:09:40.090819

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "1b8bf20bc51c"
down_revision: Union[str, None] = "6de3554a44cd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""
    # Create ENUM type for participant status
    participant_status_enum = sa.Enum(
        'active', 'inactive', 'completed', 'withdrawn',
        name='participantstatus',
        create_type=True
    )
    participant_status_enum.create(op.get_bind(), checkfirst=True)

    # Add status column to participants table
    op.add_column(
        'participants',
        sa.Column(
            'status',
            sa.Enum(
                'active', 'inactive', 'completed', 'withdrawn',
                name='participantstatus'
            ),
            nullable=False,
            server_default='active'
        )
    )

    # Create index on status column
    op.create_index(
        'idx_participants_status_new',
        'participants',
        ['status']
    )


def downgrade() -> None:
    """Downgrade database schema."""
    # Drop index
    op.drop_index('idx_participants_status_new', table_name='participants')

    # Drop status column
    op.drop_column('participants', 'status')

    # Drop ENUM type
    sa.Enum(name='participantstatus').drop(op.get_bind(), checkfirst=True)
