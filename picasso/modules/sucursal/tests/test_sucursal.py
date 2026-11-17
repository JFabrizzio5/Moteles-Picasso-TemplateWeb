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


class _Sucursales:
    async def get_or_raise(self, sucursal_id: int) -> object:
        return object()


class _Cuartos:
    def __init__(self, filas: list[Habitacion]) -> None:
        self.filas = filas
        self.altas: list[str] = []

    async def de_sucursal(self, sucursal_id: int, *, solo_activas: bool) -> list[Habitacion]:
        return self.filas

    async def create(self, **datos: object) -> Habitacion:
        self.altas.append(str(datos["numero"]))
        return Habitacion(**datos)

    async def update(self, fila: Habitacion, **cambios: object) -> Habitacion:
        for campo, valor in cambios.items():
            setattr(fila, campo, valor)
        return fila


def _cuarto(numero: str, **kw: object) -> Habitacion:
    base: dict[str, object] = dict(
        id=int(numero),
        sucursal_id=1,
        numero=numero,
        tiene_jacuzzi=False,
        tiene_alberca=False,
        tiene_sauna=False,
        tiene_terraza=False,
        activa=True,
        tipo=None,
        seccion=None,
    )
    base.update(kw)
    return Habitacion(**base)


def test_sincronizar_cuartos_da_de_alta_corrige_y_no_borra() -> None:
    from modules.sucursal.models import CuartoSincronizar

    en_obra = _cuarto("120", tiene_alberca=True)
    con_alberca = _cuarto("101", tiene_alberca=True, tiene_jacuzzi=False)
    igual = _cuarto("102", tipo="Suite", seccion="motel")
    cuartos = _Cuartos([con_alberca, igual, en_obra])
    service = SucursalService(
        sucursales=_Sucursales(),  # type: ignore[arg-type]
        habitaciones=cuartos,  # type: ignore[arg-type]
        personal=None,  # type: ignore[arg-type]
        equipos=None,  # type: ignore[arg-type]
    )
    r = asyncio.run(
        service.sincronizar_habitaciones(
            1,
            [
                CuartoSincronizar(
                    numero="101",
                    tipo="Jacuzzi y sauna",
                    seccion="motel",
                    tiene_jacuzzi=True,
                    tiene_sauna=True,
                ),
                CuartoSincronizar(
                    numero="102",
                    tipo="Suite",
                    seccion="motel",
                    tiene_jacuzzi=False,
                    tiene_sauna=False,
                ),
                CuartoSincronizar(
                    numero="901",
                    tipo="Pent house con jacuzzi",
                    seccion="hotel",
                    tiene_jacuzzi=True,
                    tiene_sauna=False,
                ),
            ],
        )
    )
    assert r.nuevos == ["901"] and cuartos.altas == ["901"]
    assert r.actualizados == ["101"] and r.sin_cambio == 1
    # Lo que no dice Kairos (alberca) se queda; el cuarto sin rentas solo se reporta.
    assert con_alberca.tiene_alberca and con_alberca.tiene_jacuzzi and con_alberca.tiene_sauna
    assert r.solo_en_picasso == ["120"] and en_obra.activa
