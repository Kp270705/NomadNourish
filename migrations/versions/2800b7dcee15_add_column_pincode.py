"""add column pincode

Revision ID: 2800b7dcee15
Revises: 
Create Date: 2025-10-09 12:38:28.525437

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2800b7dcee15'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('location', sa.String(100)))


def downgrade() -> None:
    """Downgrade schema."""
    pass
