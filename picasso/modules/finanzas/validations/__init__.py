"""Reglas del módulo finanzas."""

from __future__ import annotations

from .finanzas_validation import (
    PUESTOS_FINANZAS,
    articulo,
    exigir_desglose,
    exigir_editable,
    exigir_finanzas,
    exigir_gasto_de,
    exigir_puede_eliminar,
    exigir_quien_ve_todas,
    importe_partida,
    liga_de_incidencia,
    no_en_el_futuro,
    normalizar_rfc,
    rango,
    sucursal_para,
    sucursal_visible,
)

__all__ = [
    "PUESTOS_FINANZAS",
    "articulo",
    "exigir_desglose",
    "exigir_editable",
    "exigir_finanzas",
    "exigir_gasto_de",
    "exigir_puede_eliminar",
    "exigir_quien_ve_todas",
    "importe_partida",
    "liga_de_incidencia",
    "no_en_el_futuro",
    "normalizar_rfc",
    "rango",
    "sucursal_para",
    "sucursal_visible",
]
