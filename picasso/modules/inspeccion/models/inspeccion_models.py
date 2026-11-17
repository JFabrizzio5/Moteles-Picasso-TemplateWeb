"""Contratos del módulo inspeccion."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from shared.enums import Rol

from ..enums import EstadoIncidencia, EstadoRevision, Prioridad, Resultado, TipoEvidencia


@dataclass(frozen=True, slots=True)
class Actor:
    """Quién hace la petición, ya resuelto: puesto, nombre y sucursal."""

    user_id: str
    nombre: str
    rol: Rol
    #: None = ve todas las sucursales.
    sucursal_id: int | None

    @property
    def ve_todas(self) -> bool:
        return self.rol in (Rol.ADMIN, Rol.PROPIETARIO)

    def puede_ver(self, sucursal_id: int) -> bool:
        return self.ve_todas or self.sucursal_id == sucursal_id


# -- revisiones -------------------------------------------------------------


class RevisionCrear(BaseModel):
    habitacion_id: int


class PuntoGuardar(BaseModel):
    resultado: Resultado
    observacion: str | None = Field(default=None, max_length=2000)
    motivo_no_aplica: str | None = Field(default=None, max_length=300)


class EvidenciaRead(BaseModel):
    id: int
    tipo: TipoEvidencia
    url: str
    codigo_punto: str | None
    subida_por_nombre: str
    subida_por_rol: Rol
    nota: str | None
    creada_en: datetime


class ResultadoRead(BaseModel):
    codigo: str
    orden: int
    seccion: str
    titulo: str
    texto: str
    resultado: Resultado
    observacion: str | None
    motivo_no_aplica: str | None
    automatico: bool
    en_bloque: bool = False
    incidencia_id: int | None
    folio: str | None = None
    incidencia_estado: EstadoIncidencia | None = None
    revisado_en: datetime | None
    evidencias: list[EvidenciaRead] = Field(default_factory=list)


class DecisionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    habitacion_id: int
    habitacion_numero: str
    sucursal_clave: str
    puede_rentarse: bool
    motivo: str
    gerente_nombre: str
    incidencia_id: int | None
    decidida_en: datetime


class DecisionCrear(BaseModel):
    puede_rentarse: bool
    motivo: str = Field(min_length=3, max_length=300)
    incidencia_id: int | None = None


class RevisionResumen(BaseModel):
    id: int
    sucursal_id: int
    sucursal_clave: str
    sucursal_nombre: str
    habitacion_id: int
    habitacion_numero: str
    rol: Rol
    responsable_nombre: str
    estado: EstadoRevision
    iniciada_en: datetime
    completada_en: datetime | None
    total: int = 0
    revisados: int = 0
    bien: int = 0
    fallas: int = 0
    no_aplica: int = 0


class UltimoChequeo(BaseModel):
    """La revisión terminada más reciente de un cuarto: cuándo, quién y de qué puesto."""

    revision_id: int
    fecha: datetime
    rol: Rol
    responsable_nombre: str
    fallas: int = 0


class RevisionDetalle(RevisionResumen):
    puntos: list[ResultadoRead]
    renta: DecisionRead | None = None
    #: El chequeo terminado anterior de este cuarto (sin contar esta revisión).
    ultimo_chequeo: UltimoChequeo | None = None


# -- incidencias ------------------------------------------------------------


class EventoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    fecha: datetime
    actor_nombre: str
    actor_rol: Rol
    accion: str
    detalle: str


class IncidenciaResumen(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    folio: str
    sucursal_id: int
    sucursal_clave: str
    sucursal_nombre: str
    habitacion_id: int
    habitacion_numero: str
    codigo_punto: str
    categoria: str
    titulo: str
    prioridad: Prioridad
    estado: EstadoIncidencia
    origen_rol: Rol
    reporto_nombre: str
    reportada_en: datetime
    responsable_atencion: str | None
    cerrada_en: datetime | None


class ConteoFolios(BaseModel):
    """Folios de un estado con una prioridad; el listado arma con esto su tabla."""

    estado: EstadoIncidencia
    prioridad: Prioridad
    total: int


class IncidenciaDetalle(IncidenciaResumen):
    descripcion: str
    correccion: str | None
    cerrada_por_nombre: str | None
    origen_revision_id: int
    evidencias: list[EvidenciaRead]
    historial: list[EventoRead]
    renta_vigente: DecisionRead | None
    decisiones: list[DecisionRead]
    puede_cerrar: bool = False
    falta_para_cerrar: list[str] = Field(default_factory=list)


class IncidenciaActualizar(BaseModel):
    prioridad: Prioridad | None = None
    responsable_atencion: str | None = Field(default=None, max_length=120)
    en_atencion: bool | None = None


class AvanceCrear(BaseModel):
    nota: str = Field(min_length=2, max_length=1000)


class CierreCrear(BaseModel):
    correccion: str = Field(min_length=5, max_length=2000)


# -- tablero de personal -----------------------------------------------------


class UltimaRevision(BaseModel):
    id: int
    estado: EstadoRevision
    responsable_nombre: str
    iniciada_en: datetime
    completada_en: datetime | None
    revisados: int
    total: int


class HabitacionEstado(BaseModel):
    habitacion_id: int
    sucursal_id: int
    numero: str
    amenidades: list[str]
    gerente: UltimaRevision | None
    ama_llaves: UltimaRevision | None
    #: Para quien pregunta: la revisión de su puesto que dejó a medias.
    mi_revision_en_curso: int | None
    #: El gerente no la ha revisado dentro de su frecuencia.
    gerente_pendiente: bool
    #: El ama de llaves la envió y el gerente aún no la revisa después.
    ama_enviada_sin_gerente: bool
    incidencias_abiertas: int
    renta: DecisionRead | None
    ultimo_chequeo: UltimoChequeo | None = None
    #: Lo que tiene el cuarto según el catálogo de equipo (Netflix, minibar…).
    equipo: list[str] = Field(default_factory=list)


# -- propietarios -------------------------------------------------------------


class Periodo(BaseModel):
    desde: date
    hasta: date


class FilaSucursal(BaseModel):
    sucursal_id: int
    clave: str
    nombre: str
    foto: str | None
    habitaciones: int
    gerente_completas: int
    gerente_exigibles: int
    ama_completas: int
    ama_exigibles: int
    abiertas: int
    no_rentar: int
    #: Hora del chequeo terminado más reciente en cualquier cuarto de la sucursal.
    ultimo_chequeo: datetime | None = None


class Panel(BaseModel):
    corte: datetime
    periodo: Periodo
    completas: int
    exigibles: int
    abiertas: int
    bloqueados: int
    sucursales: list[FilaSucursal]


class Reincidencia(BaseModel):
    sucursal_nombre: str
    habitacion_id: int
    habitacion_numero: str
    categoria: str
    veces: int
    folios: list[str]


class IndicadorSucursal(BaseModel):
    sucursal_id: int
    nombre: str
    cumplimiento_gerente: float | None
    cumplimiento_ama: float | None
    bien: int
    fallas: int
    no_aplica: int
    sin_revisar: int
    conformidad: float | None
    cerradas: int
    horas_solucion_promedio: float | None
    abiertas: int
    horas_abiertas_max: float | None


class Indicadores(BaseModel):
    periodo: Periodo
    total: IndicadorSucursal
    sucursales: list[IndicadorSucursal]
    reincidencias: list[Reincidencia]
    fallas_frecuentes: list[dict[str, str | int]]


class HabitacionExpediente(BaseModel):
    habitacion_id: int
    sucursal_id: int
    sucursal_nombre: str
    numero: str
    amenidades: list[str]
    revisiones: list[RevisionResumen]
    pendientes: list[ResultadoRead]
    incidencias: list[IncidenciaResumen]
    renta: DecisionRead | None
    decisiones: list[DecisionRead]
