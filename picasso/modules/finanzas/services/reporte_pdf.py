"""Reporte PDF de finanzas por rango de fechas: para imprimir o mandar a la contadora.

Ingresos contra gastos por sucursal, la categoría más gastada, quién gasta
más, el precio de cada artículo y el detalle de cada gasto con su desglose.
Usa las mismas piezas que los reportes de inspección (banda con el logo,
tablas, pie con página). Es síncrono: quien lo llama lo corre en un hilo.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from reportlab.graphics.charts.barcharts import HorizontalBarChart, VerticalBarChart
from reportlab.graphics.charts.legends import Legend
from reportlab.graphics.shapes import Drawing, String
from reportlab.lib import colors
from reportlab.platypus import Flowable, KeepTogether, Spacer

from modules.inspeccion.public import pdf

from ..enums import NOMBRE_CATEGORIA, NOMBRE_FORMA_PAGO, FormaPago
from ..models import AnalisisGastos, GastoRead, ResumenFinanzas, SerieFinanzas

VERDE = pdf.COLOR_RESULTADO["bien"]
ROJO = pdf.CORAL_TEXTO
#: Los mismos colores de las gráficas de la app (validados para daltonismo).
AZUL_INGRESOS = colors.HexColor("#2f6db5")
VINO_GASTOS = colors.HexColor("#c0392b")
_TRAMO = {"dia": "por día", "semana": "por semana", "mes": "por mes"}
_MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def _corto(d: date) -> str:
    return f"{d.day} {_MESES[d.month - 1]}"


def _miles(v: float) -> str:
    return f"${v / 1000:,.0f}k" if abs(v) >= 1000 else f"${v:,.0f}"


def barras(
    etiquetas: Sequence[str],
    series: Sequence[tuple[str, colors.Color, Sequence[float]]],
    *,
    alto: float = 190,
    horizontal: bool = False,
) -> Drawing:
    """Barras agrupadas (una o varias series) con leyenda y eje en pesos."""
    ancho = pdf.ANCHO_UTIL
    d = Drawing(ancho, alto)
    g = HorizontalBarChart() if horizontal else VerticalBarChart()
    izquierda = 110 if horizontal else 46
    g.x, g.y = izquierda, 34 if not horizontal else 20
    g.width = ancho - izquierda - 12
    g.height = alto - (62 if not horizontal else 40)
    g.data = [list(v) for _, _, v in series] or [[0]]
    for i, (_, color, _) in enumerate(series):
        g.bars[i].fillColor = color
        g.bars[i].strokeColor = None
    g.barSpacing = 1.5
    g.groupSpacing = 6
    g.categoryAxis.categoryNames = list(etiquetas)
    g.categoryAxis.labels.fontName = "Helvetica"
    g.categoryAxis.labels.fontSize = 7
    g.categoryAxis.labels.fillColor = pdf.TEXTO_2
    g.categoryAxis.strokeColor = pdf.LINEA
    g.valueAxis.labels.fontName = "Helvetica"
    g.valueAxis.labels.fontSize = 7
    g.valueAxis.labels.fillColor = pdf.TEXTO_3
    g.valueAxis.labelTextFormat = _miles
    g.valueAxis.strokeColor = pdf.LINEA
    g.valueAxis.gridStrokeColor = pdf.LINEA
    g.valueAxis.visibleGrid = True
    g.valueAxis.valueMin = 0
    if not horizontal and len(etiquetas) > 12:
        g.categoryAxis.labels.angle = 45
        g.categoryAxis.labels.boxAnchor = "ne"
    d.add(g)
    if len(series) > 1:
        ley = Legend()
        ley.x, ley.y = izquierda, alto - 6
        ley.alignment = "right"
        ley.columnMaximum = 1
        ley.fontName = "Helvetica"
        ley.fontSize = 8
        ley.dx = ley.dy = 8
        ley.deltax = 90
        ley.colorNamePairs = [(c, n) for n, c, _ in series]
        d.add(ley)
    return d


def _vacia(texto: str) -> Drawing:
    d = Drawing(pdf.ANCHO_UTIL, 30)
    d.add(String(0, 10, texto, fontName="Helvetica", fontSize=9, fillColor=pdf.TEXTO_3))
    return d


def pesos(valor: Decimal | float | int) -> str:
    v = Decimal(valor)
    return f"{'-' if v < 0 else ''}${abs(v):,.2f}"


def pesos_cerrado(valor: Decimal | float | int) -> str:
    v = Decimal(valor)
    return f"{'-' if v < 0 else ''}${abs(v):,.0f}"


def _dia(d: date) -> str:
    return d.strftime("%d/%m/%Y")


@dataclass(frozen=True)
class DatosReporte:
    desde: date
    hasta: date
    alcance: str
    resumen: ResumenFinanzas | None
    analisis: AnalisisGastos
    gastos: Sequence[GastoRead]
    serie: SerieFinanzas | None = None


def construir_finanzas(datos: DatosReporte, generado: datetime) -> bytes:
    def contenido() -> list[Flowable]:
        a = datos.analisis
        h: list[Flowable] = pdf.encabezado(
            "Reporte de finanzas",
            datos.alcance,
            f"Del {_dia(datos.desde)} al {_dia(datos.hasta)} · ingresos de Kairos, "
            "gastos registrados en Picasso",
        )
        cifras: list[tuple[str, str, object]] = []
        if datos.resumen is not None:
            r = datos.resumen
            cifras += [
                (pesos_cerrado(r.ingresos), f"Ingresos · {r.rentas:,} rentas", VERDE),
                (pesos_cerrado(r.gastos), f"Gastos · {a.gastos} registrados", ROJO),
                (pesos_cerrado(r.utilidad), "Utilidad (ingresos menos gastos)", pdf.TEXTO),
            ]
        else:
            cifras += [(pesos_cerrado(a.total), f"Gastos · {a.gastos} registrados", ROJO)]
        if a.por_categoria:
            mayor = a.por_categoria[0]
            cifras.append(
                (
                    pesos_cerrado(mayor.total),
                    f"Categoría más gastada: {NOMBRE_CATEGORIA[mayor.categoria]}",
                    pdf.TEXTO,
                )
            )
        h.append(pdf.tarjetas(cifras))

        if datos.serie is not None and datos.serie.puntos:
            tramo = {"dia": "por día", "semana": "por semana", "mes": "por mes"}[
                datos.serie.agrupado
            ]
            h.append(pdf.seccion(f"Ingresos y gastos {tramo}"))
            pts = datos.serie.puntos
            h.append(
                barras(
                    [_corto(x.inicio) for x in pts],
                    [
                        ("Ingresos", AZUL_INGRESOS, [float(x.ingresos) for x in pts]),
                        ("Gastos", VINO_GASTOS, [float(x.gastos) for x in pts]),
                    ],
                )
            )

        if datos.resumen is not None and len(datos.resumen.sucursales) > 1:
            h.append(pdf.seccion("Ingresos y gastos por sucursal"))
            sucs = datos.resumen.sucursales
            h.append(
                barras(
                    [x.nombre.replace("Picasso ", "") for x in sucs],
                    [
                        ("Ingresos", AZUL_INGRESOS, [float(x.ingresos) for x in sucs]),
                        ("Gastos", VINO_GASTOS, [float(x.gastos) for x in sucs]),
                    ],
                    alto=170,
                )
            )
            h.append(pdf.seccion("Ingresos contra gastos por sucursal"))
            filas: list[list[object]] = [
                ["Sucursal", "Rentas", "Cuartos", "Room service", "Ingresos", "Gastos", "Utilidad"]
            ]
            for s in datos.resumen.sucursales:
                filas.append(
                    [
                        s.nombre,
                        f"{s.rentas:,}",
                        pesos_cerrado(s.habitaciones),
                        pesos_cerrado(s.room_service),
                        pesos_cerrado(s.ingresos),
                        pesos_cerrado(s.gastos),
                        pesos_cerrado(s.utilidad),
                    ]
                )
            r = datos.resumen
            filas.append(
                ["TOTAL", f"{r.rentas:,}", "", "", pesos_cerrado(r.ingresos),
                 pesos_cerrado(r.gastos), pesos_cerrado(r.utilidad)]
            )  # fmt: skip
            h.append(pdf.tabla(filas, [118, 50, 70, 74, 74, 74, 72], total=True))

        if not a.gastos:
            h.append(Spacer(1, 16))
            h.append(pdf.p("No hay gastos registrados en este periodo.", pdf.CUERPO))
            return h

        h.append(pdf.seccion("En qué se gasta"))
        cats = list(reversed(a.por_categoria))
        h.append(
            barras(
                [NOMBRE_CATEGORIA[c.categoria] for c in cats],
                [("Gastos", VINO_GASTOS, [float(c.total) for c in cats])],
                alto=26 + 20 * max(len(cats), 1),
                horizontal=True,
            )
            if cats
            else _vacia("Sin gastos.")
        )
        h.append(Spacer(1, 6))
        filas = [["Categoría", "Partidas", "Total", "% del gasto", "Por sucursal"]]
        for c in a.por_categoria:
            por_suc = " · ".join(
                f"{n.replace('Picasso ', '')} {pesos_cerrado(t)}" for n, t in c.por_sucursal.items()
            )
            filas.append(
                [
                    pdf.p(pdf.t(NOMBRE_CATEGORIA[c.categoria]), pdf.CELDA),
                    str(c.partidas),
                    pesos(c.total),
                    f"{(c.total / a.total * 100) if a.total else 0:.1f} %",
                    pdf.p(pdf.t(por_suc), pdf.CHICO),
                ]
            )
        h.append(pdf.tabla(filas, [120, 50, 74, 60, 228]))

        h.append(pdf.seccion("Quién gasta más"))
        filas = [["Persona", "Sucursal", "Gastos", "Total", "Gasta más en"]]
        for x in a.por_persona:
            filas.append(
                [
                    x.capturo_nombre,
                    x.sucursal_nombre.replace("Picasso ", ""),
                    str(x.gastos),
                    pesos(x.total),
                    NOMBRE_CATEGORIA[x.categoria_mayor] if x.categoria_mayor else "—",
                ]
            )
        h.append(pdf.tabla(filas, [150, 90, 50, 84, 158]))

        h.append(pdf.seccion("Precio por artículo"))
        h.append(
            pdf.p(
                "Los artículos con precio máximo 30 % arriba del mínimo van marcados con ▲: "
                "vale la pena preguntar por qué.",
                pdf.CHICO,
            )
        )
        h.append(Spacer(1, 4))
        filas = [["Artículo", "Veces", "Cantidad", "Total", "Promedio", "Mín · Máx"]]
        for art in a.por_articulo[:60]:
            caro = art.precio_maximo > art.precio_minimo * Decimal("1.3")
            filas.append(
                [
                    pdf.p(pdf.t(f"{art.articulo} · {NOMBRE_CATEGORIA[art.categoria]}"), pdf.CELDA),
                    str(art.veces),
                    f"{art.cantidad.normalize():f} {art.unidad}",
                    pesos(art.total),
                    f"{pesos(art.precio_promedio)}/{art.unidad}",
                    pdf.p(
                        pdf.t(f"{'▲ ' if caro else ''}{pesos(art.precio_minimo)} · "
                              f"{pesos(art.precio_maximo)}"),
                        pdf.CELDA_NEGRITA if caro else pdf.CELDA,
                    ),
                ]
            )  # fmt: skip
        h.append(pdf.tabla(filas, [176, 40, 70, 70, 84, 92]))

        h.append(pdf.seccion("Detalle de cada gasto"))
        for g in sorted(datos.gastos, key=lambda x: (x.fecha, x.id)):
            folios = ", ".join(f.folio for f in g.incidencias)
            cabeza = (
                f"<b>{pdf.t(g.folio)}</b> · {_dia(g.fecha)} · {pdf.t(g.sucursal_nombre)} · "
                f"{pdf.t(g.proveedor)} · {NOMBRE_FORMA_PAGO[FormaPago(g.forma_pago)]}"
                + (f" · folios {pdf.t(folios)}" if folios else "")
            )
            filas = [["Artículo", "Cantidad", "Precio", "Importe"]]
            for part in g.partidas:
                filas.append(
                    [
                        pdf.p(pdf.t(part.descripcion), pdf.CELDA),
                        f"{part.cantidad.normalize():f} {part.unidad}",
                        pesos(part.precio_unitario),
                        pesos(part.importe),
                    ]
                )
            filas.append([f"TOTAL · {pdf.t(g.concepto)[:60]}", "", "", pesos(g.importe)])
            h.append(
                KeepTogether(
                    [
                        pdf.p(cabeza, pdf.CELDA),
                        Spacer(1, 3),
                        pdf.tabla(filas, [262, 90, 90, 90], total=True),
                        Spacer(1, 10),
                    ]
                )
            )
        return h

    return pdf.documento(
        "Reporte de finanzas",
        generado,
        contenido,
        asunto=f"Finanzas del {_dia(datos.desde)} al {_dia(datos.hasta)}",
        banda="Finanzas",
    )
