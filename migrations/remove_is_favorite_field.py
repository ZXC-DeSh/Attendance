"""Remove is_favorite field

Revision ID: remove_is_favorite_field
Revises: add_user_favorites_table
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'remove_is_favorite_field'
down_revision = 'add_user_favorites_table'
branch_labels = None
depends_on = None

def upgrade():
    op.drop_column('course', 'is_favorite')

def downgrade():
    op.add_column('course', sa.Column('is_favorite', sa.Boolean(), nullable=True))
