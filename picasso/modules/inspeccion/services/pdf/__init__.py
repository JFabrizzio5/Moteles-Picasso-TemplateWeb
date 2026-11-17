"""Reportes PDF del documento de la dirección (sección 07): por inspección,
por incidencia, por habitación y por sucursal y grupo."""

from __future__ import annotations

from .base import FotoPdf
from .grupo_pdf import construir_grupo
from .habitacion_pdf import construir_habitacion
from .incidencia_pdf import construir_incidencia
from .revision_pdf import construir_revision

__all__ = [
    "FotoPdf",
    "construir_grupo",
    "construir_habitacion",
    "construir_incidencia",
    "construir_revision",
]
