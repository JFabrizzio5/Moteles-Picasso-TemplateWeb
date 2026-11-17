"""Acceso a datos del módulo finanzas: ingresos leídos de Kairos y gastos."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import delete, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from jfastframework.errors import NotFoundError

from ..models import (
    FuenteKairos,
    Gasto,
    GastoArchivo,
    GastoIncidencia,
    GastoPartida,
    IngresoDia,
    IngresoTarifa,
    Renta,
)


class FinanzasRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _todas(self, query: Any) -> list[Any]:
        return list((await self.session.execute(query)).scalars())

    async def agregar(self, fila: Any) -> Any:
        self.session.add(fila)
        await self.session.flush()
        return fila

    # -- fuentes ----------------------------------------------------------------

    async def fuentes(self, *, solo_activas: bool = False) -> list[FuenteKairos]:
        query = select(FuenteKairos).order_by(FuenteKairos.sucursal_clave)
        if solo_activas:
            query = query.where(FuenteKairos.activo.is_(True))
        return await self._todas(query)

    async def fuente(self, fuente_id: int) -> FuenteKairos:
        fila = await self.session.get(FuenteKairos, fuente_id)
        if fila is None:
            raise NotFoundError("Esa fuente de Kairos no existe.")
        return fila

    # -- ingresos ---------------------------------------------------------------

    async def ingreso_dia(self, sucursal_id: int, fecha: date) -> IngresoDia | None:
        query = select(IngresoDia).where(
            IngresoDia.sucursal_id == sucursal_id, IngresoDia.fecha == fecha
        )
        return (await self.session.execute(query)).scalars().first()

    async def reemplazar_detalle(
        self,
        sucursal_id: int,
        fecha: date,
        tarifas: Sequence[IngresoTarifa],
        rentas: Sequence[Renta],
    ) -> None:
        """El detalle de un día se pisa entero con lo último que dijo Kairos."""
        for modelo in (IngresoTarifa, Renta):
            await self.session.execute(
                delete(modelo).where(modelo.sucursal_id == sucursal_id, modelo.fecha == fecha)
            )
        self.session.add_all([*tarifas, *rentas])
        await self.session.flush()

    async def ingresos(
        self, *, desde: date, hasta: date, sucursal_id: int | None = None
    ) -> list[IngresoDia]:
        query = select(IngresoDia).where(IngresoDia.fecha >= desde, IngresoDia.fecha <= hasta)
        if sucursal_id is not None:
            query = query.where(IngresoDia.sucursal_id == sucursal_id)
        return await self._todas(query.order_by(IngresoDia.fecha.desc(), IngresoDia.sucursal_id))

    async def tarifas(
        self, *, desde: date, hasta: date, sucursal_id: int | None = None
    ) -> list[tuple[str, int, Decimal]]:
        query = (
            select(
                IngresoTarifa.tarifa,
                func.sum(IngresoTarifa.cantidad),
                func.sum(IngresoTarifa.importe),
            )
            .where(IngresoTarifa.fecha >= desde, IngresoTarifa.fecha <= hasta)
            .group_by(IngresoTarifa.tarifa)
            .order_by(func.sum(IngresoTarifa.importe).desc())
        )
        if sucursal_id is not None:
            query = query.where(IngresoTarifa.sucursal_id == sucursal_id)
        return [
            (t, int(n or 0), Decimal(i or 0))
            for t, n, i in (await self.session.execute(query)).all()
        ]

    async def ingreso_por_habitacion(
        self, *, sucursal_id: int, habitacion: str, desde: date, hasta: date
    ) -> tuple[int, Decimal]:
        query = select(func.count(), func.coalesce(func.sum(Renta.importe), 0)).where(
            Renta.sucursal_id == sucursal_id,
            Renta.habitacion_numero == habitacion,
            Renta.fecha >= desde,
            Renta.fecha <= hasta,
        )
        n, total = (await self.session.execute(query)).one()
        return int(n), Decimal(total)

    async def dias_importados(self, sucursal_id: int, *, desde: date, hasta: date) -> set[date]:
        query = select(IngresoDia.fecha).where(
            IngresoDia.sucursal_id == sucursal_id,
            IngresoDia.fecha >= desde,
            IngresoDia.fecha <= hasta,
        )
        return set((await self.session.execute(query)).scalars())

    # -- gastos -----------------------------------------------------------------

    async def gasto(self, gasto_id: int) -> Gasto:
        fila = await self.session.get(Gasto, gasto_id)
        if fila is None:
            raise NotFoundError("Ese gasto no existe.")
        return fila

    @staticmethod
    def _filtrar_gastos(
        query: Any,
        *,
        ids: Sequence[int] | None = None,
        sucursal_id: int | None = None,
        desde: date | None = None,
        hasta: date | None = None,
        incidencia_id: int | None = None,
        sin_incidencia: bool = False,
        categoria: str | None = None,
        texto: str | None = None,
        incluir_anulados: bool = False,
        solo_pendientes: bool = False,
    ) -> Any:
        """Los mismos filtros para la página, su conteo y la exportación."""
        if ids is not None:
            query = query.where(Gasto.id.in_(list(ids)))
        if sucursal_id is not None:
            query = query.where(Gasto.sucursal_id == sucursal_id)
        if desde is not None:
            query = query.where(Gasto.fecha >= desde)
        if hasta is not None:
            query = query.where(Gasto.fecha <= hasta)
        ligas = select(GastoIncidencia.id).where(GastoIncidencia.gasto_id == Gasto.id)
        if incidencia_id is not None:
            query = query.where(exists(ligas.where(GastoIncidencia.incidencia_id == incidencia_id)))
        if sin_incidencia:
            query = query.where(~exists(ligas))
        if categoria:
            query = query.where(Gasto.categoria == categoria)
        if not incluir_anulados:
            query = query.where(Gasto.estado != "anulado")
        if solo_pendientes:
            query = query.where(Gasto.exportado_en.is_(None))
        if texto:
            patron = f"%{texto.strip()}%"
            query = query.where(
                or_(
                    Gasto.folio.ilike(patron),
                    Gasto.concepto.ilike(patron),
                    Gasto.proveedor.ilike(patron),
                    Gasto.referencia.ilike(patron),
                    exists(
                        select(GastoIncidencia.id).where(
                            GastoIncidencia.gasto_id == Gasto.id,
                            GastoIncidencia.folio.ilike(patron),
                        )
                    ),
                )
            )
        return query

    async def gastos(self, *, limite: int = 500, offset: int = 0, **filtros: Any) -> list[Gasto]:
        query = self._filtrar_gastos(select(Gasto), **filtros)
        query = query.order_by(Gasto.fecha.desc(), Gasto.id.desc()).offset(offset).limit(limite)
        return await self._todas(query)

    async def gastos_por_dia(
        self, *, desde: date, hasta: date, sucursal_id: int | None
    ) -> dict[date, Decimal]:
        query = (
            select(Gasto.fecha, func.sum(Gasto.importe))
            .where(Gasto.fecha >= desde, Gasto.fecha <= hasta, Gasto.estado != "anulado")
            .group_by(Gasto.fecha)
        )
        if sucursal_id is not None:
            query = query.where(Gasto.sucursal_id == sucursal_id)
        return {f: Decimal(t or 0) for f, t in (await self.session.execute(query)).all()}

    async def contar_gastos(self, **filtros: Any) -> tuple[int, Decimal]:
        """Cuántos gastos y cuánto suman con esos filtros (para paginar sin perder el total)."""
        query = self._filtrar_gastos(
            select(func.count(Gasto.id), func.coalesce(func.sum(Gasto.importe), 0)), **filtros
        )
        n, total = (await self.session.execute(query)).one()
        return int(n), Decimal(total)

    async def suma_gastos(
        self, *, desde: date, hasta: date, sucursal_id: int | None = None
    ) -> dict[int, tuple[int, Decimal]]:
        query = (
            select(Gasto.sucursal_id, func.count(), func.coalesce(func.sum(Gasto.importe), 0))
            .where(Gasto.fecha >= desde, Gasto.fecha <= hasta, Gasto.estado != "anulado")
            .group_by(Gasto.sucursal_id)
        )
        if sucursal_id is not None:
            query = query.where(Gasto.sucursal_id == sucursal_id)
        return {s: (int(n), Decimal(t)) for s, n, t in (await self.session.execute(query)).all()}

    async def archivos(self, gasto_ids: Sequence[int]) -> dict[int, list[GastoArchivo]]:
        if not gasto_ids:
            return {}
        filas = await self._todas(
            select(GastoArchivo)
            .where(GastoArchivo.gasto_id.in_(list(gasto_ids)))
            .order_by(GastoArchivo.id)
        )
        por_gasto: dict[int, list[GastoArchivo]] = {}
        for f in filas:
            por_gasto.setdefault(f.gasto_id, []).append(f)
        return por_gasto

    async def incidencias(self, gasto_ids: Sequence[int]) -> dict[int, list[GastoIncidencia]]:
        if not gasto_ids:
            return {}
        filas = await self._todas(
            select(GastoIncidencia)
            .where(GastoIncidencia.gasto_id.in_(list(gasto_ids)))
            .order_by(GastoIncidencia.gasto_id, GastoIncidencia.folio)
        )
        por_gasto: dict[int, list[GastoIncidencia]] = {}
        for f in filas:
            por_gasto.setdefault(f.gasto_id, []).append(f)
        return por_gasto

    async def costos_por_folio(self, sucursal_id: int | None) -> list[tuple[int, int, Decimal]]:
        query = (
            select(GastoIncidencia.incidencia_id, func.count(), func.sum(Gasto.importe))
            .join(Gasto, Gasto.id == GastoIncidencia.gasto_id)
            .where(Gasto.estado != "anulado")
            .group_by(GastoIncidencia.incidencia_id)
        )
        if sucursal_id is not None:
            query = query.where(Gasto.sucursal_id == sucursal_id)
        return [
            (i, int(n), Decimal(t or 0)) for i, n, t in (await self.session.execute(query)).all()
        ]

    async def reemplazar_incidencias(self, gasto_id: int, filas: Sequence[GastoIncidencia]) -> None:
        await self.session.execute(
            delete(GastoIncidencia).where(GastoIncidencia.gasto_id == gasto_id)
        )
        self.session.add_all(list(filas))
        await self.session.flush()

    async def partidas(self, gasto_ids: Sequence[int]) -> dict[int, list[GastoPartida]]:
        if not gasto_ids:
            return {}
        filas = await self._todas(
            select(GastoPartida)
            .where(GastoPartida.gasto_id.in_(list(gasto_ids)))
            .order_by(GastoPartida.gasto_id, GastoPartida.orden)
        )
        por_gasto: dict[int, list[GastoPartida]] = {}
        for f in filas:
            por_gasto.setdefault(f.gasto_id, []).append(f)
        return por_gasto

    async def reemplazar_partidas(self, gasto_id: int, partidas: Sequence[GastoPartida]) -> None:
        await self.session.execute(delete(GastoPartida).where(GastoPartida.gasto_id == gasto_id))
        self.session.add_all(list(partidas))
        await self.session.flush()

    async def partidas_del_periodo(
        self, *, desde: date, hasta: date, sucursal_id: int | None
    ) -> list[tuple[Gasto, GastoPartida]]:
        """Cada partida con su gasto, para auditar (sin anulados)."""
        query = (
            select(Gasto, GastoPartida)
            .join(GastoPartida, GastoPartida.gasto_id == Gasto.id)
            .where(Gasto.fecha >= desde, Gasto.fecha <= hasta, Gasto.estado != "anulado")
        )
        if sucursal_id is not None:
            query = query.where(Gasto.sucursal_id == sucursal_id)
        return [(g, p) for g, p in (await self.session.execute(query)).all()]

    async def archivo(self, gasto_id: int, archivo_id: int) -> GastoArchivo:
        fila = await self.session.get(GastoArchivo, archivo_id)
        if fila is None or fila.gasto_id != gasto_id:
            raise NotFoundError("Ese comprobante no existe.")
        return fila

    async def borrar(self, fila: Any) -> None:
        await self.session.delete(fila)
        await self.session.flush()
