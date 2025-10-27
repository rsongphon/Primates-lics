"""add status column to experiments table

Revision ID: 6de3554a44cd
Revises: 3d3e68596ea7
Create Date: 2025-10-25 10:48:42.815794

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6de3554a44cd"
down_revision: Union[str, None] = "3d3e68596ea7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""
    # Create ENUM type for experiment status
    experiment_status_enum = sa.Enum(
        'draft', 'ready', 'running', 'paused', 'completed', 'cancelled', 'error',
        name='experimentstatus',
        create_type=True
    )
    experiment_status_enum.create(op.get_bind(), checkfirst=True)

    # Add status column to experiments table
    op.add_column(
        'experiments',
        sa.Column(
            'status',
            sa.Enum(
                'draft', 'ready', 'running', 'paused', 'completed', 'cancelled', 'error',
                name='experimentstatus'
            ),
            nullable=False,
            server_default='draft'
        )
    )

    # Create index on status column
    op.create_index(
        'idx_experiments_status',
        'experiments',
        ['status']
    )


def downgrade() -> None:
    """Downgrade database schema."""
    # Drop index
    op.drop_index('idx_experiments_status', table_name='experiments')

    # Drop status column
    op.drop_column('experiments', 'status')

    # Drop ENUM type
    sa.Enum(name='experimentstatus').drop(op.get_bind(), checkfirst=True)
