"""Lo que consultan los propietarios: panel, indicadores y expediente de habitación.

Los indicadores siguen la definición acordada:
- Cumplimiento de revisión: completas / exigibles, por puesto y frecuencia.
- Conformidad de puntos: Bien / (Bien + Falla); No aplica y Sin revisar aparte.
- Tiempo de solución: de la apertura al cierre; y antigüedad de los abiertos.
- Reincidencia: la misma categoría en la misma habitación dentro del periodo.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date

from jfastframework.errors import NotFoundError

from modules.sucursal import public as sucursal_publica
from shared.enums import Rol

from ..enums import ABIERTAS, EstadoIncidencia, Resultado
from ..models import (
    Actor,
    DecisionRead,
    FilaSucursal,
    HabitacionExpediente,
    IncidenciaResumen,
    Indicadores,
    IndicadorSucursal,
    Panel,
    Periodo,
    Reincidencia,
)
from ..repositories import InspeccionRepository
from ..validations import (
    completas_gerente,
    conformidad,
    exigibles_ama,
    exigibles_gerente,
    exigir_sucursal,
    horas,
    proporcion,
)
from .comun import (
    ahora,
    amenidades,
    decision_read,
    fecha_local,
    rango_utc,
    resultado_read,
    resumen_revision,
)


class ReporteService:
    def __init__(self, repo: InspeccionRepository) -> None:
        self.repo = repo

    async def _filas(self, actor: Actor, p: Periodo) -> list[FilaSucursal]:
        session = self.repo.session
        sucursales = await sucursal_publica.sucursales(session, tenant_id=None)
        if not actor.ve_todas:
            sucursales = [s for s in sucursales if s.id == actor.sucursal_id]
        habitaciones = await sucursal_publica.habitaciones(
            session, tenant_id=None, sucursal_id=None
        )
        cuartos: dict[int, set[int]] = defaultdict(set)
        for h in habitaciones:
            cuartos[h.sucursal_id].add(h.id)

        inicio, fin = rango_utc(p.desde, p.hasta)
        revisiones = await self.repo.revisiones(desde=inicio, hasta=fin, limite=100_000)
        abiertas = await self.repo.incidencias(estados=[e.value for e in ABIERTAS], limite=100_000)
        rentas = await self.repo.rentas_vigentes(None)
        chequeos = await self.repo.ultimo_chequeo_por_sucursal()

        filas = []
        for s in sucursales:
            propias = [
                r for r in revisiones if r.sucursal_id == s.id and r.habitacion_id in cuartos[s.id]
            ]
            fechas: dict[int, list[date]] = defaultdict(list)
            for r in propias:
                if r.rol == Rol.GERENTE and r.estado == "completa" and r.completada_en:
                    fechas[r.habitacion_id].append(fecha_local(r.completada_en))
            ama = [r for r in propias if r.rol == Rol.AMA_LLAVES]
            g_exig = exigibles_gerente(
                len(cuartos[s.id]), p.desde, p.hasta, s.frecuencia_gerente_dias
            )
            a_exig = exigibles_ama(s.ama_exigible, len(cuartos[s.id]), p.desde, p.hasta, len(ama))
            filas.append(
                FilaSucursal(
                    sucursal_id=s.id,
                    clave=s.clave,
                    nombre=s.nombre,
                    foto=s.foto,
                    habitaciones=len(cuartos[s.id]),
                    gerente_completas=min(
                        completas_gerente(fechas, p.desde, s.frecuencia_gerente_dias), g_exig
                    ),
                    gerente_exigibles=g_exig,
                    ama_completas=min(sum(1 for r in ama if r.estado == "completa"), a_exig),
                    ama_exigibles=a_exig,
                    abiertas=sum(1 for i in abiertas if i.sucursal_id == s.id),
                    no_rentar=sum(
                        1
                        for hid, d in rentas.items()
                        if hid in cuartos[s.id] and not d.puede_rentarse
                    ),
                    ultimo_chequeo=chequeos.get(s.id),
                )
            )
        return filas

    async def panel(self, actor: Actor, p: Periodo) -> Panel:
        filas = await self._filas(actor, p)
        return Panel(
            corte=ahora(),
            periodo=p,
            completas=sum(f.gerente_completas + f.ama_completas for f in filas),
            exigibles=sum(f.gerente_exigibles + f.ama_exigibles for f in filas),
            abiertas=sum(f.abiertas for f in filas),
            bloqueados=sum(f.no_rentar for f in filas),
            sucursales=filas,
        )

    async def indicadores(self, actor: Actor, p: Periodo) -> Indicadores:
        filas = await self._filas(actor, p)
        visibles = {f.sucursal_id for f in filas}
        inicio, fin = rango_utc(p.desde, p.hasta)
        conteo: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for sid, resultado, n in await self.repo.resultados_del_periodo(inicio, fin):
            if sid in visibles:
                conteo[sid][resultado] += n

        todas = [
            i
            for i in await self.repo.incidencias(desde=None, limite=100_000)
            if i.sucursal_id in visibles
        ]
        momento = ahora()
        cerradas = [
            i
            for i in todas
            if i.estado == EstadoIncidencia.CERRADA
            and i.cerrada_en
            and inicio <= i.cerrada_en < fin
        ]
        abiertas = [i for i in todas if i.estado in ABIERTAS]

        def indicador(sid: int, nombre: str, grupo: list[FilaSucursal]) -> IndicadorSucursal:
            ids = {f.sucursal_id for f in grupo}
            c: dict[str, int] = defaultdict(int)
            for s in ids:
                for k, v in conteo[s].items():
                    c[k] += v
            mis_cerradas = [i for i in cerradas if i.sucursal_id in ids]
            mis_abiertas = [i for i in abiertas if i.sucursal_id in ids]
            tiempos = [horas(i.reportada_en, i.cerrada_en) for i in mis_cerradas if i.cerrada_en]
            return IndicadorSucursal(
                sucursal_id=sid,
                nombre=nombre,
                cumplimiento_gerente=proporcion(
                    sum(f.gerente_completas for f in grupo), sum(f.gerente_exigibles for f in grupo)
                ),
                cumplimiento_ama=proporcion(
                    sum(f.ama_completas for f in grupo), sum(f.ama_exigibles for f in grupo)
                ),
                bien=c[Resultado.BIEN],
                fallas=c[Resultado.FALLA],
                no_aplica=c[Resultado.NO_APLICA],
                sin_revisar=c[Resultado.SIN_REVISAR],
                conformidad=conformidad(c[Resultado.BIEN], c[Resultado.FALLA]),
                cerradas=len(mis_cerradas),
                horas_solucion_promedio=round(sum(tiempos) / len(tiempos), 1) if tiempos else None,
                abiertas=len(mis_abiertas),
                horas_abiertas_max=max(
                    (horas(i.reportada_en, momento) for i in mis_abiertas), default=None
                ),
            )

        grupos: dict[tuple[int, str, str], list[str]] = defaultdict(list)
        nombres: dict[int, tuple[str, str]] = {}
        for i in todas:
            if i.estado == EstadoIncidencia.ANULADA or not (inicio <= i.reportada_en < fin):
                continue
            grupos[(i.habitacion_id, i.categoria, i.sucursal_nombre)].append(i.folio)
            nombres[i.habitacion_id] = (i.sucursal_nombre, i.habitacion_numero)
        reincidencias = sorted(
            (
                Reincidencia(
                    sucursal_nombre=suc,
                    habitacion_id=hid,
                    habitacion_numero=nombres[hid][1],
                    categoria=cat,
                    veces=len(folios),
                    folios=sorted(folios),
                )
                for (hid, cat, suc), folios in grupos.items()
                if len(folios) >= 2
            ),
            key=lambda r: -r.veces,
        )
        sucursal_id = actor.sucursal_id if not actor.ve_todas else None
        frecuentes = [
            {"codigo": c, "titulo": t, "veces": n}
            for c, t, n in await self.repo.fallas_por_punto(inicio, fin, sucursal_id)
        ]
        return Indicadores(
            periodo=p,
            total=indicador(0, "Grupo Picasso", filas),
            sucursales=[indicador(f.sucursal_id, f.nombre, [f]) for f in filas],
            reincidencias=reincidencias[:20],
            fallas_frecuentes=frecuentes,  # type: ignore[arg-type]
        )

    async def expediente(self, actor: Actor, habitacion_id: int) -> HabitacionExpediente:
        """Últimas revisiones de ambos puestos, pendientes, folios y renta."""
        session = self.repo.session
        habitacion = await sucursal_publica.habitacion(
            session, tenant_id=None, habitacion_id=habitacion_id
        )
        if habitacion is None:
            raise NotFoundError(f"la habitación {habitacion_id} no existe")
        exigir_sucursal(actor, habitacion.sucursal_id)
        sucursal = next(
            (
                s
                for s in await sucursal_publica.sucursales(session, tenant_id=None)
                if s.id == habitacion.sucursal_id
            ),
            None,
        )
        revisiones = await self.repo.revisiones(habitacion_id=habitacion_id, limite=30)
        conteos = await self.repo.conteo_resultados([r.id for r in revisiones])
        en_curso = [r for r in revisiones if r.estado == "en_curso"]
        resultados = await self.repo.resultados([r.id for r in en_curso])
        pendientes = [
            resultado_read(f, {}) for f in resultados if f.resultado == Resultado.SIN_REVISAR
        ]
        incidencias = await self.repo.incidencias(habitacion_id=habitacion_id, limite=50)
        decisiones = await self.repo.decisiones(habitacion_id)
        return HabitacionExpediente(
            habitacion_id=habitacion.id,
            sucursal_id=habitacion.sucursal_id,
            sucursal_nombre=sucursal.nombre if sucursal else "",
            numero=habitacion.numero,
            amenidades=amenidades(habitacion),
            revisiones=[resumen_revision(r, conteos.get(r.id)) for r in revisiones],
            pendientes=pendientes,
            incidencias=[
                IncidenciaResumen.model_validate(i, from_attributes=True)
                for i in incidencias
                if i.estado != EstadoIncidencia.ANULADA
            ],
            renta=decision_read(decisiones[0] if decisiones else None),
            decisiones=[
                DecisionRead.model_validate(d, from_attributes=True) for d in decisiones[:20]
            ],
        )
