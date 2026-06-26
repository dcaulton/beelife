"""add period_start and period_end to analysis_reports

Revision ID: 8d14c43489d0
Revises: 6a50c824aff4
Create Date: 2026-06-26 17:06:21.206739

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '8d14c43489d0'
down_revision: Union[str, Sequence[str], None] = '6a50c824aff4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('analysis_reports', sa.Column('period_start', sa.Date(), nullable=True))
    op.add_column('analysis_reports', sa.Column('period_end', sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column('analysis_reports', 'period_end')
    op.drop_column('analysis_reports', 'period_start')
