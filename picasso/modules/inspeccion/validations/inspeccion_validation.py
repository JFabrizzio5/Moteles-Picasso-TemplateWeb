"""Reglas puras del módulo inspeccion: sin base, sin HTTP, sin reloj.

Cada regla sale del documento de la dirección; la cita va junto a la función.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from jfastframework.errors import ForbiddenError, ValidationError

from shared.enums import Rol

from ..enums import Resultado
from ..models.catalogo_models import CHECKLISTS, NOMBRE_AMENIDAD, Punto
from ..models.inspeccion_models import Actor


@dataclass(frozen=True, slots=True)
class PuntoInicial:
    punto: Punto
    resultado: Resultado
    motivo: str | None
    automatico: bool


def puntos_iniciales(rol: Rol, amenidades: set[str]) -> list[PuntoInicial]:
    """El checklist del puesto, con lo que no aplica a esta habitación ya marcado.

    "No aplica: no corresponde. Se registra el motivo." Si la habitación no
    tiene jacuzzi, el punto del jacuzzi no corresponde y el motivo lo escribe
    el sistema.
    """
    salida = []
    for punto in CHECKLISTS[rol.value]:
        if punto.requiere and not amenidades.intersection(punto.requiere):
            faltan = " ni ".join(NOMBRE_AMENIDAD[a] for a in punto.requiere)
            salida.append(
                PuntoInicial(punto, Resultado.NO_APLICA, f"La habitación no tiene {faltan}.", True)
            )
        else:
            salida.append(PuntoInicial(punto, Resultado.SIN_REVISAR, None, False))
    return salida


def normalizar_punto(
    resultado: Resultado, observacion: str | None, motivo: str | None
) -> tuple[str | None, str | None]:
    """Devuelve (observación, motivo) limpios o rechaza lo que falta.

    - Falla: requiere observación ("Requiere corrección y seguimiento").
    - No aplica: requiere el motivo ("Se registra el motivo").
    """
    observacion = (observacion or "").strip() or None
    motivo = (motivo or "").strip() or None
    if resultado is Resultado.FALLA and observacion is None:
        raise ValidationError("Escribe qué falla: la observación inicia el folio.")
    if resultado is Resultado.NO_APLICA and motivo is None:
        raise ValidationError("No aplica pide el motivo.")
    if resultado is not Resultado.NO_APLICA:
        motivo = None
    return observacion, motivo


def validar_completar(resultados: Iterable[str]) -> None:
    """ "Para enviar, resolver todos los puntos Sin revisar." """
    pendientes = sum(1 for r in resultados if r == Resultado.SIN_REVISAR)
    if pendientes:
        plural = "punto" if pendientes == 1 else "puntos"
        raise ValidationError(f"Faltan {pendientes} {plural} sin revisar.")


def faltantes_para_cerrar(
    correccion: str | None,
    fotos_reparacion_gerente: int,
    actor_rol: Rol,
    *,
    revisar_correccion: bool = True,
) -> list[str]:
    """ "Sin foto tomada por el gerente y sin explicación de la corrección, no se
    permite cerrar." Devuelve lo que falta; vacío = se puede cerrar."""
    falta = []
    if actor_rol is not Rol.GERENTE:
        falta.append("Solo el gerente de la sucursal cierra el folio.")
    if fotos_reparacion_gerente < 1:
        falta.append("Toma al menos una foto de la reparación terminada.")
    if revisar_correccion and not (correccion or "").strip():
        falta.append("Escribe qué se corrigió.")
    return falta


def exigir_puesto(actor: Actor, *roles: Rol) -> None:
    if actor.rol not in roles:
        nombres = " o ".join(r.value.replace("_", " de ") for r in roles)
        raise ForbiddenError(f"Esta acción es del puesto de {nombres}.")


def exigir_sucursal(actor: Actor, sucursal_id: int) -> None:
    if not actor.puede_ver(sucursal_id):
        raise ForbiddenError("Esta habitación es de otra sucursal.")


def formato_folio(clave: str, numero: int) -> str:
    return f"PIC-{clave.upper()}-{numero:06d}"


def dias_del_periodo(desde: date, hasta: date) -> int:
    return (hasta - desde).days + 1


def exigibles_gerente(habitaciones: int, desde: date, hasta: date, frecuencia_dias: int) -> int:
    """Revisiones de gerente que el periodo exige: una por habitación por ventana.

    La ventana es la frecuencia de la sucursal (1 = diaria, 2 = cada dos días).
    """
    ventanas = math.ceil(dias_del_periodo(desde, hasta) / max(frecuencia_dias, 1))
    return habitaciones * ventanas


def completas_gerente(
    fechas_por_habitacion: dict[int, list[date]], desde: date, frecuencia_dias: int
) -> int:
    """Ventanas cubiertas: dos revisiones del mismo cuarto el mismo día cuentan una."""
    total = 0
    for fechas in fechas_por_habitacion.values():
        ventanas = {(f - desde).days // max(frecuencia_dias, 1) for f in fechas if f >= desde}
        total += len(ventanas)
    return total


def exigibles_ama(regla: str, habitaciones: int, desde: date, hasta: date, iniciadas: int) -> int:
    """Por limpieza: cada revisión abierta es una limpieza que debe enviarse.
    Diaria: una por habitación por día."""
    if regla == "diaria":
        return habitaciones * dias_del_periodo(desde, hasta)
    return iniciadas


def conformidad(bien: int, falla: int) -> float | None:
    """Bien / (Bien + Falla). No aplica y Sin revisar van aparte."""
    base = bien + falla
    return None if base == 0 else round(bien / base, 4)


def proporcion(parte: int, total: int) -> float | None:
    return None if total == 0 else round(min(parte, total) / total, 4)


def horas(desde: datetime, hasta: datetime) -> float:
    return round((hasta - desde) / timedelta(hours=1), 1)
