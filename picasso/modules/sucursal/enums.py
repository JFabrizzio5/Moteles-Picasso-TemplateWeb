"""Enums del módulo sucursal."""

from __future__ import annotations

from enum import StrEnum


class AmaExigible(StrEnum):
    """Cómo se cuentan las revisiones exigibles de ama de llaves.

    Regla sin confirmar con la dirección, por eso es un interruptor por
    sucursal y no código fijo.

    POR_LIMPIEZA: cada revisión abierta es una limpieza, y toda limpieza debe
    terminar en una revisión enviada al gerente.
    DIARIA: una revisión por habitación por día.
    """

    POR_LIMPIEZA = "por_limpieza"
    DIARIA = "diaria"
