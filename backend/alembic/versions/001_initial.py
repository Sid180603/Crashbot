"""Initial database schema

Revision ID: 001_initial
Revises: 
Create Date: 2025-11-17

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('username', sa.String(length=100), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('is_superuser', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('api_key', sa.String(length=255), nullable=True),
        sa.Column('api_key_created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    op.create_index(op.f('ix_users_api_key'), 'users', ['api_key'], unique=False)

    # Create crash_analyses table
    op.create_table('crash_analyses',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('file_size', sa.BigInteger(), nullable=False),
        sa.Column('file_hash', sa.String(length=64), nullable=False),
        sa.Column('storage_path', sa.String(length=500), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('parse_duration_seconds', sa.Float(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        
        # Parsed crash information
        sa.Column('exception_code', sa.String(length=50), nullable=True),
        sa.Column('exception_message', sa.Text(), nullable=True),
        sa.Column('faulting_module', sa.String(length=255), nullable=True),
        sa.Column('faulting_address', sa.String(length=50), nullable=True),
        sa.Column('stack_trace', sa.Text(), nullable=True),
        sa.Column('loaded_modules', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('threads', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('platform', sa.String(length=50), nullable=True),
        sa.Column('architecture', sa.String(length=20), nullable=True),
        
        # LLM analysis results
        sa.Column('llm_analysis', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('llm_provider', sa.String(length=50), nullable=True),
        sa.Column('llm_model', sa.String(length=100), nullable=True),
        sa.Column('llm_cost_usd', sa.Float(), nullable=True),
        
        # Vector DB
        sa.Column('embedding_id', sa.String(length=100), nullable=True),
        sa.Column('similar_crashes', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        
        # Error tracking
        sa.Column('error_message', sa.Text(), nullable=True),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], )
    )
    op.create_index(op.f('ix_crash_analyses_file_hash'), 'crash_analyses', ['file_hash'], unique=False)
    op.create_index(op.f('ix_crash_analyses_status'), 'crash_analyses', ['status'], unique=False)
    op.create_index(op.f('ix_crash_analyses_created_at'), 'crash_analyses', ['created_at'], unique=False)
    op.create_index(op.f('ix_crash_analyses_exception_code'), 'crash_analyses', ['exception_code'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_crash_analyses_exception_code'), table_name='crash_analyses')
    op.drop_index(op.f('ix_crash_analyses_created_at'), table_name='crash_analyses')
    op.drop_index(op.f('ix_crash_analyses_status'), table_name='crash_analyses')
    op.drop_index(op.f('ix_crash_analyses_file_hash'), table_name='crash_analyses')
    op.drop_table('crash_analyses')
    
    op.drop_index(op.f('ix_users_api_key'), table_name='users')
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
