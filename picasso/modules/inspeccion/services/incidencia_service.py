"""Folios: de la falla al cierre, sin perder el historial.

1 Detectar y registrar (lo hace RevisionService al marcar Falla).
2 Decidir si puede rentarse (RevisionService.decidir_renta).
3 Atender la corrección: el gerente coordina al responsable y anota avances.
4 Verificar y fotografiar: el gerente toma al menos una foto de la reparación.
5 Actualizar y cerrar: solo el gerente, con foto y explicación.
"""

from __future__ import annotations

from datetime import datetime

from jfastframework.errors import ForbiddenError, ValidationError

from shared.enums import Rol

from ..enums import ABIERTAS, EstadoIncidencia, Prioridad, TipoEvidencia
from ..models import (
    Actor,
    ConteoFolios,
    DecisionRead,
    EventoRead,
    Evidencia,
    EvidenciaRead,
    Incidencia,
    IncidenciaActualizar,
    IncidenciaDetalle,
    IncidenciaResumen,
)
from ..repositories import InspeccionRepository
from ..validations import exigir_puesto, exigir_sucursal, faltantes_para_cerrar
from .comun import Archivos, ahora, decision_read, evento

NOMBRE_PRIORIDAD = {Prioridad.ALTA: "alta", Prioridad.MEDIA: "media", Prioridad.BAJA: "baja"}


