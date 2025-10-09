"""add column current_location

Revision ID: d026094152f8
Revises: 2800b7dcee15
Create Date: 2025-10-09 13:16:24.180427

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd026094152f8'
down_revision: Union[str, Sequence[str], None] = '2800b7dcee15'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('current_location', sa.String(100)))


def downgrade() -> None:
    """Downgrade schema."""
    pass
