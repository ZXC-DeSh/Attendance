"""Add user favorites table

Revision ID: add_user_favorites_table
Revises: 
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_user_favorites_table'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('user_favorites',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('course_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['course_id'], ['course.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'course_id')
    )
    
    op.create_index(op.f('ix_user_favorites_user_id'), 'user_favorites', ['user_id'], unique=False)

def downgrade():
    op.drop_index(op.f('ix_user_favorites_user_id'), table_name='user_favorites')
    
    op.drop_table('user_favorites')