class IncidenciaService:
    def __init__(self, repo: InspeccionRepository, archivos: Archivos) -> None:
        self.repo = repo
        self.archivos = archivos

    async def listar(
        self,
        actor: Actor,
        *,
        sucursal_id: int | None,
        habitacion_id: int | None,
        estado: str | None,
        desde: datetime | None,
        hasta: datetime | None,
        buscar: str | None,
        prioridad: Prioridad | None = None,
    ) -> list[IncidenciaResumen]:
        if not actor.ve_todas:
            sucursal_id = actor.sucursal_id
        estados: list[str] | None
        if estado in (None, "", "todas"):
            estados = None
        elif estado == "abiertas":
            estados = [e.value for e in ABIERTAS]
        else:
            estados = [EstadoIncidencia(estado).value]
        filas = await self.repo.incidencias(
            sucursal_id=sucursal_id,
            habitacion_id=habitacion_id,
            estados=estados,
            prioridad=prioridad.value if prioridad else None,
            desde=desde,
            hasta=hasta,
            texto_busqueda=buscar,
        )
        return [IncidenciaResumen.model_validate(f, from_attributes=True) for f in filas]

    async def conteo(
        self,
        actor: Actor,
        *,
        sucursal_id: int | None,
        desde: datetime | None,
        hasta: datetime | None,
        buscar: str | None,
    ) -> list[ConteoFolios]:
        """Folios por estado y prioridad con los mismos filtros del listado."""
        if not actor.ve_todas:
            sucursal_id = actor.sucursal_id
        filas = await self.repo.conteo_incidencias(
            sucursal_id=sucursal_id, desde=desde, hasta=hasta, texto_busqueda=buscar
        )
        return [
            ConteoFolios(estado=EstadoIncidencia(e), prioridad=Prioridad(p), total=n)
            for e, p, n in filas
        ]

    async def _de(self, actor: Actor, incidencia_id: int) -> Incidencia:
        incidencia = await self.repo.incidencia(incidencia_id)
        exigir_sucursal(actor, incidencia.sucursal_id)
        return incidencia

    async def _gestionable(self, actor: Actor, incidencia_id: int) -> Incidencia:
        """El gerente de la sucursal actualiza; el propietario solo consulta."""
        exigir_puesto(actor, Rol.GERENTE)
        incidencia = await self._de(actor, incidencia_id)
        if incidencia.estado not in ABIERTAS:
            raise ValidationError("El folio ya no está abierto.")
        return incidencia

    async def detalle(self, actor: Actor, incidencia_id: int) -> IncidenciaDetalle:
        incidencia = await self._de(actor, incidencia_id)
        evidencias = await self.repo.evidencias_de_incidencia(incidencia.id)
        decisiones = await self.repo.decisiones(incidencia.habitacion_id)
        vigente = decisiones[0] if decisiones else None
        desde_reporte = [d for d in decisiones if d.decidida_en >= incidencia.reportada_en]
        falta = (
            faltantes_para_cerrar(
                None, self._fotos_reparacion(evidencias), actor.rol, revisar_correccion=False
            )
            if incidencia.estado in ABIERTAS
            else ["El folio ya está cerrado."]
        )
        base = IncidenciaResumen.model_validate(incidencia, from_attributes=True)
        return IncidenciaDetalle(
            **base.model_dump(),
            descripcion=incidencia.descripcion,
            correccion=incidencia.correccion,
            cerrada_por_nombre=incidencia.cerrada_por_nombre,
            origen_revision_id=incidencia.origen_revision_id,
            evidencias=await self.archivos.evidencias(evidencias),
            historial=[
                EventoRead.model_validate(e, from_attributes=True)
                for e in await self.repo.eventos(incidencia.id)
            ],
            renta_vigente=decision_read(vigente),
            decisiones=[
                DecisionRead.model_validate(d, from_attributes=True) for d in desde_reporte
            ],
            puede_cerrar=not falta,
            falta_para_cerrar=falta,
        )

    @staticmethod
    def _fotos_reparacion(evidencias: list[Evidencia]) -> int:
        return sum(
            1
            for e in evidencias
            if e.tipo == TipoEvidencia.REPARACION and e.subida_por_rol == Rol.GERENTE
        )

    async def actualizar(
        self, actor: Actor, incidencia_id: int, payload: IncidenciaActualizar
    ) -> IncidenciaDetalle:
        incidencia = await self._gestionable(actor, incidencia_id)
        if payload.prioridad is not None and payload.prioridad != incidencia.prioridad:
            incidencia.prioridad = payload.prioridad.value
            self.repo.session.add(
                evento(
                    incidencia.id,
                    actor,
                    "prioridad",
                    f"Definió prioridad {NOMBRE_PRIORIDAD[payload.prioridad]}.",
                )
            )
        responsable = (payload.responsable_atencion or "").strip() or None
        if (
            "responsable_atencion" in payload.model_fields_set
            and responsable != incidencia.responsable_atencion
        ):
            incidencia.responsable_atencion = responsable
            if responsable:
                self.repo.session.add(
                    evento(
                        incidencia.id, actor, "responsable", f"Asignó la atención a {responsable}."
                    )
                )
        if payload.en_atencion and incidencia.estado == EstadoIncidencia.REPORTADA:
            incidencia.estado = EstadoIncidencia.EN_ATENCION.value
            quien = (
                f" con {incidencia.responsable_atencion}" if incidencia.responsable_atencion else ""
            )
            self.repo.session.add(
                evento(incidencia.id, actor, "atencion", f"Puso el folio en atención{quien}.")
            )
        await self.repo.session.flush()
        return await self.detalle(actor, incidencia.id)

    async def avance(self, actor: Actor, incidencia_id: int, nota: str) -> IncidenciaDetalle:
        incidencia = await self._gestionable(actor, incidencia_id)
        if incidencia.estado == EstadoIncidencia.REPORTADA:
            incidencia.estado = EstadoIncidencia.EN_ATENCION.value
        self.repo.session.add(evento(incidencia.id, actor, "avance", nota.strip()))
        await self.repo.session.flush()
        return await self.detalle(actor, incidencia.id)

    async def foto(
        self,
        actor: Actor,
        incidencia_id: int,
        tipo: TipoEvidencia,
        datos: bytes,
        contenido: str | None,
        nota: str | None,
    ) -> EvidenciaRead:
        if tipo is TipoEvidencia.PUNTO:
            raise ValidationError("Las fotos del punto se toman desde el checklist.")
        incidencia = await self._gestionable(actor, incidencia_id)
        llave = await self.archivos.guardar(datos, contenido)
        fila = await self.repo.agregar(
            Evidencia(
                tipo=tipo.value,
                archivo=llave,
                incidencia_id=incidencia.id,
                subida_por_id=actor.user_id,
                subida_por_nombre=actor.nombre,
                subida_por_rol=actor.rol.value,
                nota=(nota or "").strip() or None,
                creada_en=ahora(),
            )
        )
        texto = (
            "Verificó y tomó la foto de la reparación."
            if tipo is TipoEvidencia.REPARACION
            else "Agregó foto de avance."
        )
        self.repo.session.add(evento(incidencia.id, actor, "evidencia", texto))
        return await self.archivos.evidencia(fila)

    async def cerrar(self, actor: Actor, incidencia_id: int, correccion: str) -> IncidenciaDetalle:
        """ "Sin foto tomada por el gerente y sin explicación de la corrección, no
        se permite cerrar." """
        if actor.rol is not Rol.GERENTE:
            raise ForbiddenError("Solo el gerente de la sucursal cierra el folio.")
        incidencia = await self._gestionable(actor, incidencia_id)
        evidencias = await self.repo.evidencias_de_incidencia(incidencia.id)
        falta = faltantes_para_cerrar(correccion, self._fotos_reparacion(evidencias), actor.rol)
        if falta:
            raise ValidationError(" ".join(falta))
        incidencia.estado = EstadoIncidencia.CERRADA.value
        incidencia.correccion = correccion.strip()
        incidencia.cerrada_por_nombre = actor.nombre
        incidencia.cerrada_en = ahora()
        self.repo.session.add(
            evento(incidencia.id, actor, "cierre", f"Actualizó y cerró: {incidencia.correccion}")
        )
        await self.repo.session.flush()
        return await self.detalle(actor, incidencia.id)
