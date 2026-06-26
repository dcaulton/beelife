"""add analysis_reports table

Revision ID: b5d779fc903e
Revises: 4c160c3c823b
Create Date: 2026-06-26 14:44:41.632652

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b5d779fc903e'
down_revision: Union[str, Sequence[str], None] = '4c160c3c823b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'analysis_reports',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('device_id', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.String(), nullable=True),
        sa.Column('report_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_analysis_reports_device_id'), 'analysis_reports', ['device_id'], unique=False)
    op.create_index(op.f('ix_analysis_reports_status'), 'analysis_reports', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_analysis_reports_status'), table_name='analysis_reports')
    op.drop_index(op.f('ix_analysis_reports_device_id'), table_name='analysis_reports')
    op.drop_table('analysis_reports')
