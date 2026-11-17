"""Fachada pública del módulo sucursal: lo único que inspeccion puede importar.

Devuelve DTOs, nunca entidades, y usa la sesión de quien llama.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from shared.enums import Rol

from .models import CuartoSincronizar
from .repositories import (
    EquipoRepository,
    HabitacionRepository,
    PersonalRepository,
    SucursalRepository,
)
from .services import SucursalService, rol_principal

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True, slots=True)
class SucursalDTO:
    id: int
    clave: str
    nombre: str
    foto: str | None
    frecuencia_gerente_dias: int
    ama_exigible: str
    permite_bien_en_bloque: bool


@dataclass(frozen=True, slots=True)
class HabitacionDTO:
    id: int
    sucursal_id: int
    numero: str
    tiene_jacuzzi: bool
    tiene_alberca: bool
    tiene_sauna: bool
    tiene_terraza: bool
    activa: bool
    tipo: str | None = None
    seccion: str | None = None


@dataclass(frozen=True, slots=True)
class CuartoKairosDTO:
    """Lo que finanzas lee de Kairos de un cuarto, para darlo de alta o corregirlo."""

    numero: str
    tipo: str
    seccion: str | None
    tiene_jacuzzi: bool
    tiene_sauna: bool
    tiene_alberca: bool = False
    tiene_terraza: bool = False


@dataclass(frozen=True, slots=True)
class SincronizacionDTO:
    nuevos: list[str]
    actualizados: list[str]
    sin_cambio: int
    solo_en_picasso: list[str]


@dataclass(frozen=True, slots=True)
class EquipoDTO:
    id: int
    nombre: str
    categoria: str


@dataclass(frozen=True, slots=True)
class PerfilDTO:
    user_id: str
    nombre: str
    rol: Rol
    #: None = ve todas las sucursales (propietario, administración).
    sucursal_id: int | None


async def sucursales(session: AsyncSession, *, tenant_id: str | None) -> list[SucursalDTO]:
    filas = await SucursalRepository(session, tenant_id=tenant_id).todas()
    return [
        SucursalDTO(
            id=s.id,
            clave=s.clave,
            nombre=s.nombre,
            foto=s.foto,
            frecuencia_gerente_dias=s.frecuencia_gerente_dias,
            ama_exigible=s.ama_exigible,
            permite_bien_en_bloque=s.permite_bien_en_bloque,
        )
        for s in filas
        if s.activa
    ]


def _habitacion(h: Any) -> HabitacionDTO:
    return HabitacionDTO(
        id=h.id,
        sucursal_id=h.sucursal_id,
        numero=h.numero,
        tiene_jacuzzi=h.tiene_jacuzzi,
        tiene_alberca=h.tiene_alberca,
        tiene_sauna=h.tiene_sauna,
        tiene_terraza=h.tiene_terraza,
        activa=h.activa,
        tipo=h.tipo,
        seccion=h.seccion,
    )


async def habitaciones(
    session: AsyncSession, *, tenant_id: str | None, sucursal_id: int | None
) -> list[HabitacionDTO]:
    repo = HabitacionRepository(session, tenant_id=tenant_id)
    return [_habitacion(h) for h in await repo.de_sucursal(sucursal_id, solo_activas=True)]


async def habitacion(
    session: AsyncSession, *, tenant_id: str | None, habitacion_id: int
) -> HabitacionDTO | None:
    fila = await HabitacionRepository(session, tenant_id=tenant_id).get(habitacion_id)
    return None if fila is None else _habitacion(fila)


async def perfil_de(
    session: AsyncSession, *, tenant_id: str | None, user_id: str, roles: frozenset[str]
) -> PerfilDTO | None:
    """El puesto lo dice el token; el nombre y la sucursal, la tabla de personal."""
    persona = await PersonalRepository(session, tenant_id=tenant_id).de_usuario(user_id)
    rol = rol_principal(roles) or (Rol(persona.rol) if persona else None)
    if rol is None:
        return None
    return PerfilDTO(
        user_id=user_id,
        nombre=persona.nombre if persona else "Administración",
        rol=rol,
        sucursal_id=persona.sucursal_id if persona else None,
    )


async def equipos_por_habitacion(
    session: AsyncSession, *, tenant_id: str | None, habitacion_ids: list[int]
) -> dict[int, list[EquipoDTO]]:
    """Lo que tiene cada cuarto (solo equipo activo del catálogo)."""
    filas = await EquipoRepository(session, tenant_id=tenant_id).de_habitaciones(habitacion_ids)
    return {
        hid: [EquipoDTO(id=e.id, nombre=e.nombre, categoria=e.categoria) for e in equipos]
        for hid, equipos in filas.items()
    }


async def sincronizar_habitaciones(
    session: AsyncSession,
    *,
    tenant_id: str | None,
    sucursal_id: int,
    cuartos: list[CuartoKairosDTO],
) -> SincronizacionDTO:
    """Alta y corrección de cuartos según Kairos (pasa por las reglas del servicio)."""
    servicio = SucursalService(
        SucursalRepository(session, tenant_id=tenant_id),
        HabitacionRepository(session, tenant_id=tenant_id),
        PersonalRepository(session, tenant_id=tenant_id),
        EquipoRepository(session, tenant_id=tenant_id),
    )
    r = await servicio.sincronizar_habitaciones(
        sucursal_id,
        [
            CuartoSincronizar(
                numero=c.numero,
                tipo=c.tipo,
                seccion=c.seccion,
                tiene_jacuzzi=c.tiene_jacuzzi,
                tiene_sauna=c.tiene_sauna,
                tiene_alberca=c.tiene_alberca,
                tiene_terraza=c.tiene_terraza,
            )
            for c in cuartos
        ],
    )
    return SincronizacionDTO(
        nuevos=r.nuevos,
        actualizados=r.actualizados,
        sin_cambio=r.sin_cambio,
        solo_en_picasso=r.solo_en_picasso,
    )
