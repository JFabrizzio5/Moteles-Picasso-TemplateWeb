"""Entidades del módulo inspeccion.

Las revisiones y los folios guardan una copia de la sucursal y la habitación
(clave, nombre, número) en vez de unirse a las tablas del módulo sucursal: el
expediente debe decir lo que decía el día que se levantó, y los módulos no se
unen por SQL.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, false
from sqlalchemy.orm import Mapped, mapped_column

from jfastframework.db import Base, TenantMixin, TimestampMixin


class Revision(Base, TimestampMixin, TenantMixin):
    __tablename__ = "revisiones"

    id: Mapped[int] = mapped_column(primary_key=True)
    sucursal_id: Mapped[int] = mapped_column(index=True)
    sucursal_clave: Mapped[str] = mapped_column(String(3))
    sucursal_nombre: Mapped[str] = mapped_column(String(80))
    habitacion_id: Mapped[int] = mapped_column(index=True)
    habitacion_numero: Mapped[str] = mapped_column(String(10))
    rol: Mapped[str] = mapped_column(String(20), index=True)
    responsable_id: Mapped[str] = mapped_column(String(64))
    responsable_nombre: Mapped[str] = mapped_column(String(120))
    estado: Mapped[str] = mapped_column(String(20), default="en_curso", index=True)
    iniciada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    completada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)


class ResultadoPunto(Base, TimestampMixin, TenantMixin):
    __tablename__ = "resultados_punto"
    __table_args__ = (
        UniqueConstraint("revision_id", "codigo", name="uq_resultados_revision_codigo"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    revision_id: Mapped[int] = mapped_column(
        ForeignKey("revisiones.id", ondelete="CASCADE"), index=True
    )
    codigo: Mapped[str] = mapped_column(String(4))
    orden: Mapped[int] = mapped_column()
    seccion: Mapped[str] = mapped_column(String(60))
    titulo: Mapped[str] = mapped_column(String(80))
    #: Copia del criterio el día de la revisión.
    texto: Mapped[str] = mapped_column(Text)
    resultado: Mapped[str] = mapped_column(String(12), default="sin_revisar")
    observacion: Mapped[str | None] = mapped_column(Text, default=None)
    motivo_no_aplica: Mapped[str | None] = mapped_column(String(300), default=None)
    #: True cuando el sistema lo marcó No aplica porque la habitación no tiene la amenidad.
    automatico: Mapped[bool] = mapped_column(default=False)
    #: Marcado Bien con "Lo demás está bien", no punto por punto. Se distingue
    #: en pantallas y PDF porque el documento pide revisar cada punto.
    en_bloque: Mapped[bool] = mapped_column(default=False, server_default=false())
    incidencia_id: Mapped[int | None] = mapped_column(
        ForeignKey("incidencias.id"), default=None, index=True
    )
    revisado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)


class Incidencia(Base, TimestampMixin, TenantMixin):
    __tablename__ = "incidencias"

    id: Mapped[int] = mapped_column(primary_key=True)
    folio: Mapped[str] = mapped_column(String(20), unique=True)
    sucursal_id: Mapped[int] = mapped_column(index=True)
    sucursal_clave: Mapped[str] = mapped_column(String(3))
    sucursal_nombre: Mapped[str] = mapped_column(String(80))
    habitacion_id: Mapped[int] = mapped_column(index=True)
    habitacion_numero: Mapped[str] = mapped_column(String(10))
    codigo_punto: Mapped[str] = mapped_column(String(4))
    categoria: Mapped[str] = mapped_column(String(60))
    titulo: Mapped[str] = mapped_column(String(160))
    #: La observación original. Nunca se edita.
    descripcion: Mapped[str] = mapped_column(Text)
    origen_rol: Mapped[str] = mapped_column(String(20))
    origen_revision_id: Mapped[int] = mapped_column(ForeignKey("revisiones.id"))
    reporto_id: Mapped[str] = mapped_column(String(64))
    reporto_nombre: Mapped[str] = mapped_column(String(120))
    reportada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    prioridad: Mapped[str] = mapped_column(String(10), default="media")
    estado: Mapped[str] = mapped_column(String(20), default="reportada", index=True)
    responsable_atencion: Mapped[str | None] = mapped_column(String(120), default=None)
    correccion: Mapped[str | None] = mapped_column(Text, default=None)
    cerrada_por_nombre: Mapped[str | None] = mapped_column(String(120), default=None)
    cerrada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)


class EventoIncidencia(Base, TenantMixin):
    """Quién hizo qué y cuándo. Solo se agrega; nunca se edita ni se borra."""

    __tablename__ = "eventos_incidencia"

    id: Mapped[int] = mapped_column(primary_key=True)
    incidencia_id: Mapped[int] = mapped_column(
        ForeignKey("incidencias.id", ondelete="CASCADE"), index=True
    )
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    actor_id: Mapped[str] = mapped_column(String(64))
    actor_nombre: Mapped[str] = mapped_column(String(120))
    actor_rol: Mapped[str] = mapped_column(String(20))
    accion: Mapped[str] = mapped_column(String(40))
    detalle: Mapped[str] = mapped_column(Text)


class Evidencia(Base, TenantMixin):
    __tablename__ = "evidencias"

    id: Mapped[int] = mapped_column(primary_key=True)
    tipo: Mapped[str] = mapped_column(String(12))
    #: Llave en el disco privado del plugin storage.
    archivo: Mapped[str] = mapped_column(String(300))
    revision_id: Mapped[int | None] = mapped_column(
        ForeignKey("revisiones.id"), default=None, index=True
    )
    codigo_punto: Mapped[str | None] = mapped_column(String(4), default=None)
    incidencia_id: Mapped[int | None] = mapped_column(
        ForeignKey("incidencias.id"), default=None, index=True
    )
    subida_por_id: Mapped[str] = mapped_column(String(64))
    subida_por_nombre: Mapped[str] = mapped_column(String(120))
    subida_por_rol: Mapped[str] = mapped_column(String(20))
    nota: Mapped[str | None] = mapped_column(String(300), default=None)
    creada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class DecisionRenta(Base, TenantMixin):
    """Cada decisión es un renglón nuevo; la vigente es la más reciente."""

    __tablename__ = "decisiones_renta"

    id: Mapped[int] = mapped_column(primary_key=True)
    sucursal_id: Mapped[int] = mapped_column(index=True)
    sucursal_clave: Mapped[str] = mapped_column(String(3))
    habitacion_id: Mapped[int] = mapped_column(index=True)
    habitacion_numero: Mapped[str] = mapped_column(String(10))
    puede_rentarse: Mapped[bool] = mapped_column()
    motivo: Mapped[str] = mapped_column(String(300))
    gerente_id: Mapped[str] = mapped_column(String(64))
    gerente_nombre: Mapped[str] = mapped_column(String(120))
    incidencia_id: Mapped[int | None] = mapped_column(ForeignKey("incidencias.id"), default=None)
    decidida_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class ConsecutivoFolio(Base):
    """El último número de folio usado por sucursal: PIC-LER-000245."""

    __tablename__ = "consecutivos_folio"

    sucursal_id: Mapped[int] = mapped_column(primary_key=True)
    ultimo: Mapped[int] = mapped_column(default=0)
