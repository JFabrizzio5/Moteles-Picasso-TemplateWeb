"""Arma los cuatro reportes PDF con los mismos datos y permisos que la app.

Los datos salen de los servicios de siempre (así un PDF nunca muestra algo que
la pantalla no dejaría ver); las fotos se leen del disco privado. El armado del
PDF es CPU pura y corre en un hilo para no detener las demás peticiones.
"""

from __future__ import annotations

import asyncio
import re
import unicodedata
from dataclasses import dataclass

from shared.enums import Rol

from ..models import Actor, Evidencia, Periodo
from ..repositories import InspeccionRepository
from ..validations import exigir_puesto
from .comun import Archivos, ahora, fecha_local, hoy
from .incidencia_service import IncidenciaService
from .pdf import (
    FotoPdf,
    construir_grupo,
    construir_habitacion,
    construir_incidencia,
    construir_revision,
)
from .pdf.base import ROLES, fecha_hora
from .reporte_service import ReporteService
from .revision_service import RevisionService

TIPOS = {"punto": "Evidencia", "avance": "Avance", "reparacion": "Reparación"}


@dataclass(frozen=True, slots=True)
class Pdf:
    datos: bytes
    nombre: str

    @property
    def nombre_ascii(self) -> str:
        """Para el `filename=` clásico; el real va en `filename*` (RFC 5987)."""
        sin_acentos = unicodedata.normalize("NFKD", self.nombre).encode("ascii", "ignore").decode()
        return re.sub(r"[^A-Za-z0-9._-]+", "-", sin_acentos)


def _nombre(*partes: str) -> str:
    return "-".join(re.sub(r"\s+", "-", p.strip()) for p in partes if p) + ".pdf"


class PdfService:
    def __init__(self, repo: InspeccionRepository, archivos: Archivos) -> None:
        self.repo = repo
        self.archivos = archivos

    async def _fotos(self, filas: list[Evidencia]) -> list[tuple[Evidencia, FotoPdf]]:
        salida = []
        for fila in filas:
            datos = await self.archivos.leer(fila.archivo)
            titulo = f"{TIPOS.get(fila.tipo, fila.tipo)}" + (
                f" · {fila.codigo_punto}" if fila.codigo_punto else ""
            )
            pie = (
                f"{fila.subida_por_nombre} ({ROLES.get(fila.subida_por_rol, fila.subida_por_rol)})"
                f" · {fecha_hora(fila.creada_en)}"
            )
            salida.append((fila, FotoPdf(titulo, pie, datos)))
        return salida

    async def revision(self, actor: Actor, revision_id: int) -> Pdf:
        detalle = await RevisionService(self.repo, self.archivos).detalle(actor, revision_id)
        fotos: dict[str, list[FotoPdf]] = {}
        for fila, foto in await self._fotos(await self.repo.evidencias_de_revision(revision_id)):
            fotos.setdefault(fila.codigo_punto or "", []).append(foto)
        datos = await asyncio.to_thread(construir_revision, detalle, fotos, ahora())
        nombre = _nombre(
            "Revision",
            detalle.sucursal_clave,
            detalle.habitacion_numero,
            fecha_local(detalle.iniciada_en).isoformat(),
        )
        return Pdf(datos, nombre)

    async def incidencia(self, actor: Actor, incidencia_id: int) -> Pdf:
        detalle = await IncidenciaService(self.repo, self.archivos).detalle(actor, incidencia_id)
        pares = await self._fotos(await self.repo.evidencias_de_incidencia(incidencia_id))
        fotos = [(fila.tipo, foto) for fila, foto in pares]
        datos = await asyncio.to_thread(construir_incidencia, detalle, fotos, ahora())
        return Pdf(datos, _nombre("Folio", detalle.folio))

    async def habitacion(self, actor: Actor, habitacion_id: int) -> Pdf:
        exigir_puesto(actor, Rol.GERENTE, Rol.PROPIETARIO, Rol.ADMIN)
        expediente = await ReporteService(self.repo).expediente(actor, habitacion_id)
        datos = await asyncio.to_thread(construir_habitacion, expediente, ahora())
        sucursal = expediente.sucursal_nombre.replace("Picasso ", "")
        return Pdf(datos, _nombre("Habitacion", sucursal, expediente.numero, hoy().isoformat()))

    async def grupo(self, actor: Actor, periodo: Periodo) -> Pdf:
        exigir_puesto(actor, Rol.GERENTE, Rol.PROPIETARIO, Rol.ADMIN)
        reportes = ReporteService(self.repo)
        panel = await reportes.panel(actor, periodo)
        indicadores = await reportes.indicadores(actor, periodo)
        datos = await asyncio.to_thread(construir_grupo, panel, indicadores, ahora())
        alcance = (
            "Grupo"
            if actor.ve_todas
            else (panel.sucursales[0].nombre if panel.sucursales else "Sucursal")
        )
        return Pdf(
            datos,
            _nombre(
                "Reporte",
                alcance.replace("Picasso ", ""),
                periodo.desde.isoformat(),
                "a",
                periodo.hasta.isoformat(),
            ),
        )
