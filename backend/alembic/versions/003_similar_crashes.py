"""Add similar_crashes field

Revision ID: 003_similar_crashes
Revises: 002_add_indexes
Create Date: 2025-11-18

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003_similar_crashes'
down_revision = '002_add_indexes'
branch_labels = None
depends_on = None


def upgrade():
    # Add similar_crashes column
    op.add_column('crash_analyses', sa.Column('similar_crashes', postgresql.JSON(astext_type=sa.Text()), nullable=True))


def downgrade():
    # Remove similar_crashes column
    op.drop_column('crash_analyses', 'similar_crashes')
