"""Vocabulario que comparten los módulos sucursal e inspeccion.

El valor es el formato en el cable: se guarda en columnas, viaja en JSON y lo
lee el front. Cambiar un valor es una migración de datos.
"""

from __future__ import annotations

from enum import StrEnum


class Rol(StrEnum):
    """Puesto de una persona en la operación.

    Coincide con el nombre del rol en el plugin `accounts`, así que el token
    ya trae el puesto sin consultar la base.
    """

    ADMIN = "admin"
    PROPIETARIO = "propietario"
    GERENTE = "gerente"
    AMA_LLAVES = "ama_llaves"


#: Del de más alcance al de menos; si alguien tiene dos, manda el primero.
PRIORIDAD_ROL: tuple[Rol, ...] = (Rol.ADMIN, Rol.PROPIETARIO, Rol.GERENTE, Rol.AMA_LLAVES)
