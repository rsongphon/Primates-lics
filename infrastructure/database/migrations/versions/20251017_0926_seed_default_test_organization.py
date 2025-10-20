"""seed default test organization

Revision ID: seed_default_test_org
Revises: 207cea644e2f
Create Date: 2025-10-17 09:26:00.000000

This migration creates a default test organization for development and testing.
The organization uses a well-known UUID to make testing easier.
"""
from typing import Sequence, Union
from datetime import datetime

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from sqlalchemy import String, Boolean, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'seed_default_test_org'
down_revision: Union[str, None] = '207cea644e2f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Insert default test organization."""

    # Define organizations table structure for insert
    organizations = table(
        'organizations',
        column('id', UUID),
        column('name', String),
        column('description', String),
        column('settings', JSON),
        column('max_users', sa.Integer),
        column('max_devices', sa.Integer),
        column('is_active', Boolean),
        column('created_at', DateTime),
        column('updated_at', DateTime)
    )

    # Insert default test organization with well-known UUID
    op.execute(
        organizations.insert().values(
            id='00000000-0000-0000-0000-000000000001',
            name='Default Test Organization',
            description='Default organization for testing and development',
            settings={},
            max_users=None,
            max_devices=None,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    )


def downgrade() -> None:
    """Remove default test organization."""
    op.execute(
        "DELETE FROM organizations WHERE id = '00000000-0000-0000-0000-000000000001'"
    )
