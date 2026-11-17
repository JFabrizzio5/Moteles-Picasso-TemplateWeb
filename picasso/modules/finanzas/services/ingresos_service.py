"""Ingresos: se leen de Kairos y se consultan junto con los gastos.

Kairos es la fuente de verdad. Cada día importado se pisa entero con lo último
que diga Kairos, así una corrección en recepción llega en la siguiente lectura.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from jfastframework.errors import ValidationError

from ..models import (
    Actor,
    FilaSucursalFinanzas,
    FuenteKairos,
    IngresoDia,
    IngresoTarifa,
    PuntoSerie,
    Renta,
    ResumenFinanzas,
    SerieFinanzas,
    TarifaRead,
)
from ..repositories import FinanzasRepository
from ..validations import exigir_finanzas, rango, sucursal_visible
from .comun import ahora, hoy
from .kairos_cliente import ClienteKairos, KairosError
from .kairos_html import TipoCuarto, tipo_mayoritario

log = logging.getLogger("picasso.finanzas")

#: Lo más viejo que se busca al rellenar el historial (Circuito existe desde 2018).
HISTORIAL_MAS_VIEJO = date(2015, 1, 1)


@dataclass
class Sucursal:
    id: int
    clave: str
    nombre: str


@dataclass
class ResultadoImportacion:
    clave: str
    dias: int = 0
    con_ventas: int = 0
    errores: list[str] = field(default_factory=list)


#: Para probar sin red: recibe la fuente y regresa un cliente.
FabricaCliente = Callable[[FuenteKairos], ClienteKairos]


class ImportadorKairos:
    def __init__(
        self,
        repo: FinanzasRepository,
        sucursales: dict[str, Sucursal],
        fabrica: FabricaCliente,
        *,
        al_terminar_dia: Callable[[], object] | None = None,
    ) -> None:
        self.repo = repo
        self.sucursales = sucursales
        self.fabrica = fabrica
        #: El worker hace commit aquí para no perder lo avanzado si algo truena.
        self.al_terminar_dia = al_terminar_dia

    async def _guardar_dia(
        self, cliente: ClienteKairos, sucursal: Sucursal, dia: date, *, detalle: bool
    ) -> bool:
        resumen = await cliente.resumen(dia)
        fila = await self.repo.ingreso_dia(sucursal.id, dia)
        if fila is None:
            fila = IngresoDia(sucursal_id=sucursal.id, fecha=dia, importado_en=ahora())
            await self.repo.agregar(fila)
        fila.habitaciones = resumen.habitaciones
        fila.rentas = resumen.rentas
        fila.extras = resumen.extras
        fila.extras_n = resumen.extras_n
        fila.room_service = resumen.room_service
        fila.comandas = resumen.comandas
        fila.gastos_kairos = resumen.gastos
        fila.gastos_kairos_n = resumen.gastos_n
        fila.total = resumen.total
        fila.importado_en = ahora()
        if detalle and resumen.rentas:
            ventas = await cliente.ventas(dia)
            await self.repo.reemplazar_detalle(
                sucursal.id,
                dia,
                [
                    IngresoTarifa(
                        sucursal_id=sucursal.id,
                        fecha=dia,
                        tarifa=t.tarifa[:80],
                        cantidad=t.cantidad,
                        importe=t.importe,
                    )
                    for t in ventas.tarifas
                ],
                [
                    Renta(
                        sucursal_id=sucursal.id,
                        fecha=dia,
                        renglon=r.renglon,
                        folio_kairos=r.folio[:20],
                        habitacion_numero=r.habitacion[:10],
                        forma_pago=r.forma_pago[:40],
                        importe=r.importe,
                        entrada=r.entrada,
                    )
                    for r in ventas.rentas
                ],
            )
            fila.con_detalle = True
        elif detalle:
            await self.repo.reemplazar_detalle(sucursal.id, dia, [], [])
            fila.con_detalle = True
        if self.al_terminar_dia is not None:
            await _esperar(self.al_terminar_dia())
        return not resumen.vacio

    async def importar(
        self,
        fuente: FuenteKairos,
        dias: list[date],
        *,
        detalle: bool = True,
    ) -> ResultadoImportacion:
        resultado = ResultadoImportacion(fuente.sucursal_clave)
        sucursal = self.sucursales.get(fuente.sucursal_clave)
        fuente.ultima_corrida = ahora()
        if sucursal is None:
            fuente.ultimo_error = f"No hay sucursal {fuente.sucursal_clave} en Picasso."
            resultado.errores.append(fuente.ultimo_error)
            return resultado
        try:
            async with self.fabrica(fuente) as cliente:
                for dia in sorted(dias):
                    if await self._guardar_dia(cliente, sucursal, dia, detalle=detalle):
                        resultado.con_ventas += 1
                    resultado.dias += 1
        except KairosError as e:
            fuente.ultimo_error = str(e)[:300]
            resultado.errores.append(fuente.ultimo_error)
            log.warning("Kairos %s: %s", fuente.sucursal_clave, e)
            return resultado
        fuente.ultimo_ok = ahora()
        fuente.ultimo_error = None
        return resultado

    async def rellenar_historial(
        self,
        fuente: FuenteKairos,
        *,
        max_dias: int,
        detalle_desde: date,
    ) -> ResultadoImportacion:
        """Trae hacia atrás los días que faltan, a lo más `max_dias` por vuelta.

        La primera vez pregunta a la gráfica de ventas (JSON, un año por petición)
        qué días tuvieron rentas, para no pedir años vacíos día por día.
        """
        resultado = ResultadoImportacion(fuente.sucursal_clave)
        sucursal = self.sucursales.get(fuente.sucursal_clave)
        if sucursal is None:
            resultado.errores.append(f"No hay sucursal {fuente.sucursal_clave} en Picasso.")
            return resultado
        ayer = hoy() - timedelta(days=1)
        hasta = (fuente.historial_desde or ayer + timedelta(days=1)) - timedelta(days=1)
        inicio = fuente.primer_dia or HISTORIAL_MAS_VIEJO
        if hasta < inicio:
            return resultado
        try:
            async with self.fabrica(fuente) as cliente:
                serie = await cliente.rentas_por_dia(inicio, hasta)
                con_rentas = sorted(d for d, n in serie.items() if n > 0)
                if fuente.primer_dia is None:
                    fuente.primer_dia = con_rentas[0] if con_rentas else None
                    if fuente.primer_dia is None:
                        fuente.historial_desde = inicio
                        return resultado
                ya = await self.repo.dias_importados(
                    sucursal.id, desde=fuente.primer_dia, hasta=hasta
                )
                pendientes = [d for d in reversed(con_rentas) if d not in ya][:max_dias]
                for dia in pendientes:
                    await self._guardar_dia(cliente, sucursal, dia, detalle=dia >= detalle_desde)
                    resultado.dias += 1
                    resultado.con_ventas += 1
                restantes = [d for d in con_rentas if d not in ya and d not in set(pendientes)]
                fuente.historial_desde = (
                    fuente.primer_dia if not restantes else min(pendientes, default=hasta)
                )
        except KairosError as e:
            fuente.ultimo_error = str(e)[:300]
            resultado.errores.append(fuente.ultimo_error)
            log.warning("Kairos %s (historial): %s", fuente.sucursal_clave, e)
        return resultado

    async def tipos_de_cuarto(
        self, fuente: FuenteKairos, *, dias: int = 14, muestras: int = 2
    ) -> dict[str, TipoCuarto]:
        """Cada cuarto que se rentó en los últimos `dias` y qué tipo es.

        Kairos no tiene un catálogo de cuartos a la vista móvil: el tipo sale de
        la tarifa con que se rentó cada uno. Se piden `muestras` rentas por
        cuarto (no todas) para no cargarle la línea al motel.
        """
        ayer = hoy() - timedelta(days=1)
        tarifas: dict[str, list[str]] = {}
        async with self.fabrica(fuente) as cliente:
            for atras in range(dias):
                ventas = await cliente.ventas(ayer - timedelta(days=atras))
                for r in ventas.rentas:
                    vistas = tarifas.setdefault(r.habitacion, [])
                    if len(vistas) >= muestras or not r.marca:
                        continue
                    tarifa = await cliente.tarifa_de_renta(r.habitacion, r.marca)
                    if tarifa:
                        vistas.append(tarifa)
        return {
            numero: tipo
            for numero, lista in tarifas.items()
            if (tipo := tipo_mayoritario(lista)) is not None
        }


async def _esperar(valor: object) -> None:
    if hasattr(valor, "__await__"):
        await valor


def _dec(valor: Decimal | int | None) -> Decimal:
    return Decimal(valor or 0).quantize(Decimal("0.01"))


class IngresosService:
    """Lo que ven las pantallas: ingresos de Kairos contra gastos de Picasso."""

    def __init__(self, repo: FinanzasRepository, sucursales: list[Sucursal]) -> None:
        self.repo = repo
        self.sucursales = {s.id: s for s in sucursales}

    async def dias(
        self, actor: Actor, *, desde: date, hasta: date, sucursal_id: int | None
    ) -> list[IngresoDia]:
        rango(desde, hasta)
        return await self.repo.ingresos(
            desde=desde, hasta=hasta, sucursal_id=sucursal_visible(actor, sucursal_id)
        )

    async def tarifas(
        self, actor: Actor, *, desde: date, hasta: date, sucursal_id: int | None
    ) -> list[TarifaRead]:
        rango(desde, hasta)
        filas = await self.repo.tarifas(
            desde=desde, hasta=hasta, sucursal_id=sucursal_visible(actor, sucursal_id)
        )
        return [TarifaRead(tarifa=t, cantidad=n, importe=_dec(i)) for t, n, i in filas]

    async def serie(
        self, actor: Actor, *, desde: date, hasta: date, sucursal_id: int | None
    ) -> SerieFinanzas:
        """Ingresos y gastos por día, semana o mes (según lo largo del periodo)."""
        exigir_finanzas(actor)
        rango(desde, hasta)
        filtro = sucursal_visible(actor, sucursal_id)
        ingresos: dict[date, Decimal] = {}
        for fila in await self.repo.ingresos(desde=desde, hasta=hasta, sucursal_id=filtro):
            ingresos[fila.fecha] = (
                ingresos.get(fila.fecha, Decimal(0))
                + fila.habitaciones
                + fila.room_service
                + fila.extras
            )
        gastos = await self.repo.gastos_por_dia(desde=desde, hasta=hasta, sucursal_id=filtro)
        dias = (hasta - desde).days + 1
        agrupado = "dia" if dias <= 62 else "semana" if dias <= 200 else "mes"

        def tramo(d: date) -> tuple[date, date]:
            if agrupado == "dia":
                return d, d
            if agrupado == "semana":
                lunes = d - timedelta(days=d.weekday())
                return max(lunes, desde), min(lunes + timedelta(days=6), hasta)
            inicio = d.replace(day=1)
            siguiente = (inicio + timedelta(days=32)).replace(day=1)
            return max(inicio, desde), min(siguiente - timedelta(days=1), hasta)

        puntos: dict[date, PuntoSerie] = {}
        for dia in dias_entre(desde, hasta):
            a, b = tramo(dia)
            p = puntos.setdefault(
                a, PuntoSerie(inicio=a, fin=b, ingresos=Decimal(0), gastos=Decimal(0))
            )
            p.ingresos += ingresos.get(dia, Decimal(0))
            p.gastos += gastos.get(dia, Decimal(0))
        for p in puntos.values():
            p.ingresos, p.gastos = _dec(p.ingresos), _dec(p.gastos)
        return SerieFinanzas(
            desde=desde, hasta=hasta, agrupado=agrupado, puntos=list(puntos.values())
        )

    async def resumen(
        self, actor: Actor, *, desde: date, hasta: date, sucursal_id: int | None
    ) -> ResumenFinanzas:
        exigir_finanzas(actor)
        rango(desde, hasta)
        filtro = sucursal_visible(actor, sucursal_id)
        dias = await self.repo.ingresos(desde=desde, hasta=hasta, sucursal_id=filtro)
        gastos = await self.repo.suma_gastos(desde=desde, hasta=hasta, sucursal_id=filtro)
        fuentes = {f.sucursal_clave: f for f in await self.repo.fuentes()}
        filas: list[FilaSucursalFinanzas] = []
        for s in self.sucursales.values():
            if filtro is not None and s.id != filtro:
                continue
            propios = [d for d in dias if d.sucursal_id == s.id]
            habitaciones = sum((d.habitaciones for d in propios), Decimal(0))
            room = sum((d.room_service for d in propios), Decimal(0))
            extras = sum((d.extras for d in propios), Decimal(0))
            ingresos = habitaciones + room + extras
            n_gastos, total_gastos = gastos.get(s.id, (0, Decimal(0)))
            fuente = fuentes.get(s.clave)
            filas.append(
                FilaSucursalFinanzas(
                    sucursal_id=s.id,
                    clave=s.clave,
                    nombre=s.nombre,
                    dias=len(propios),
                    rentas=sum(d.rentas for d in propios),
                    habitaciones=_dec(habitaciones),
                    room_service=_dec(room),
                    extras=_dec(extras),
                    ingresos=_dec(ingresos),
                    gastos_kairos=_dec(sum((d.gastos_kairos for d in propios), Decimal(0))),
                    gastos=_dec(total_gastos),
                    gastos_n=n_gastos,
                    utilidad=_dec(ingresos - total_gastos),
                    ultimo_ok=fuente.ultimo_ok if fuente else None,
                    ultimo_error=fuente.ultimo_error if fuente else "Sin Kairos configurado.",
                )
            )
        filas.sort(key=lambda f: f.ingresos, reverse=True)
        ingresos_total = sum((f.ingresos for f in filas), Decimal(0))
        gastos_total = sum((f.gastos for f in filas), Decimal(0))
        return ResumenFinanzas(
            desde=desde,
            hasta=hasta,
            sucursales=filas,
            rentas=sum(f.rentas for f in filas),
            ingresos=_dec(ingresos_total),
            gastos=_dec(gastos_total),
            utilidad=_dec(ingresos_total - gastos_total),
        )


def dias_entre(desde: date, hasta: date) -> list[date]:
    if desde > hasta:
        raise ValidationError("La fecha inicial va antes de la final.")
    return [desde + timedelta(days=i) for i in range((hasta - desde).days + 1)]
