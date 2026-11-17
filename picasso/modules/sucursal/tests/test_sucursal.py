"""Pruebas del módulo sucursal (sin base de datos)."""

from __future__ import annotations

import asyncio

import pytest

from jfastframework.errors import ValidationError

from modules.sucursal.models import Habitacion, HabitacionUpdate
from modules.sucursal.services import SucursalService, rol_principal
from modules.sucursal.validations import validar_asignacion
from shared.enums import Rol


def test_gerente_y_ama_necesitan_sucursal() -> None:
    with pytest.raises(ValidationError):
        validar_asignacion(Rol.GERENTE, None)
    with pytest.raises(ValidationError):
        validar_asignacion(Rol.AMA_LLAVES, None)
    validar_asignacion(Rol.GERENTE, 1)


def test_propietario_no_lleva_sucursal() -> None:
    with pytest.raises(ValidationError):
        validar_asignacion(Rol.PROPIETARIO, 3)
    validar_asignacion(Rol.PROPIETARIO, None)


def test_rol_principal_toma_el_de_mas_alcance() -> None:
    assert rol_principal(frozenset({"ama_llaves", "gerente"})) is Rol.GERENTE
    assert rol_principal(frozenset({"admin", "propietario"})) is Rol.ADMIN
    assert rol_principal(frozenset({"otro"})) is None


class _Habitaciones:
    def __init__(self, fila: Habitacion) -> None:
        self.fila = fila

    async def get_or_raise(self, habitacion_id: int) -> Habitacion:
        return self.fila

    async def update(self, fila: Habitacion, **cambios: object) -> Habitacion:
        for campo, valor in cambios.items():
            setattr(fila, campo, valor)
        return fila


class _Equipos:
    async def ids_de(self, habitacion_ids: list[int]) -> dict[int, list[int]]:
        return {7: [3, 1]}


def test_dar_de_baja_un_cuarto_conserva_su_equipo_en_la_respuesta() -> None:
    # Ajustes reemplaza la tarjeta con la respuesta del PATCH: si no trae
    # equipo_ids, el cuarto aparece como "Sin equipo registrado".
    cuarto = Habitacion(
        id=7,
        sucursal_id=1,
        numero="104",
        tiene_jacuzzi=False,
        tiene_alberca=False,
        tiene_sauna=False,
        tiene_terraza=False,
        activa=True,
    )
    service = SucursalService(
        sucursales=None,  # type: ignore[arg-type]
        habitaciones=_Habitaciones(cuarto),  # type: ignore[arg-type]
        personal=None,  # type: ignore[arg-type]
        equipos=_Equipos(),  # type: ignore[arg-type]
    )
    leida = asyncio.run(service.actualizar_habitacion(7, HabitacionUpdate(activa=False)))
    assert leida.activa is False
    assert leida.equipo_ids == [1, 3]
