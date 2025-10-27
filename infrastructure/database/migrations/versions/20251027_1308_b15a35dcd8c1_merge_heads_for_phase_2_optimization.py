"""Merge heads for Phase 2 optimization

Revision ID: b15a35dcd8c1
Revises: 1b8bf20bc51c, seed_default_admin_user
Create Date: 2025-10-27 13:08:38.306991

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b15a35dcd8c1"
down_revision: Union[str, None] = ("1b8bf20bc51c", "seed_default_admin_user")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""
    pass


def downgrade() -> None:
    """Downgrade database schema."""
    pass
