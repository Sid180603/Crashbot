"""Add performance indexes

Revision ID: 002_add_indexes
Revises: 001_initial
Create Date: 2025-11-18

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '002_add_indexes'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add indexes for frequently queried columns"""
    # Add composite indexes for common query patterns
    op.create_index(
        'idx_crash_status_created',
        'crash_analyses',
        ['status', 'created_at'],
        unique=False
    )
    
    op.create_index(
        'idx_crash_user_created',
        'crash_analyses',
        ['user_id', 'created_at'],
        unique=False
    )
    
    op.create_index(
        'idx_crash_exception_severity',
        'crash_analyses',
        ['exception_code', 'severity'],
        unique=False
    )
    
    # Add index for embedding lookups
    op.create_index(
        'idx_crash_embedding',
        'crash_analyses',
        ['embedding_id'],
        unique=False
    )


def downgrade() -> None:
    """Remove indexes"""
    op.drop_index('idx_crash_embedding', table_name='crash_analyses')
    op.drop_index('idx_crash_exception_severity', table_name='crash_analyses')
    op.drop_index('idx_crash_user_created', table_name='crash_analyses')
    op.drop_index('idx_crash_status_created', table_name='crash_analyses')
