"""Contratos del módulo sucursal."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from shared.enums import Rol

from ..enums import AmaExigible


class SucursalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    clave: str
    nombre: str
    foto: str | None
    frecuencia_gerente_dias: int
    ama_exigible: AmaExigible
    permite_bien_en_bloque: bool
    activa: bool
    habitaciones: int = 0


class SucursalUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=80)
    foto: str | None = Field(default=None, max_length=200)
    frecuencia_gerente_dias: int | None = Field(default=None, ge=1, le=7)
    ama_exigible: AmaExigible | None = None
    permite_bien_en_bloque: bool | None = None


class HabitacionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sucursal_id: int
    numero: str
    tiene_jacuzzi: bool
    tiene_alberca: bool
    tiene_sauna: bool
    tiene_terraza: bool
    activa: bool
    equipo_ids: list[int] = Field(default_factory=list)


class HabitacionCreate(BaseModel):
    numero: str = Field(min_length=1, max_length=10)
    tiene_jacuzzi: bool = False
    tiene_alberca: bool = False
    tiene_sauna: bool = False
    tiene_terraza: bool = False


class HabitacionUpdate(BaseModel):
    tiene_jacuzzi: bool | None = None
    tiene_alberca: bool | None = None
    tiene_sauna: bool | None = None
    tiene_terraza: bool | None = None
    activa: bool | None = None


class EquipoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    categoria: str
    activo: bool


class EquipoCreate(BaseModel):
    nombre: str = Field(min_length=2, max_length=60)
    categoria: str = Field(min_length=2, max_length=40)


class EquipoUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=60)
    categoria: str | None = Field(default=None, min_length=2, max_length=40)
    activo: bool | None = None


class EquiposDeHabitacion(BaseModel):
    equipo_ids: list[int] = Field(default_factory=list, max_length=60)


class PerfilRead(BaseModel):
    """Quién está usando la app y qué puede ver."""

    user_id: str
    nombre: str
    email: str | None = None
    rol: Rol
    sucursal_id: int | None
    sucursal_nombre: str | None
    sucursal_clave: str | None


class PersonalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: str
    nombre: str
    rol: Rol
    sucursal_id: int | None
    activo: bool


class PersonalCreate(BaseModel):
    nombre: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=10, max_length=200)
    rol: Rol
    sucursal_id: int | None = None
