"""Modelos del módulo sucursal."""

from __future__ import annotations

from .sucursal_entity import Equipo, Habitacion, HabitacionEquipo, Personal, Sucursal
from .sucursal_models import (
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
    SucursalRead,
    SucursalUpdate,
)

__all__ = [
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
    "Sucursal",
    "SucursalRead",
    "SucursalUpdate",
]
