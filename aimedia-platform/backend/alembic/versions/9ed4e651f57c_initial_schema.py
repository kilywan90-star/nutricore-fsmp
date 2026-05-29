"""initial_schema

Revision ID: 9ed4e651f57c
Revises:
Create Date: 2026-05-10 23:53:50.995877
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '9ed4e651f57c'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('hospitals',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('code', sa.String(50), nullable=False),
        sa.Column('level', sa.String(20), nullable=True),
        sa.Column('admin_phone', sa.String(20), nullable=True),
        sa.Column('review_config', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    op.create_table('channels',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('hospital_id', sa.String(36), nullable=False),
        sa.Column('name', sa.String(50), nullable=False),
        sa.Column('display_name', sa.String(100), nullable=False),
        sa.Column('config', sa.JSON(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['hospital_id'], ['hospitals.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('users',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('hospital_id', sa.String(36), nullable=False),
        sa.Column('username', sa.String(100), nullable=False),
        sa.Column('hashed_password', sa.String(200), nullable=False),
        sa.Column('display_name', sa.String(100), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('department', sa.String(100), nullable=True),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['hospital_id'], ['hospitals.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username')
    )
    op.create_table('contents',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('hospital_id', sa.String(36), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('content_type', sa.String(20), nullable=False),
        sa.Column('body', sa.JSON(), nullable=False),
        sa.Column('cover_url', sa.String(500), nullable=True),
        sa.Column('ai_generated', sa.Boolean(), nullable=False),
        sa.Column('ai_generated_parts', sa.JSON(), nullable=True),
        sa.Column('medical_tags', sa.JSON(), nullable=True),
        sa.Column('source_references', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('created_by', sa.String(36), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['hospital_id'], ['hospitals.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('doctor_profiles',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('license_no', sa.String(50), nullable=True),
        sa.Column('specialty', sa.String(200), nullable=True),
        sa.Column('title', sa.String(50), nullable=True),
        sa.Column('verified', sa.Boolean(), nullable=False),
        sa.Column('employed_since', sa.DateTime(), nullable=True),
        sa.Column('employed_until', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
    op.create_table('compliance_logs',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('content_id', sa.String(36), nullable=False),
        sa.Column('content_snapshot_hash', sa.String(64), nullable=False),
        sa.Column('rule_results', sa.JSON(), nullable=False),
        sa.Column('llm_results', sa.JSON(), nullable=True),
        sa.Column('privacy_findings', sa.JSON(), nullable=False),
        sa.Column('overall_verdict', sa.String(20), nullable=False),
        sa.Column('detected_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['content_id'], ['contents.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('publish_tasks',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('content_id', sa.String(36), nullable=False),
        sa.Column('channels', sa.JSON(), nullable=False),
        sa.Column('schedule_type', sa.String(20), nullable=False),
        sa.Column('scheduled_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('retry_count', sa.Integer(), nullable=False),
        sa.Column('result_detail', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['content_id'], ['contents.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('review_records',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('content_id', sa.String(36), nullable=False),
        sa.Column('review_level', sa.Integer(), nullable=False),
        sa.Column('reviewer_id', sa.String(36), nullable=False),
        sa.Column('action', sa.String(20), nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('compliance_report', sa.JSON(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('sla_deadline', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['content_id'], ['contents.id']),
        sa.ForeignKeyConstraint(['reviewer_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('publish_records',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('task_id', sa.String(36), nullable=False),
        sa.Column('channel', sa.String(50), nullable=False),
        sa.Column('external_id', sa.String(200), nullable=True),
        sa.Column('external_url', sa.String(500), nullable=True),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('error_message', sa.String(500), nullable=True),
        sa.Column('published_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['task_id'], ['publish_tasks.id']),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('publish_records')
    op.drop_table('review_records')
    op.drop_table('publish_tasks')
    op.drop_table('compliance_logs')
    op.drop_table('doctor_profiles')
    op.drop_table('contents')
    op.drop_table('users')
    op.drop_table('channels')
    op.drop_table('hospitals')
