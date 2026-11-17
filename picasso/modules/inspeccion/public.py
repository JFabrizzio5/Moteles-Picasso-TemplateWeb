"""Fachada pública del módulo inspeccion.

La usa finanzas para ligar un gasto con un folio: solo lee y regresa una copia,
nunca la entidad.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from jfastframework.errors import NotFoundError

from .repositories import InspeccionRepository


@dataclass(frozen=True, slots=True)
class IncidenciaDTO:
    id: int
    folio: str
    titulo: str
    sucursal_id: int
    habitacion_numero: str
    estado: str
    prioridad: str


async def incidencia(session: AsyncSession, incidencia_id: int) -> IncidenciaDTO | None:
    try:
        fila = await InspeccionRepository(session).incidencia(incidencia_id)
    except NotFoundError:
        return None
    return IncidenciaDTO(
        id=fila.id,
        folio=fila.folio,
        titulo=fila.titulo,
        sucursal_id=fila.sucursal_id,
        habitacion_numero=fila.habitacion_numero,
        estado=fila.estado,
        prioridad=fila.prioridad,
    )
