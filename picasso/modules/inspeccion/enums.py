"""Enums del módulo inspeccion."""

from __future__ import annotations

from enum import StrEnum


class Resultado(StrEnum):
    """Los cuatro resultados por punto. Sin revisar nunca cuenta como Bien."""

    BIEN = "bien"
    FALLA = "falla"
    NO_APLICA = "no_aplica"
    SIN_REVISAR = "sin_revisar"


class EstadoRevision(StrEnum):
    EN_CURSO = "en_curso"
    #: Todos los puntos tienen resultado. Para ama de llaves: enviada al gerente.
    COMPLETA = "completa"


class EstadoIncidencia(StrEnum):
    REPORTADA = "reportada"
    EN_ATENCION = "en_atencion"
    CERRADA = "cerrada"
    #: El punto se corrigió en la misma revisión antes de atenderse (fue un error
    #: de captura). Se conserva el folio y su historial; no cuenta como abierta.
    ANULADA = "anulada"


ABIERTAS = (EstadoIncidencia.REPORTADA, EstadoIncidencia.EN_ATENCION)


class Prioridad(StrEnum):
    ALTA = "alta"
    MEDIA = "media"
    BAJA = "baja"


class TipoEvidencia(StrEnum):
    #: Foto tomada al revisar un punto.
    PUNTO = "punto"
    #: Foto del avance mientras se atiende.
    AVANCE = "avance"
    #: Foto de la reparación terminada, tomada por el gerente. Obligatoria para cerrar.
    REPARACION = "reparacion"
