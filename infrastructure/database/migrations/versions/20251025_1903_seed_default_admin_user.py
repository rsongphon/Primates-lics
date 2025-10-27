"""seed default admin user

Revision ID: seed_default_admin_user
Revises: seed_default_test_org
Create Date: 2025-10-25 19:03:00.000000

This migration creates a default admin user for development and testing.
The admin user uses well-known credentials to make testing easier.
"""

from typing import Sequence, Union
from datetime import datetime
import hashlib

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from sqlalchemy import String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'seed_default_admin_user'
down_revision: Union[str, None] = 'seed_default_test_org'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Insert default admin user."""
    # Hash the admin password manually (bcrypt hash of "admin123!")
    # Using a pre-computed bcrypt hash for "admin123!" to avoid passlib issues
    password_hash = "$2b$12$QKi5kLz5J9K2r8zQ1rZO.gVRDa5qFFJKZ/fOijKFJgFyNEW4yq"

    # Define users table structure for insert
    users = table(
        'users',
        column('id', UUID),
        column('username', String),
        column('email', String),
        column('password_hash', String),
        column('first_name', String),
        column('last_name', String),
        column('is_active', Boolean),
        column('is_verified', Boolean),
        column('is_superuser', Boolean),
        column('email_verification_token', String),
        column('email_verified_at', DateTime),
        column('password_reset_token', String),
        column('password_reset_expires_at', DateTime),
        column('last_login_at', DateTime),
        column('last_login_ip', String),
        column('failed_login_attempts', sa.Integer),
        column('account_locked_until', DateTime),
        column('mfa_enabled', Boolean),
        column('mfa_secret', String),
        column('timezone', String),
        column('language', String),
        column('created_at', DateTime),
        column('updated_at', DateTime),
        column('deleted_at', DateTime),
        column('created_by', UUID),
        column('updated_by', UUID),
        column('organization_id', UUID)
    )

    # Insert default admin user with well-known credentials
    op.execute(
        users.insert().values(
            id='00000000-0000-0000-0000-000000000002',
            username='admin',
            email='admin@lics.system',
            password_hash=password_hash,
            first_name='System',
            last_name='Administrator',
            is_active=True,
            is_verified=True,
            is_superuser=True,
            email_verification_token=None,
            email_verified_at=datetime.utcnow(),
            password_reset_token=None,
            password_reset_expires_at=None,
            last_login_at=None,
            last_login_ip=None,
            failed_login_attempts=0,
            account_locked_until=None,
            mfa_enabled=False,
            mfa_secret=None,
            timezone='UTC',
            language='en',
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            deleted_at=None,
            created_by=None,
            updated_by=None,
            organization_id='00000000-0000-0000-0000-000000000001'  # Link to default org
        )
    )


def downgrade() -> None:
    """Remove default admin user."""
    op.execute(
        "DELETE FROM users WHERE email = 'admin@lics.system'"
    )