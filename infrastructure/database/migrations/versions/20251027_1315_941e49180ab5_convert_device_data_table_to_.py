"""Convert device_data table to TimescaleDB hypertable for Phase 2 optimization

Revision ID: 941e49180ab5
Revises: 88689b09d906
Create Date: 2025-10-27 13:15:08.945442

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "941e49180ab5"
down_revision: Union[str, None] = "88689b09d906"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema by converting device_data to TimescaleDB hypertable."""

    # Drop existing indexes that might conflict with hypertable conversion
    # The primary key constraint will be automatically recreated by TimescaleDB
    op.execute("""
        ALTER TABLE device_data DROP CONSTRAINT IF EXISTS pk_device_data CASCADE;
    """)

    # Convert device_data table to hypertable with timestamp as time column
    # TimescaleDB will automatically recreate the primary key including timestamp
    op.execute("""
        SELECT create_hypertable(
            'device_data',
            'timestamp',
            chunk_time_interval => INTERVAL '7 days',
            migrate_data => true
        );
    """)

    # Recreate the primary key to include both id and timestamp for hypertable compatibility
    op.execute("""
        ALTER TABLE device_data ADD PRIMARY KEY (id, timestamp);
    """)

    # Create optimized index for time-series queries on hypertable
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_device_data_hypertable_time_device
        ON device_data (timestamp DESC, device_id);
    """)

    # Skip compression for now due to foreign key constraints
    # Can be added later in a separate migration after testing

    # Create retention policy to delete data older than 1 year (optional)
    # Commented out for now - can be enabled based on requirements
    # op.execute("""
    #     SELECT add_retention_policy(
    #         'device_data',
    #         INTERVAL '1 year'
    #     );
    # """)


def downgrade() -> None:
    """Downgrade database schema by removing TimescaleDB hypertable."""

    # Drop hypertable-specific index
    op.drop_index('idx_device_data_hypertable_time_device', table_name='device_data', if_exists=True)

    # Convert hypertable back to regular table
    op.execute("""
        DROP TABLE IF EXISTS device_data CASCADE;
    """)

    # Note: The regular table structure will be recreated by previous migrations
    # This is a simplified downgrade - in production you might want to preserve data
