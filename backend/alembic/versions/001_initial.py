"""Initial database schema — regenerated to match current models

Revision ID: 001_initial
Revises:
Create Date: 2026-06-28

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False, index=True),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_superuser', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('api_key_hash', sa.String(64), nullable=True, unique=True, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        'crash_analyses',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        # File info
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('file_hash', sa.String(64), nullable=False, index=True),
        sa.Column('storage_path', sa.String(512), nullable=False),
        # Status
        sa.Column('status', sa.String(20), nullable=False, index=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        # Parsed data
        sa.Column('exception_code', sa.String(20), nullable=True, index=True),
        sa.Column('exception_message', sa.Text(), nullable=True),
        sa.Column('faulting_module', sa.String(255), nullable=True, index=True),
        sa.Column('faulting_address', sa.String(20), nullable=True),
        sa.Column('stack_trace', sa.JSON(), nullable=True),
        sa.Column('loaded_modules', sa.JSON(), nullable=True),
        sa.Column('threads', sa.JSON(), nullable=True),
        # LLM analysis
        sa.Column('root_cause', sa.Text(), nullable=True),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('solutions', sa.JSON(), nullable=True),
        sa.Column('severity', sa.String(20), nullable=True, index=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('references', sa.JSON(), nullable=True),
        sa.Column('llm_analysis', sa.JSON(), nullable=True),
        sa.Column('llm_provider', sa.String(50), nullable=True),
        sa.Column('llm_model', sa.String(100), nullable=True),
        sa.Column('llm_cost_usd', sa.Float(), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        # RAG
        sa.Column('similar_crash_ids', sa.JSON(), nullable=True),
        sa.Column('similar_crashes', sa.JSON(), nullable=True),
        sa.Column('embedding_id', sa.String(100), nullable=True),
        # Metadata
        sa.Column('platform', sa.String(50), nullable=True),
        sa.Column('architecture', sa.String(20), nullable=True),
        sa.Column('os_version', sa.String(100), nullable=True),
        # User/session
        sa.Column('user_id', sa.String(100), nullable=True, index=True),
        sa.Column('session_id', sa.String(100), nullable=True, index=True),
        # Timing
        sa.Column('parse_duration_seconds', sa.Float(), nullable=True),
        sa.Column('analysis_duration_seconds', sa.Float(), nullable=True),
        # Advanced
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('crash_category', sa.String(50), nullable=True, index=True),
        sa.Column('related_issue_urls', sa.JSON(), nullable=True),
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('crash_analyses')
    op.drop_table('users')
