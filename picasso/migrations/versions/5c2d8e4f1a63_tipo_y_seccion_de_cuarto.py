"""tipo y sección de cuarto

El tipo de cada cuarto (Suite, Jacuzzi, Jacuzzi y sauna, Pent house) y si es de
motel o de hotel, como lo dicen las tarifas de Kairos.

Revision ID: 5c2d8e4f1a63
Revises: 3b7e1c9a52f4
Create Date: 2026-11-17 20:05:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "5c2d8e4f1a63"
down_revision: str | None = "3b7e1c9a52f4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("habitaciones", sa.Column("tipo", sa.String(length=40), nullable=True))
    op.add_column("habitaciones", sa.Column("seccion", sa.String(length=10), nullable=True))


def downgrade() -> None:
    op.drop_column("habitaciones", "seccion")
    op.drop_column("habitaciones", "tipo")
