"""Add schedule tables

Revision ID: add_schedule_tables
Revises: add_groups_table
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_schedule_tables'
down_revision = 'add_groups_table'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('room',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('number', sa.String(length=20), nullable=False),
        sa.Column('capacity', sa.Integer(), nullable=False),
        sa.Column('building', sa.String(length=50), nullable=False),
        sa.Column('room_type', sa.String(length=50), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_room_number'), 'room', ['number'], unique=True)
    
    op.create_table('schedule',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('group_id', sa.Integer(), nullable=False),
        sa.Column('course_id', sa.Integer(), nullable=False),
        sa.Column('teacher_id', sa.Integer(), nullable=False),
        sa.Column('room_id', sa.Integer(), nullable=False),
        sa.Column('day_of_week', sa.Integer(), nullable=False),
        sa.Column('slot_number', sa.Integer(), nullable=False),
        sa.Column('week_type', sa.String(length=10), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['course_id'], ['course.id'], ),
        sa.ForeignKeyConstraint(['group_id'], ['group.id'], ),
        sa.ForeignKeyConstraint(['room_id'], ['room.id'], ),
        sa.ForeignKeyConstraint(['teacher_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('teacher_substitution',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('original_schedule_id', sa.Integer(), nullable=False),
        sa.Column('substitute_teacher_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('reason', sa.String(length=200), nullable=True),
        sa.Column('is_confirmed', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['original_schedule_id'], ['schedule.id'], ),
        sa.ForeignKeyConstraint(['substitute_teacher_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade():
    op.drop_table('teacher_substitution')
    op.drop_table('schedule')
    op.drop_index(op.f('ix_room_number'), table_name='room')
    op.drop_table('room')
