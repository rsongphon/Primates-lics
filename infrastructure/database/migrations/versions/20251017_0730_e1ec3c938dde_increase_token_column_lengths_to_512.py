"""increase token column lengths to 512

Revision ID: e1ec3c938dde
Revises: seed_default_test_org
Create Date: 2025-10-17 07:30:56.289942

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e1ec3c938dde"
down_revision: Union[str, None] = "seed_default_test_org"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema - increase token column lengths."""
    # Increase email_verification_token from VARCHAR(255) to VARCHAR(512)
    op.alter_column(
        "users",
        "email_verification_token",
        existing_type=sa.String(length=255),
        type_=sa.String(length=512),
        existing_nullable=True,
    )

    # Increase password_reset_token from VARCHAR(255) to VARCHAR(512)
    op.alter_column(
        "users",
        "password_reset_token",
        existing_type=sa.String(length=255),
        type_=sa.String(length=512),
        existing_nullable=True,
    )


def downgrade() -> None:
    """Downgrade database schema - revert token column lengths."""
    # Revert email_verification_token from VARCHAR(512) to VARCHAR(255)
    op.alter_column(
        "users",
        "email_verification_token",
        existing_type=sa.String(length=512),
        type_=sa.String(length=255),
        existing_nullable=True,
    )

    # Revert password_reset_token from VARCHAR(512) to VARCHAR(255)
    op.alter_column(
        "users",
        "password_reset_token",
        existing_type=sa.String(length=512),
        type_=sa.String(length=255),
        existing_nullable=True,
    )
