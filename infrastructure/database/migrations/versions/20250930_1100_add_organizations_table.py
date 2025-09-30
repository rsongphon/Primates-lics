"""add organizations table

Revision ID: add_organizations_table
Revises: 53c928d13d4a
Create Date: 2025-09-30 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_organizations_table'
down_revision: Union[str, None] = '53c928d13d4a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""
    # Create organizations table
    op.create_table('organizations',
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('settings', sa.JSON(), nullable=True),
        sa.Column('max_users', sa.Integer(), nullable=True),
        sa.Column('max_devices', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )

    # Add foreign key constraint to users table for organization_id
    op.create_foreign_key(
        'fk_users_organization_id',
        'users', 'organizations',
        ['organization_id'], ['id']
    )


def downgrade() -> None:
    """Downgrade database schema."""
    # Drop foreign key constraint
    op.drop_constraint('fk_users_organization_id', 'users', type_='foreignkey')

    # Drop organizations table
    op.drop_table('organizations')