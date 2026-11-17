"""Entidades del módulo finanzas.

Ingresos: copia de lo que registra Kairos (el sistema de recepción de cada
motel). Picasso no los captura ni los corrige: se leen cada noche y se pisan
con lo que diga Kairos.

Gastos: los captura Picasso (gerente, administración o propietarios). Pueden
ligarse a un folio de mantenimiento; del folio se guarda una copia del código y
el título, porque los módulos no se unen por SQL.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from jfastframework.db import Base, TenantMixin, TimestampMixin

DINERO = Numeric(12, 2)


class FuenteKairos(Base, TimestampMixin, TenantMixin):
    """De dónde se leen los ingresos de una sucursal: su Kairos."""

    __tablename__ = "fuentes_kairos"

    id: Mapped[int] = mapped_column(primary_key=True)
    #: La clave de la sucursal en Picasso (LER, VAQ...). Se resuelve a su id al importar.
    sucursal_clave: Mapped[str] = mapped_column(String(3), unique=True)
    #: Como lo llama Kairos (puede no coincidir con Picasso: Tláhuac / Periférico).
    nombre_kairos: Mapped[str] = mapped_column(String(60))
    url_base: Mapped[str] = mapped_column(String(200))
    activo: Mapped[bool] = mapped_column(default=True)
    #: Primer día con ventas que encontró el rellenado del historial.
    primer_dia: Mapped[date | None] = mapped_column(Date, default=None)
    #: Hasta qué día hacia atrás ya está rellenado el historial.
    historial_desde: Mapped[date | None] = mapped_column(Date, default=None)
    ultima_corrida: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    ultimo_ok: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    ultimo_error: Mapped[str | None] = mapped_column(String(300), default=None)


class IngresoDia(Base, TimestampMixin, TenantMixin):
    """El resumen de un día en Kairos: la pantalla de inicio de su vista móvil."""

    __tablename__ = "ingresos_dia"
    __table_args__ = (UniqueConstraint("sucursal_id", "fecha", name="uq_ingresos_dia"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    sucursal_id: Mapped[int] = mapped_column(index=True)
    fecha: Mapped[date] = mapped_column(Date, index=True)
    habitaciones: Mapped[Decimal] = mapped_column(DINERO, default=Decimal(0))
    rentas: Mapped[int] = mapped_column(default=0)
    extras: Mapped[Decimal] = mapped_column(DINERO, default=Decimal(0))
    extras_n: Mapped[int] = mapped_column(default=0)
    room_service: Mapped[Decimal] = mapped_column(DINERO, default=Decimal(0))
    comandas: Mapped[int] = mapped_column(default=0)
    #: Lo que el personal anotó como gasto en Kairos; los gastos de verdad van en `gastos`.
    gastos_kairos: Mapped[Decimal] = mapped_column(DINERO, default=Decimal(0))
    gastos_kairos_n: Mapped[int] = mapped_column(default=0)
    #: El "Total" de Kairos: habitaciones + extras + room service - gastos.
    total: Mapped[Decimal] = mapped_column(DINERO, default=Decimal(0))
    #: False = solo el resumen (historial viejo); True = trae tarifas y rentas.
    con_detalle: Mapped[bool] = mapped_column(default=False)
    importado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class IngresoTarifa(Base, TimestampMixin, TenantMixin):
    """Rentas e importe por tarifa en un día (Motel Suite, Hotel Jacuzzi...)."""

    __tablename__ = "ingresos_tarifa"
    __table_args__ = (
        UniqueConstraint("sucursal_id", "fecha", "tarifa", name="uq_ingresos_tarifa"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    sucursal_id: Mapped[int] = mapped_column(index=True)
    fecha: Mapped[date] = mapped_column(Date, index=True)
    tarifa: Mapped[str] = mapped_column(String(80))
    cantidad: Mapped[int] = mapped_column(default=0)
    importe: Mapped[Decimal] = mapped_column(DINERO, default=Decimal(0))


class Renta(Base, TimestampMixin, TenantMixin):
    """Cada renta de un día: cuarto, forma de pago e importe."""

    __tablename__ = "rentas"
    __table_args__ = (
        UniqueConstraint("sucursal_id", "fecha", "renglon", name="uq_rentas_renglon"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    sucursal_id: Mapped[int] = mapped_column(index=True)
    fecha: Mapped[date] = mapped_column(Date, index=True)
    #: El número de renglón en la lista de Kairos de ese día.
    renglon: Mapped[int] = mapped_column()
    folio_kairos: Mapped[str] = mapped_column(String(20))
    habitacion_numero: Mapped[str] = mapped_column(String(10), index=True)
    forma_pago: Mapped[str] = mapped_column(String(40))
    importe: Mapped[Decimal] = mapped_column(DINERO, default=Decimal(0))
    #: Hora de entrada, de la marca de tiempo que Kairos pone en cada renta.
    entrada: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)


class Gasto(Base, TimestampMixin, TenantMixin):
    """Un egreso capturado en Picasso."""

    __tablename__ = "gastos"

    id: Mapped[int] = mapped_column(primary_key=True)
    #: GTO-<clave>-<id>, asignado al guardar.
    folio: Mapped[str] = mapped_column(String(24), default="", index=True)
    sucursal_id: Mapped[int] = mapped_column(index=True)
    sucursal_clave: Mapped[str] = mapped_column(String(3))
    sucursal_nombre: Mapped[str] = mapped_column(String(80))
    fecha: Mapped[date] = mapped_column(Date, index=True)
    categoria: Mapped[str] = mapped_column(String(20))
    concepto: Mapped[str] = mapped_column(String(200))
    #: Beneficiario en E-Cont.
    proveedor: Mapped[str] = mapped_column(String(120))
    rfc_proveedor: Mapped[str | None] = mapped_column(String(13), default=None)
    forma_pago: Mapped[str] = mapped_column(String(20))
    tipo_operacion: Mapped[str] = mapped_column(String(30), default="gasto")
    banco: Mapped[str | None] = mapped_column(String(40), default=None)
    #: #FACTURA en E-Cont: número de factura, cheque o referencia.
    referencia: Mapped[str | None] = mapped_column(String(40), default=None)
    importe: Mapped[Decimal] = mapped_column(DINERO)
    nota: Mapped[str | None] = mapped_column(Text, default=None)
    incidencia_id: Mapped[int | None] = mapped_column(index=True, default=None)
    incidencia_folio: Mapped[str | None] = mapped_column(String(24), default=None)
    incidencia_titulo: Mapped[str | None] = mapped_column(String(160), default=None)
    capturo_id: Mapped[str] = mapped_column(String(64))
    capturo_nombre: Mapped[str] = mapped_column(String(120))
    capturo_rol: Mapped[str] = mapped_column(String(20))
    estado: Mapped[str] = mapped_column(String(12), default="registrado", index=True)
    #: La última vez que entró a un archivo para E-Cont.
    exportado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)


class GastoPartida(Base, TimestampMixin, TenantMixin):
    """Cada cosa que se compró en un gasto: «Broca para tornillo · 1 pza · $30».

    El total del gasto es la suma de sus partidas: no se acepta «Verdulería
    $700» sin decir qué se compró. Así se audita artículo por artículo.
    """

    __tablename__ = "gasto_partidas"

    id: Mapped[int] = mapped_column(primary_key=True)
    gasto_id: Mapped[int] = mapped_column(ForeignKey("gastos.id", ondelete="CASCADE"), index=True)
    orden: Mapped[int] = mapped_column()
    descripcion: Mapped[str] = mapped_column(String(120))
    #: En minúsculas y sin espacios de más, para agrupar el mismo artículo.
    articulo: Mapped[str] = mapped_column(String(120), index=True)
    cantidad: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    unidad: Mapped[str] = mapped_column(String(12))
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    importe: Mapped[Decimal] = mapped_column(DINERO)
    categoria: Mapped[str] = mapped_column(String(20), index=True)


class GastoArchivo(Base, TimestampMixin, TenantMixin):
    """Comprobante de un gasto: foto del ticket, PDF o XML de la factura."""

    __tablename__ = "gasto_archivos"

    id: Mapped[int] = mapped_column(primary_key=True)
    gasto_id: Mapped[int] = mapped_column(ForeignKey("gastos.id", ondelete="CASCADE"), index=True)
    tipo: Mapped[str] = mapped_column(String(8))
    archivo: Mapped[str] = mapped_column(String(200))
    nombre: Mapped[str] = mapped_column(String(160))
    #: UUID del CFDI cuando es un XML de factura (lo lee al subirlo).
    uuid_cfdi: Mapped[str | None] = mapped_column(String(36), default=None)
