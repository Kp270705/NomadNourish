"""adding cuisine_type column in cuisines

Revision ID: 6a1c3f162bb8
Revises: 6d50c7e65c1d
Create Date: 2025-11-07 11:38:13.802983

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6a1c3f162bb8'
down_revision: Union[str, Sequence[str], None] = '6d50c7e65c1d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('cuisines', sa.Column('cuisine_type', sa.String(length=50), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('cuisines', 'cuisine_type')
