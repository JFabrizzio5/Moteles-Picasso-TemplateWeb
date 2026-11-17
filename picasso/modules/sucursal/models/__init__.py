"""Modelos del módulo sucursal."""

from __future__ import annotations

from .sucursal_entity import Equipo, Habitacion, HabitacionEquipo, Personal, Sucursal
from .sucursal_models import (
    CuartoSincronizar,
    EquipoCreate,
    EquipoRead,
    EquiposDeHabitacion,
    EquipoUpdate,
    HabitacionCreate,
    HabitacionRead,
    HabitacionUpdate,
    PerfilRead,
    PersonalCreate,
    PersonalRead,
    Sincronizacion,
    SucursalRead,
    SucursalUpdate,
)

__all__ = [
    "CuartoSincronizar",
    "Equipo",
    "EquipoCreate",
    "EquipoRead",
    "EquipoUpdate",
    "EquiposDeHabitacion",
    "Habitacion",
    "HabitacionCreate",
    "HabitacionEquipo",
    "HabitacionRead",
    "HabitacionUpdate",
    "PerfilRead",
    "Personal",
    "PersonalCreate",
    "PersonalRead",
    "Sincronizacion",
    "Sucursal",
    "SucursalRead",
    "SucursalUpdate",
]
