"""Advanced indexing strategy for Phase 2 optimization

Revision ID: 88689b09d906
Revises: b15a35dcd8c1
Create Date: 2025-10-27 13:09:00.377032

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "88689b09d906"
down_revision: Union[str, None] = "b15a35dcd8c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema with advanced indexing strategy for Phase 2 optimization."""

    # Part 1: Full-Text Search Indexes
    # Experiments full-text search index
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_experiments_search
        ON experiments USING gin(
            to_tsvector('english', COALESCE(name, '') || ' ' || COALESCE(description, ''))
        );
    """)

    # Tasks full-text search index
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_tasks_search
        ON tasks USING gin(
            to_tsvector('english', COALESCE(name, '') || ' ' || COALESCE(description, ''))
        );
    """)

    # Part 2: Performance-Critical Composite Indexes
    # Status + date queries (most common pattern)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_experiments_status_date
        ON experiments(status, created_at DESC);
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_participants_id_date
        ON participants(participant_id, enrollment_date DESC);
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_task_executions_participant_status
        ON task_executions(participant_id, status, started_at DESC);
    """)

    # Organization-specific queries
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_experiments_org_status_date
        ON experiments(organization_id, status, created_at DESC);
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_devices_org_status
        ON devices(organization_id, status, last_heartbeat_at DESC);
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_tasks_org_category
        ON tasks(organization_id, category, is_template, created_at DESC);
    """)

    # Task execution performance
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_task_executions_exp_status
        ON task_executions(experiment_id, status, started_at DESC);
    """)

    # Part 3: Partial Indexes for Filtered Queries
    # Active devices only
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_devices_active_org
        ON devices(organization_id, last_heartbeat_at)
        WHERE status = 'online' AND is_active = true;
    """)

    # Running experiments only
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_experiments_running_org
        ON experiments(organization_id, updated_at)
        WHERE status = 'running';
    """)

    # Active participants
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_participants_active_exp
        ON participants(experiment_id, status)
        WHERE status = 'active';
    """)

    # Device data for recent telemetry (simplified partial index)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_device_data_device_timestamp
        ON device_data(device_id, timestamp DESC);
    """)

    # Part 4: JSONB GIN Indexes
    # Hardware configuration search
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_devices_hardware_config
        ON devices USING gin(hardware_config);
    """)

    # Note: Skip JSON GIN indexes for json columns (require jsonb type)
    # Tasks default_parameters is json type, not jsonb - skip GIN index
    # Device data has json columns but they require jsonb for GIN indexing


def downgrade() -> None:
    """Downgrade database schema by removing advanced indexes."""

    # Part 4: Remove JSONB GIN Indexes
    op.drop_index('idx_devices_hardware_config', table_name='devices', if_exists=True)

    # Part 3: Remove Partial Indexes
    op.drop_index('idx_device_data_device_timestamp', table_name='device_data', if_exists=True)
    op.drop_index('idx_participants_active_exp', table_name='participants', if_exists=True)
    op.drop_index('idx_experiments_running_org', table_name='experiments', if_exists=True)
    op.drop_index('idx_devices_active_org', table_name='devices', if_exists=True)

    # Part 2: Remove Composite Indexes
    op.drop_index('idx_tasks_org_category', table_name='tasks', if_exists=True)
    op.drop_index('idx_devices_org_status', table_name='devices', if_exists=True)
    op.drop_index('idx_experiments_org_status_date', table_name='experiments', if_exists=True)
    op.drop_index('idx_task_executions_participant_status', table_name='task_executions', if_exists=True)
    op.drop_index('idx_participants_id_date', table_name='participants', if_exists=True)
    op.drop_index('idx_experiments_status_date', table_name='experiments', if_exists=True)

    # Part 1: Remove Full-Text Search Indexes
    op.drop_index('idx_tasks_search', table_name='tasks', if_exists=True)
    op.drop_index('idx_experiments_search', table_name='experiments', if_exists=True)
