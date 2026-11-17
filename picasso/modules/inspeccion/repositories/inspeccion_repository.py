"""Acceso a datos del módulo inspeccion.

Un solo repositorio para las tablas del módulo: revisiones, resultados, folios,
historial, evidencias y decisiones de renta se leen casi siempre juntos.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import and_, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from jfastframework.errors import NotFoundError

from ..models import (
    DecisionRenta,
    EventoIncidencia,
    Evidencia,
    Incidencia,
    ResultadoPunto,
    Revision,
)

ABIERTAS = ("reportada", "en_atencion")


class InspeccionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _todas(self, query: Any) -> list[Any]:
        return list((await self.session.execute(query)).scalars())

    async def agregar(self, fila: Any) -> Any:
        self.session.add(fila)
        await self.session.flush()
        return fila

    # -- revisiones ------------------------------------------------------

    async def revision(self, revision_id: int) -> Revision:
        fila = await self.session.get(Revision, revision_id)
        if fila is None:
            raise NotFoundError(f"la revisión {revision_id} no existe")
        return fila

    async def revision_en_curso(self, habitacion_id: int, rol: str) -> Revision | None:
        query = (
            select(Revision)
            .where(
                Revision.habitacion_id == habitacion_id,
                Revision.rol == rol,
                Revision.estado == "en_curso",
            )
            .order_by(Revision.iniciada_en.desc())
            .limit(1)
        )
        return (await self.session.execute(query)).scalars().first()

    async def resultados(self, revision_ids: Sequence[int]) -> list[ResultadoPunto]:
        if not revision_ids:
            return []
        query = (
            select(ResultadoPunto)
            .where(ResultadoPunto.revision_id.in_(revision_ids))
            .order_by(ResultadoPunto.revision_id, ResultadoPunto.orden)
        )
        return await self._todas(query)

    async def resultado(self, revision_id: int, codigo: str) -> ResultadoPunto:
        query = select(ResultadoPunto).where(
            ResultadoPunto.revision_id == revision_id, ResultadoPunto.codigo == codigo
        )
        fila = (await self.session.execute(query)).scalars().first()
        if fila is None:
            raise NotFoundError(f"el punto {codigo} no está en esta revisión")
        return fila

    async def revisiones(
        self,
        *,
        sucursal_id: int | None = None,
        habitacion_id: int | None = None,
        rol: str | None = None,
        desde: datetime | None = None,
        hasta: datetime | None = None,
        estado: str | None = None,
        limite: int = 200,
    ) -> list[Revision]:
        query = select(Revision)
        if sucursal_id is not None:
            query = query.where(Revision.sucursal_id == sucursal_id)
        if habitacion_id is not None:
            query = query.where(Revision.habitacion_id == habitacion_id)
        if rol is not None:
            query = query.where(Revision.rol == rol)
        if desde is not None:
            query = query.where(Revision.iniciada_en >= desde)
        if hasta is not None:
            query = query.where(Revision.iniciada_en < hasta)
        if estado is not None:
            query = query.where(Revision.estado == estado)
        return await self._todas(query.order_by(Revision.iniciada_en.desc()).limit(limite))

    async def ultimas_por_habitacion(self, sucursal_id: int | None) -> list[Revision]:
        """La revisión más reciente de cada (habitación, puesto)."""
        sub = select(
            Revision.id,
            func.row_number()
            .over(
                partition_by=(Revision.habitacion_id, Revision.rol),
                order_by=Revision.iniciada_en.desc(),
            )
            .label("n"),
        )
        if sucursal_id is not None:
            sub = sub.where(Revision.sucursal_id == sucursal_id)
        sub_q = sub.subquery()
        query = select(Revision).join(sub_q, and_(sub_q.c.id == Revision.id, sub_q.c.n == 1))
        return await self._todas(query)

    async def ultimos_chequeos(
        self, *, sucursal_id: int | None = None, habitacion_id: int | None = None
    ) -> dict[int, Revision]:
        """Por cuarto, la revisión terminada más reciente (de cualquier puesto)."""
        sub = select(
            Revision.id,
            func.row_number()
            .over(partition_by=Revision.habitacion_id, order_by=Revision.completada_en.desc())
            .label("n"),
        ).where(Revision.estado == "completa", Revision.completada_en.is_not(None))
        if sucursal_id is not None:
            sub = sub.where(Revision.sucursal_id == sucursal_id)
        if habitacion_id is not None:
            sub = sub.where(Revision.habitacion_id == habitacion_id)
        sub_q = sub.subquery()
        query = select(Revision).join(sub_q, and_(sub_q.c.id == Revision.id, sub_q.c.n == 1))
        return {r.habitacion_id: r for r in await self._todas(query)}

    async def ultimo_chequeo_por_sucursal(self) -> dict[int, datetime]:
        query = (
            select(Revision.sucursal_id, func.max(Revision.completada_en))
            .where(Revision.estado == "completa")
            .group_by(Revision.sucursal_id)
        )
        filas = (await self.session.execute(query)).all()
        return {sid: fecha for sid, fecha in filas if fecha is not None}

    async def ultima_gerente_completa(self, sucursal_id: int | None) -> dict[int, datetime]:
        query = (
            select(Revision.habitacion_id, func.max(Revision.completada_en))
            .where(Revision.rol == "gerente", Revision.estado == "completa")
            .group_by(Revision.habitacion_id)
        )
        if sucursal_id is not None:
            query = query.where(Revision.sucursal_id == sucursal_id)
        filas = (await self.session.execute(query)).all()
        return {hid: fecha for hid, fecha in filas if fecha is not None}

    async def conteo_resultados(self, revision_ids: Sequence[int]) -> dict[int, dict[str, int]]:
        if not revision_ids:
            return {}
        query = (
            select(ResultadoPunto.revision_id, ResultadoPunto.resultado, func.count())
            .where(ResultadoPunto.revision_id.in_(revision_ids))
            .group_by(ResultadoPunto.revision_id, ResultadoPunto.resultado)
        )
        salida: dict[int, dict[str, int]] = {}
        for rid, resultado, total in (await self.session.execute(query)).all():
            salida.setdefault(rid, {})[resultado] = total
        return salida

    async def resultados_del_periodo(
        self, desde: datetime, hasta: datetime
    ) -> list[tuple[int, str, int]]:
        """(sucursal_id, resultado, cuántos) de las revisiones completas del periodo."""
        query = (
            select(Revision.sucursal_id, ResultadoPunto.resultado, func.count())
            .join(Revision, Revision.id == ResultadoPunto.revision_id)
            .where(
                Revision.estado == "completa",
                Revision.completada_en >= desde,
                Revision.completada_en < hasta,
            )
            .group_by(Revision.sucursal_id, ResultadoPunto.resultado)
        )
        return [(s, r, n) for s, r, n in (await self.session.execute(query)).all()]

    async def fallas_por_punto(
        self, desde: datetime, hasta: datetime, sucursal_id: int | None
    ) -> list[tuple[str, str, int]]:
        query = (
            select(ResultadoPunto.codigo, ResultadoPunto.titulo, func.count())
            .join(Revision, Revision.id == ResultadoPunto.revision_id)
            .where(
                ResultadoPunto.resultado == "falla",
                Revision.iniciada_en >= desde,
                Revision.iniciada_en < hasta,
            )
            .group_by(ResultadoPunto.codigo, ResultadoPunto.titulo)
            .order_by(func.count().desc())
            .limit(10)
        )
        if sucursal_id is not None:
            query = query.where(Revision.sucursal_id == sucursal_id)
        return [(c, t, n) for c, t, n in (await self.session.execute(query)).all()]

    # -- incidencias -----------------------------------------------------

    async def siguiente_folio(self, sucursal_id: int) -> int:
        """Un número por sucursal, sin huecos por carreras: el UPDATE serializa."""
        resultado = await self.session.execute(
            text(
                "INSERT INTO consecutivos_folio (sucursal_id, ultimo) VALUES (:s, 1) "
                "ON CONFLICT (sucursal_id) DO UPDATE "
                "SET ultimo = consecutivos_folio.ultimo + 1 RETURNING ultimo"
            ),
            {"s": sucursal_id},
        )
        return int(resultado.scalar_one())

    async def incidencia(self, incidencia_id: int) -> Incidencia:
        fila = await self.session.get(Incidencia, incidencia_id)
        if fila is None:
            raise NotFoundError(f"el folio {incidencia_id} no existe")
        return fila

    async def incidencia_abierta_de(self, habitacion_id: int, codigo: str) -> Incidencia | None:
        """ "Se genera un folio o se vincula uno abierto de la misma falla." """
        query = (
            select(Incidencia)
            .where(
                Incidencia.habitacion_id == habitacion_id,
                Incidencia.codigo_punto == codigo,
                Incidencia.estado.in_(ABIERTAS),
            )
            .order_by(Incidencia.reportada_en.desc())
            .limit(1)
        )
        return (await self.session.execute(query)).scalars().first()

    @staticmethod
    def _filtrar_incidencias(
        query: Any,
        *,
        sucursal_id: int | None = None,
        habitacion_id: int | None = None,
        estados: Sequence[str] | None = None,
        prioridad: str | None = None,
        desde: datetime | None = None,
        hasta: datetime | None = None,
        texto_busqueda: str | None = None,
    ) -> Any:
        """Los mismos filtros para el listado y para su conteo."""
        if sucursal_id is not None:
            query = query.where(Incidencia.sucursal_id == sucursal_id)
        if habitacion_id is not None:
            query = query.where(Incidencia.habitacion_id == habitacion_id)
        if estados:
            query = query.where(Incidencia.estado.in_(list(estados)))
        if prioridad:
            query = query.where(Incidencia.prioridad == prioridad)
        if desde is not None:
            query = query.where(Incidencia.reportada_en >= desde)
        if hasta is not None:
            query = query.where(Incidencia.reportada_en < hasta)
        if texto_busqueda:
            patron = f"%{texto_busqueda.strip()}%"
            query = query.where(
                Incidencia.folio.ilike(patron)
                | Incidencia.titulo.ilike(patron)
                | Incidencia.habitacion_numero.ilike(patron)
            )
        return query

    async def incidencias(
        self,
        *,
        sucursal_id: int | None = None,
        habitacion_id: int | None = None,
        estados: Sequence[str] | None = None,
        prioridad: str | None = None,
        desde: datetime | None = None,
        hasta: datetime | None = None,
        texto_busqueda: str | None = None,
        limite: int = 300,
    ) -> list[Incidencia]:
        query = self._filtrar_incidencias(
            select(Incidencia),
            sucursal_id=sucursal_id,
            habitacion_id=habitacion_id,
            estados=estados,
            prioridad=prioridad,
            desde=desde,
            hasta=hasta,
            texto_busqueda=texto_busqueda,
        )
        orden_estado = func.array_position(
            text("ARRAY['reportada','en_atencion','cerrada','anulada']::varchar[]"),
            Incidencia.estado,
        )
        query = query.order_by(orden_estado, Incidencia.reportada_en.desc()).limit(limite)
        return await self._todas(query)

    async def conteo_incidencias(
        self,
        *,
        sucursal_id: int | None = None,
        desde: datetime | None = None,
        hasta: datetime | None = None,
        texto_busqueda: str | None = None,
    ) -> list[tuple[str, str, int]]:
        """Cuántos folios hay por (estado, prioridad), sin el tope del listado."""
        query = self._filtrar_incidencias(
            select(Incidencia.estado, Incidencia.prioridad, func.count()),
            sucursal_id=sucursal_id,
            desde=desde,
            hasta=hasta,
            texto_busqueda=texto_busqueda,
        ).group_by(Incidencia.estado, Incidencia.prioridad)
        return [(e, p, n) for e, p, n in (await self.session.execute(query)).all()]

    async def abiertas_por_habitacion(self, sucursal_id: int | None) -> dict[int, int]:
        query = (
            select(Incidencia.habitacion_id, func.count())
            .where(Incidencia.estado.in_(ABIERTAS))
            .group_by(Incidencia.habitacion_id)
        )
        if sucursal_id is not None:
            query = query.where(Incidencia.sucursal_id == sucursal_id)
        return {h: n for h, n in (await self.session.execute(query)).all()}

    async def folios(self, ids: Sequence[int]) -> dict[int, Incidencia]:
        if not ids:
            return {}
        filas = await self._todas(select(Incidencia).where(Incidencia.id.in_(list(set(ids)))))
        return {f.id: f for f in filas}

    async def eventos(self, incidencia_id: int) -> list[EventoIncidencia]:
        query = (
            select(EventoIncidencia)
            .where(EventoIncidencia.incidencia_id == incidencia_id)
            .order_by(EventoIncidencia.fecha, EventoIncidencia.id)
        )
        return await self._todas(query)

    # -- evidencias ------------------------------------------------------

    async def evidencias_de_revision(self, revision_id: int) -> list[Evidencia]:
        query = (
            select(Evidencia)
            .where(Evidencia.revision_id == revision_id)
            .order_by(Evidencia.creada_en)
        )
        return await self._todas(query)

    async def evidencias_de_incidencia(self, incidencia_id: int) -> list[Evidencia]:
        query = (
            select(Evidencia)
            .where(Evidencia.incidencia_id == incidencia_id)
            .order_by(Evidencia.creada_en)
        )
        return await self._todas(query)

    async def evidencias_de_punto(self, revision_id: int, codigo: str) -> list[Evidencia]:
        query = select(Evidencia).where(
            Evidencia.revision_id == revision_id, Evidencia.codigo_punto == codigo
        )
        return await self._todas(query)

    async def evidencia(self, evidencia_id: int) -> Evidencia:
        fila = await self.session.get(Evidencia, evidencia_id)
        if fila is None:
            raise NotFoundError(f"la evidencia {evidencia_id} no existe")
        return fila

    async def borrar(self, fila: Any) -> None:
        await self.session.delete(fila)
        await self.session.flush()

    # -- renta -----------------------------------------------------------

    async def decisiones(
        self, habitacion_id: int, *, desde: datetime | None = None
    ) -> list[DecisionRenta]:
        query = select(DecisionRenta).where(DecisionRenta.habitacion_id == habitacion_id)
        if desde is not None:
            query = query.where(DecisionRenta.decidida_en >= desde)
        return await self._todas(query.order_by(DecisionRenta.decidida_en.desc()))

    async def rentas_vigentes(self, sucursal_id: int | None) -> dict[int, DecisionRenta]:
        sub = select(
            DecisionRenta.id,
            func.row_number()
            .over(
                partition_by=DecisionRenta.habitacion_id, order_by=DecisionRenta.decidida_en.desc()
            )
            .label("n"),
        )
        if sucursal_id is not None:
            sub = sub.where(DecisionRenta.sucursal_id == sucursal_id)
        sub_q = sub.subquery()
        query = select(DecisionRenta).join(
            sub_q, and_(sub_q.c.id == DecisionRenta.id, sub_q.c.n == 1)
        )
        return {d.habitacion_id: d for d in await self._todas(query)}
