"""papelera de gastos

Un gasto eliminado no se borra: queda con quién, cuándo y por qué, y deja de
contar en listas, reportes, auditoría y exportes hasta que lo restauren.

Revision ID: 3b7e1c9a52f4
Revises: 8166e118c343
Create Date: 2026-11-17 19:10:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "3b7e1c9a52f4"
down_revision: str | None = "8166e118c343"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("gastos", sa.Column("eliminado_en", sa.DateTime(timezone=True), nullable=True))
    op.add_column("gastos", sa.Column("eliminado_por_id", sa.String(length=64), nullable=True))
    op.add_column("gastos", sa.Column("eliminado_por_nombre", sa.String(length=120), nullable=True))
    op.add_column("gastos", sa.Column("motivo_eliminacion", sa.String(length=300), nullable=True))
    op.create_index(op.f("ix_gastos_eliminado_en"), "gastos", ["eliminado_en"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_gastos_eliminado_en"), table_name="gastos")
    op.drop_column("gastos", "motivo_eliminacion")
    op.drop_column("gastos", "eliminado_por_nombre")
    op.drop_column("gastos", "eliminado_por_id")
    op.drop_column("gastos", "eliminado_en")
