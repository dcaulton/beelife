"""make analysis_reports datetimes timezone aware

Revision ID: 6a50c824aff4
Revises: b5d779fc903e
Create Date: 2026-06-26 15:36:27.211936

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '6a50c824aff4'
down_revision: Union[str, Sequence[str], None] = 'b5d779fc903e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Make sure started_at and created_at are proper timestamptz
    op.alter_column(
        'analysis_reports',
        'started_at',
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=False,
    )
    op.alter_column(
        'analysis_reports',
        'created_at',
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=False,
        existing_server_default=sa.text('now()'),
    )


def downgrade() -> None:
    # Revert to previous state if needed
    op.alter_column(
        'analysis_reports',
        'started_at',
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=True,
    )
    op.alter_column(
        'analysis_reports',
        'created_at',
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=True,
        existing_server_default=sa.text('now()'),
    )
