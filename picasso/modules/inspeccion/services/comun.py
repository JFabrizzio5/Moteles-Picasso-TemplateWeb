"""Piezas que comparten los servicios del módulo: fotos, fechas y conversiones."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, time, timedelta
from typing import Any, Protocol
from zoneinfo import ZoneInfo

from jfastframework.errors import ValidationError

from shared.enums import Rol

from ..enums import Resultado
from ..models import (
    Actor,
    DecisionRead,
    DecisionRenta,
    EventoIncidencia,
    Evidencia,
    EvidenciaRead,
    Incidencia,
    Periodo,
    ResultadoPunto,
    ResultadoRead,
    Revision,
    RevisionResumen,
    UltimoChequeo,
)

#: La zona del negocio: lo que "hoy" significa para un corte o un periodo.
ZONA = ZoneInfo("America/Mexico_City")

TIPOS_IMAGEN = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
MAX_FOTO = 8 * 1024 * 1024
#: Las ligas a las fotos caducan; el front las vuelve a pedir con el expediente.
VIGENCIA_LIGA = 2 * 60 * 60


def ahora() -> datetime:
    return datetime.now(UTC)


def hoy() -> date:
    return ahora().astimezone(ZONA).date()


def fecha_local(momento: datetime) -> date:
    return momento.astimezone(ZONA).date()


def rango_utc(desde: date, hasta: date) -> tuple[datetime, datetime]:
    """Del inicio de `desde` al final de `hasta`, en hora de CDMX."""
    inicio = datetime.combine(desde, time.min, ZONA)
    fin = datetime.combine(hasta + timedelta(days=1), time.min, ZONA)
    return inicio, fin


def periodo(desde: date | None, hasta: date | None) -> Periodo:
    fin = hasta or hoy()
    inicio = desde or fin - timedelta(days=6)
    if inicio > fin:
        raise ValidationError("La fecha inicial va antes de la final.")
    if (fin - inicio).days > 366:
        raise ValidationError("El periodo máximo es de un año.")
    return Periodo(desde=inicio, hasta=fin)


class Disco(Protocol):
    async def put(self, key: str, data: bytes, **kwargs: Any) -> Any: ...
    async def get(self, key: str) -> bytes: ...
    async def temporary_url(self, key: str, *, expires_in: int = 300) -> str: ...


class Archivos:
    """Las fotos van al disco privado: nadie las ve sin una liga firmada."""

    def __init__(self, disco: Disco) -> None:
        self.disco = disco

    async def guardar(self, datos: bytes, tipo: str | None) -> str:
        extension = TIPOS_IMAGEN.get((tipo or "").lower())
        if extension is None:
            raise ValidationError("La evidencia debe ser una foto (JPG, PNG o WebP).")
        if not datos:
            raise ValidationError("La foto llegó vacía.")
        if len(datos) > MAX_FOTO:
            raise ValidationError("La foto pesa más de 8 MB.")
        momento = ahora()
        llave = f"evidencias/{momento:%Y/%m}/{uuid.uuid4().hex}.{extension}"
        await self.disco.put(llave, datos, content_type=tipo)
        return llave

    async def leer(self, llave: str) -> bytes | None:
        """Los bytes de una foto, o None si ya no está en el disco (el PDF lo dice)."""
        try:
            return await self.disco.get(llave)
        except Exception:
            return None

    async def liga(self, llave: str) -> str:
        return await self.disco.temporary_url(llave, expires_in=VIGENCIA_LIGA)

    async def evidencias(self, filas: list[Evidencia]) -> list[EvidenciaRead]:
        return [await self.evidencia(fila) for fila in filas]

    async def evidencia(self, fila: Evidencia) -> EvidenciaRead:
        return EvidenciaRead(
            id=fila.id,
            tipo=fila.tipo,  # type: ignore[arg-type]
            url=await self.liga(fila.archivo),
            codigo_punto=fila.codigo_punto,
            subida_por_nombre=fila.subida_por_nombre,
            subida_por_rol=Rol(fila.subida_por_rol),
            nota=fila.nota,
            creada_en=fila.creada_en,
        )


def evento(incidencia_id: int, actor: Actor, accion: str, detalle: str) -> EventoIncidencia:
    return EventoIncidencia(
        incidencia_id=incidencia_id,
        fecha=ahora(),
        actor_id=actor.user_id,
        actor_nombre=actor.nombre,
        actor_rol=actor.rol.value,
        accion=accion,
        detalle=detalle,
    )


def decision_read(fila: DecisionRenta | None) -> DecisionRead | None:
    return None if fila is None else DecisionRead.model_validate(fila, from_attributes=True)


def resumen_revision(fila: Revision, conteo: dict[str, int] | None = None) -> RevisionResumen:
    conteo = conteo or {}
    total = sum(conteo.values())
    return RevisionResumen(
        id=fila.id,
        sucursal_id=fila.sucursal_id,
        sucursal_clave=fila.sucursal_clave,
        sucursal_nombre=fila.sucursal_nombre,
        habitacion_id=fila.habitacion_id,
        habitacion_numero=fila.habitacion_numero,
        rol=Rol(fila.rol),
        responsable_nombre=fila.responsable_nombre,
        estado=fila.estado,  # type: ignore[arg-type]
        iniciada_en=fila.iniciada_en,
        completada_en=fila.completada_en,
        total=total,
        revisados=total - conteo.get(Resultado.SIN_REVISAR, 0),
        bien=conteo.get(Resultado.BIEN, 0),
        fallas=conteo.get(Resultado.FALLA, 0),
        no_aplica=conteo.get(Resultado.NO_APLICA, 0),
    )


def resultado_read(
    fila: ResultadoPunto,
    folios: dict[int, Incidencia],
    evidencias: list[EvidenciaRead] | None = None,
) -> ResultadoRead:
    incidencia = folios.get(fila.incidencia_id) if fila.incidencia_id else None
    return ResultadoRead(
        codigo=fila.codigo,
        orden=fila.orden,
        seccion=fila.seccion,
        titulo=fila.titulo,
        texto=fila.texto,
        resultado=fila.resultado,  # type: ignore[arg-type]
        observacion=fila.observacion,
        motivo_no_aplica=fila.motivo_no_aplica,
        automatico=fila.automatico,
        en_bloque=fila.en_bloque,
        incidencia_id=fila.incidencia_id,
        folio=incidencia.folio if incidencia else None,
        incidencia_estado=incidencia.estado if incidencia else None,  # type: ignore[arg-type]
        revisado_en=fila.revisado_en,
        evidencias=evidencias or [],
    )


def ultimo_chequeo(fila: Revision | None, fallas: int = 0) -> UltimoChequeo | None:
    if fila is None or fila.completada_en is None:
        return None
    return UltimoChequeo(
        revision_id=fila.id,
        fecha=fila.completada_en,
        rol=Rol(fila.rol),
        responsable_nombre=fila.responsable_nombre,
        fallas=fallas,
    )


def amenidades(habitacion: Any) -> list[str]:
    return [
        nombre
        for nombre in ("jacuzzi", "alberca", "sauna", "terraza")
        if getattr(habitacion, f"tiene_{nombre}", False)
    ]
