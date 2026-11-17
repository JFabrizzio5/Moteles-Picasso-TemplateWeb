"""Acceso a datos del módulo sucursal."""

from __future__ import annotations

from sqlalchemy import delete, func, insert, select

from jfastframework.db import BaseRepository

from ..models import Equipo, Habitacion, HabitacionEquipo, Personal, Sucursal


class SucursalRepository(BaseRepository[Sucursal]):
    model = Sucursal

    async def todas(self) -> list[Sucursal]:
        query = self._base_query().order_by(Sucursal.id)
        return list((await self.session.execute(query)).scalars())

    async def conteo_habitaciones(self) -> dict[int, int]:
        query = (
            select(Habitacion.sucursal_id, func.count())
            .where(Habitacion.activa.is_(True))
            .group_by(Habitacion.sucursal_id)
        )
        return {sid: total for sid, total in (await self.session.execute(query)).all()}


class HabitacionRepository(BaseRepository[Habitacion]):
    model = Habitacion

    async def de_sucursal(self, sucursal_id: int | None, *, solo_activas: bool) -> list[Habitacion]:
        query = self._base_query()
        if sucursal_id is not None:
            query = query.where(Habitacion.sucursal_id == sucursal_id)
        if solo_activas:
            query = query.where(Habitacion.activa.is_(True))
        # Orden natural de cuarto: 9 antes que 10.
        query = query.order_by(
            Habitacion.sucursal_id, func.length(Habitacion.numero), Habitacion.numero
        )
        return list((await self.session.execute(query)).scalars())


class PersonalRepository(BaseRepository[Personal]):
    model = Personal

    async def de_usuario(self, user_id: str) -> Personal | None:
        return await self.find_one(user_id=user_id)

    async def todos(self) -> list[Personal]:
        query = self._base_query().order_by(Personal.sucursal_id, Personal.rol, Personal.nombre)
        return list((await self.session.execute(query)).scalars())


class EquipoRepository(BaseRepository[Equipo]):
    model = Equipo

    async def todos(self) -> list[Equipo]:
        query = self._base_query().order_by(Equipo.categoria, Equipo.nombre)
        return list((await self.session.execute(query)).scalars())

    async def de_habitaciones(self, habitacion_ids: list[int]) -> dict[int, list[Equipo]]:
        """Lo que tiene cada cuarto, solo equipo activo."""
        if not habitacion_ids:
            return {}
        query = (
            select(HabitacionEquipo.habitacion_id, Equipo)
            .join(Equipo, Equipo.id == HabitacionEquipo.equipo_id)
            .where(HabitacionEquipo.habitacion_id.in_(habitacion_ids), Equipo.activo.is_(True))
            .order_by(Equipo.categoria, Equipo.nombre)
        )
        salida: dict[int, list[Equipo]] = {}
        for hid, equipo in (await self.session.execute(query)).all():
            salida.setdefault(hid, []).append(equipo)
        return salida

    async def ids_de(self, habitacion_ids: list[int]) -> dict[int, list[int]]:
        if not habitacion_ids:
            return {}
        query = select(HabitacionEquipo.habitacion_id, HabitacionEquipo.equipo_id).where(
            HabitacionEquipo.habitacion_id.in_(habitacion_ids)
        )
        salida: dict[int, list[int]] = {}
        for hid, eid in (await self.session.execute(query)).all():
            salida.setdefault(hid, []).append(eid)
        return salida

    async def asignar(self, habitacion_id: int, equipo_ids: list[int]) -> None:
        await self.session.execute(
            delete(HabitacionEquipo).where(HabitacionEquipo.habitacion_id == habitacion_id)
        )
        if equipo_ids:
            await self.session.execute(
                insert(HabitacionEquipo),
                [{"habitacion_id": habitacion_id, "equipo_id": e} for e in equipo_ids],
            )
        await self.session.flush()
