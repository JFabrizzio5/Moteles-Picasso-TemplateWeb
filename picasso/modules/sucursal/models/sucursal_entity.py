"""Entidades del módulo sucursal: sucursales, habitaciones y personal."""

from __future__ import annotations

from sqlalchemy import ForeignKey, String, UniqueConstraint, true
from sqlalchemy.orm import Mapped, mapped_column

from jfastframework.db import Base, TenantMixin, TimestampMixin


class Sucursal(Base, TimestampMixin, TenantMixin):
    __tablename__ = "sucursales"

    id: Mapped[int] = mapped_column(primary_key=True)
    #: Tres letras que van en el folio: PIC-LER-000245.
    clave: Mapped[str] = mapped_column(String(3), unique=True)
    nombre: Mapped[str] = mapped_column(String(80))
    #: Ruta de la foto pública en el front (/sucursales/lerma.jpg); None = pendiente.
    foto: Mapped[str | None] = mapped_column(String(200), default=None)
    #: Cada cuántos días el gerente debe revisar cada habitación (1 = diaria).
    frecuencia_gerente_dias: Mapped[int] = mapped_column(default=1)
    ama_exigible: Mapped[str] = mapped_column(String(20), default="por_limpieza")
    #: Si el checklist deja marcar "Lo demás está bien" de un toque. Interruptor:
    #: el documento pide revisar punto por punto; la operación pidió rapidez.
    permite_bien_en_bloque: Mapped[bool] = mapped_column(default=True, server_default=true())
    activa: Mapped[bool] = mapped_column(default=True)


class Habitacion(Base, TimestampMixin, TenantMixin):
    __tablename__ = "habitaciones"
    __table_args__ = (
        UniqueConstraint("sucursal_id", "numero", name="uq_habitaciones_sucursal_numero"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    sucursal_id: Mapped[int] = mapped_column(ForeignKey("sucursales.id"), index=True)
    numero: Mapped[str] = mapped_column(String(10))
    # Lo que tiene la habitación decide qué puntos del checklist aplican: sin
    # jacuzzi, el punto del jacuzzi entra como No aplica con su motivo.
    tiene_jacuzzi: Mapped[bool] = mapped_column(default=False)
    tiene_alberca: Mapped[bool] = mapped_column(default=False)
    tiene_sauna: Mapped[bool] = mapped_column(default=False)
    tiene_terraza: Mapped[bool] = mapped_column(default=False)
    activa: Mapped[bool] = mapped_column(default=True)


class Personal(Base, TimestampMixin, TenantMixin):
    """La persona detrás de una cuenta: nombre, puesto y sucursal.

    La cuenta (correo, contraseña, roles) vive en el plugin accounts; aquí solo
    lo que la operación necesita y accounts no guarda.
    """

    __tablename__ = "personal"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), unique=True)
    nombre: Mapped[str] = mapped_column(String(120))
    rol: Mapped[str] = mapped_column(String(20))
    #: None para propietarios y administración: ven las seis sucursales.
    sucursal_id: Mapped[int | None] = mapped_column(ForeignKey("sucursales.id"), default=None)
    activo: Mapped[bool] = mapped_column(default=True)


class Equipo(Base, TimestampMixin, TenantMixin):
    """Algo que un cuarto puede tener: Netflix, sillón tántrico, minibar…

    Es un catálogo que administra la cuenta de administración; cada cuarto
    elige del catálogo lo que tiene. Lo que tiene entra a su checklist.
    """

    __tablename__ = "equipos"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(60), unique=True)
    categoria: Mapped[str] = mapped_column(String(40))
    activo: Mapped[bool] = mapped_column(default=True)


class HabitacionEquipo(Base):
    __tablename__ = "habitacion_equipos"

    habitacion_id: Mapped[int] = mapped_column(
        ForeignKey("habitaciones.id", ondelete="CASCADE"), primary_key=True
    )
    equipo_id: Mapped[int] = mapped_column(
        ForeignKey("equipos.id", ondelete="CASCADE"), primary_key=True
    )
