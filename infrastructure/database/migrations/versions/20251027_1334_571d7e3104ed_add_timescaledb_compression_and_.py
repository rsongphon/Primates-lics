"""Add TimescaleDB compression and retention policies for Phase 2 optimization

Revision ID: 571d7e3104ed
Revises: 941e49180ab5
Create Date: 2025-10-27 13:34:49.484578

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "571d7e3104ed"
down_revision: Union[str, None] = "941e49180ab5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema by adding TimescaleDB compression and retention policies."""

    # First, let's try to enable compression with a simpler approach
    # Drop foreign key constraints temporarily if they exist
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE constraint_name = 'fk_device_data_task_execution_id_task_executions'
                AND table_name = 'device_data'
            ) THEN
                ALTER TABLE device_data DROP CONSTRAINT fk_device_data_task_execution_id_task_executions;
            END IF;
        END $$;
    """)

    # Enable compression with compatible settings
    op.execute("""
        ALTER TABLE device_data SET (
            timescaledb.compress,
            timescaledb.compress_orderby = 'timestamp DESC, id'
        );
    """)

    # Add compression policy for data older than 14 days (shorter for dev environment)
    op.execute("""
        SELECT add_compression_policy(
            'device_data',
            INTERVAL '14 days'
        );
    """)

    # Add retention policy to delete data older than 90 days (dev environment)
    # Production would use longer retention (1-2 years)
    op.execute("""
        SELECT add_retention_policy(
            'device_data',
            INTERVAL '90 days'
        );
    """)

    # Note: Foreign key constraint cannot be recreated after compression is enabled
    # This is a TimescaleDB limitation. The constraint is documented but not enforced
    # Application logic should handle referential integrity for this table

    # Create continuous aggregates for common telemetry queries
    # Note: Create views WITHOUT DATA initially to avoid transaction issues
    # Hourly averages per device
    op.execute("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS device_data_hourly
        WITH (timescaledb.continuous) AS
        SELECT
            device_id,
            time_bucket('1 hour', timestamp) AS hour,
            data_type,
            AVG(numeric_value) as avg_numeric_value,
            MIN(numeric_value) as min_numeric_value,
            MAX(numeric_value) as max_numeric_value,
            COUNT(*) as sample_count
        FROM device_data
        WHERE numeric_value IS NOT NULL
        GROUP BY device_id, time_bucket('1 hour', timestamp), data_type
        WITH NO DATA;
    """)

    # Add refresh policy for the hourly aggregate (fixed window size)
    op.execute("""
        SELECT add_continuous_aggregate_policy(
            'device_data_hourly',
            start_offset => INTERVAL '3 hours',
            end_offset => INTERVAL '1 hour',
            schedule_interval => INTERVAL '1 hour'
        );
    """)

    # Daily device health summary
    op.execute("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS device_health_daily
        WITH (timescaledb.continuous) AS
        SELECT
            device_id,
            time_bucket('1 day', timestamp) AS day,
            COUNT(*) as total_readings,
            COUNT(DISTINCT data_type) as unique_data_types,
            MAX(timestamp) as last_reading_time,
            MIN(timestamp) as first_reading_time
        FROM device_data
        GROUP BY device_id, time_bucket('1 day', timestamp)
        WITH NO DATA;
    """)

    # Add refresh policy for the daily aggregate (fixed window size)
    op.execute("""
        SELECT add_continuous_aggregate_policy(
            'device_health_daily',
            start_offset => INTERVAL '3 days',
            end_offset => INTERVAL '1 day',
            schedule_interval => INTERVAL '1 day'
        );
    """)


def downgrade() -> None:
    """Downgrade database schema by removing TimescaleDB policies."""

    # Remove continuous aggregate policies
    op.execute("""
        SELECT remove_continuous_aggregate_policy('device_data_hourly', if_exists => TRUE);
    """)

    op.execute("""
        SELECT remove_continuous_aggregate_policy('device_health_daily', if_exists => TRUE);
    """)

    # Drop continuous aggregates
    op.execute("""
        DROP MATERIALIZED VIEW IF EXISTS device_health_daily CASCADE;
    """)

    op.execute("""
        DROP MATERIALIZED VIEW IF EXISTS device_data_hourly CASCADE;
    """)

    # Remove retention policy
    op.execute("""
        SELECT remove_retention_policy('device_data', if_exists => TRUE);
    """)

    # Remove compression policy
    op.execute("""
        SELECT remove_compression_policy('device_data', if_exists => TRUE);
    """)

    # Disable compression
    op.execute("""
        ALTER TABLE device_data SET (
            timescaledb.compress = FALSE
        );
    """)
