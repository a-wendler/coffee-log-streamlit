"""mietzahlungen in prod 2

Revision ID: a56eccd4707a
Revises: 19bc507696d5
Create Date: 2024-11-01 13:52:54.631704

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a56eccd4707a'
down_revision: Union[str, None] = '19bc507696d5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
