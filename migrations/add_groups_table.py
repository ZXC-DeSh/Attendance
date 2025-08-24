"""Add groups table

Revision ID: add_groups_table
Revises: remove_is_favorite_field
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_groups_table'
down_revision = 'remove_is_favorite_field'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('group',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=20), nullable=False),
        sa.Column('specialty', sa.String(length=50), nullable=False),
        sa.Column('course_year', sa.Integer(), nullable=False),
        sa.Column('group_number', sa.Integer(), nullable=False),
        sa.Column('max_students', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_index(op.f('ix_group_name'), 'group', ['name'], unique=True)
    op.create_index(op.f('ix_group_specialty'), 'group', ['specialty'], unique=False)
    op.create_index(op.f('ix_group_course_year'), 'group', ['course_year'], unique=False)
    
    op.create_table('student_group_association',
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('group_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['group_id'], ['group.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['student_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('student_id', 'group_id')
    )
    
    op.create_index(op.f('ix_student_group_association_student_id'), 'student_group_association', ['student_id'], unique=False)
    op.create_index(op.f('ix_student_group_association_group_id'), 'student_group_association', ['group_id'], unique=False)

def downgrade():
    op.drop_index(op.f('ix_student_group_association_group_id'), table_name='student_group_association')
    op.drop_index(op.f('ix_student_group_association_student_id'), table_name='student_group_association')
    
    op.drop_table('student_group_association')
    
    op.drop_index(op.f('ix_group_course_year'), table_name='group')
    op.drop_index(op.f('ix_group_specialty'), table_name='group')
    op.drop_index(op.f('ix_group_name'), table_name='group')
    
    op.drop_table('group')
