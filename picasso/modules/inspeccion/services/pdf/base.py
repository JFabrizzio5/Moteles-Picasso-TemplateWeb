"""Estilo común de los reportes PDF: la marca de motelpicasso.mx en papel.

Banda negra arriba con el logo blanco, coral para etiquetas, texto casi negro,
tablas con renglones alternados y los mismos colores de resultado que la app.
Pie en cada página: "Picasso · Inspecciones · generado el … · página N de M".

Todo aquí es síncrono y de CPU: quien lo llama lo corre en un hilo.
"""

from __future__ import annotations

import io
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from functools import partial
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from PIL import Image as PilImage
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    Flowable,
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from ..comun import ZONA

LOGO = Path(__file__).resolve().parents[4] / "assets" / "picasso-logo-blanco.png"

NEGRO = colors.HexColor("#000000")
TEXTO = colors.HexColor("#1e1e1e")
TEXTO_2 = colors.HexColor("#555555")
TEXTO_3 = colors.HexColor("#8c8c8c")
CORAL = colors.HexColor("#fe7877")
CORAL_TEXTO = colors.HexColor("#c0392b")
LINEA = colors.HexColor("#e4e4e4")
RENGLON = colors.HexColor("#f4f4f4")
BLANCO = colors.white

COLOR_RESULTADO = {
    "bien": colors.HexColor("#2e7d4f"),
    "falla": colors.HexColor("#c0392b"),
    "no_aplica": colors.HexColor("#b7791f"),
    "sin_revisar": colors.HexColor("#6b6b6b"),
}
TEXTO_RESULTADO = {
    "bien": "Bien",
    "falla": "Falla",
    "no_aplica": "No aplica",
    "sin_revisar": "Sin revisar",
}
COLOR_ESTADO = {
    "reportada": colors.HexColor("#c0392b"),
    "en_atencion": colors.HexColor("#b7791f"),
    "cerrada": colors.HexColor("#2e7d4f"),
    "anulada": colors.HexColor("#6b6b6b"),
}
TEXTO_ESTADO = {
    "reportada": "Reportada",
    "en_atencion": "En atención",
    "cerrada": "Cerrada",
    "anulada": "Anulada",
}
ROLES = {
    "admin": "Administración",
    "propietario": "Propietarios",
    "gerente": "Gerente",
    "ama_llaves": "Ama de llaves",
}
PRIORIDADES = {"alta": "Prioridad alta", "media": "Prioridad media", "baja": "Prioridad baja"}

MARGEN = 40
BANDA = 62
ANCHO_UTIL = letter[0] - 2 * MARGEN

MESES = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")


# -- fechas y texto ---------------------------------------------------------------


def fecha(momento: datetime | date | None) -> str:
    if momento is None:
        return "—"
    if isinstance(momento, datetime):
        momento = momento.astimezone(ZONA)
    return f"{momento.day:02d} {MESES[momento.month - 1]} {momento.year}"


def fecha_hora(momento: datetime | None) -> str:
    if momento is None:
        return "—"
    local = momento.astimezone(ZONA)
    return f"{fecha(local)}, {local:%H:%M}"


def t(texto: object) -> str:
    """Texto del usuario listo para un Paragraph (escapa <, > y &)."""
    return escape("" if texto is None else str(texto))


def pct(valor: float | None) -> str:
    return "—" if valor is None else f"{round(valor * 100)}\u00a0%"


def horas(valor: float | None) -> str:
    if valor is None:
        return "—"
    return f"{valor:g}\u00a0h" if valor < 48 else f"{round(valor / 24)}\u00a0días"


# -- estilos ------------------------------------------------------------------------


def _estilo(nombre: str, **kw: Any) -> ParagraphStyle:
    base: dict[str, Any] = {
        "fontName": "Helvetica",
        "fontSize": 9.5,
        "leading": 13,
        "textColor": TEXTO,
    }
    base.update(kw)
    return ParagraphStyle(nombre, **base)


ETIQUETA = _estilo(
    "etiqueta", fontName="Helvetica-Bold", fontSize=7.5, leading=10, textColor=CORAL_TEXTO
)
TITULO = _estilo("titulo", fontSize=24, leading=28, spaceAfter=2)
SUBTITULO = _estilo("subtitulo", fontSize=10, leading=14, textColor=TEXTO_2)
SECCION = _estilo("seccion", fontSize=15, leading=19, spaceBefore=14, spaceAfter=6)
CUERPO = _estilo("cuerpo")
NEGRITA = _estilo("negrita", fontName="Helvetica-Bold")
CHICO = _estilo("chico", fontSize=8, leading=10.5, textColor=TEXTO_2)
SIN_FOTO = _estilo("sin_foto", fontSize=8, leading=10.5, textColor=TEXTO_3, alignment=1)
CELDA = _estilo("celda", fontSize=8.5, leading=11)
CELDA_NEGRITA = _estilo("celda_negrita", fontName="Helvetica-Bold", fontSize=8.5, leading=11)
CABECERA = _estilo(
    "cabecera", fontName="Helvetica-Bold", fontSize=7.5, leading=10, textColor=BLANCO
)
CIFRA = _estilo("cifra", fontSize=22, leading=26)


def p(texto: str, estilo: ParagraphStyle = CUERPO) -> Paragraph:
    return Paragraph(texto, estilo)


def etiqueta(texto: str) -> Paragraph:
    return Paragraph(t(texto.upper()), ETIQUETA)


def encabezado(etiqueta_texto: str, titulo: str, subtitulo: str = "") -> list[Flowable]:
    bloque: list[Flowable] = [etiqueta(etiqueta_texto), Spacer(1, 4), p(t(titulo), TITULO)]
    if subtitulo:
        bloque.append(p(subtitulo, SUBTITULO))
    bloque.append(Spacer(1, 12))
    return bloque


def seccion(titulo: str) -> Paragraph:
    return Paragraph(t(titulo), SECCION)


# -- piezas -------------------------------------------------------------------------


class Chip(Flowable):  # type: ignore[misc]
    """Una pastilla de color con texto blanco, como los estados de la app."""

    def __init__(self, texto: str, color: colors.Color, tamano: float = 7.5) -> None:
        super().__init__()
        self.texto = texto
        self.color = color
        self.tamano = tamano
        self.width = stringWidth(texto, "Helvetica-Bold", tamano) + 12
        self.height = tamano + 7

    def wrap(self, *_: Any) -> tuple[float, float]:
        return self.width, self.height

    def draw(self) -> None:
        c = self.canv
        c.setFillColor(self.color)
        c.roundRect(0, 0, self.width, self.height, self.height / 2, stroke=0, fill=1)
        c.setFillColor(BLANCO)
        c.setFont("Helvetica-Bold", self.tamano)
        c.drawCentredString(self.width / 2, 4, self.texto)


def chip_resultado(resultado: str) -> Chip:
    return Chip(TEXTO_RESULTADO.get(resultado, resultado), COLOR_RESULTADO.get(resultado, TEXTO_3))


def chip_estado(estado: str) -> Chip:
    return Chip(TEXTO_ESTADO.get(estado, estado), COLOR_ESTADO.get(estado, TEXTO_3))


def tabla(
    filas: Sequence[Sequence[Any]],
    anchos: Sequence[float],
    *,
    cabecera: bool = True,
    total: bool = False,
) -> Table:
    """Tabla de la marca: cabecera negra, renglones alternados, total en negritas."""
    datos = [list(f) for f in filas]
    if cabecera:
        datos[0] = [
            Paragraph(t(str(x).upper()), CABECERA) if isinstance(x, str) else x for x in datos[0]
        ]
    tbl = Table(datos, colWidths=list(anchos), repeatRows=1 if cabecera else 0)
    estilo: list[tuple[Any, ...]] = [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("TEXTCOLOR", (0, 0), (-1, -1), TEXTO),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINEA),
    ]
    inicio = 0
    if cabecera:
        estilo += [("BACKGROUND", (0, 0), (-1, 0), NEGRO), ("TEXTCOLOR", (0, 0), (-1, 0), BLANCO)]
        inicio = 1
    for i in range(inicio, len(datos)):
        if (i - inicio) % 2 == 0:
            estilo.append(("BACKGROUND", (0, i), (-1, i), RENGLON))
    if total:
        estilo += [
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("LINEABOVE", (0, -1), (-1, -1), 0.8, TEXTO),
            ("BACKGROUND", (0, -1), (-1, -1), BLANCO),
        ]
    tbl.setStyle(TableStyle(estilo))
    return tbl


def tarjetas(cifras: Sequence[tuple[str, str, colors.Color]]) -> Table:
    """Fila de cifras grandes (valor, etiqueta, color)."""
    celdas = [
        [
            Paragraph(f'<font color="{c.hexval()}">{t(v)}</font>', CIFRA),
            Paragraph(t(e), CHICO),
        ]
        for v, e, c in cifras
    ]
    ancho = ANCHO_UTIL / len(cifras)
    tbl = Table([celdas], colWidths=[ancho] * len(cifras))
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), RENGLON),
                ("LINEAFTER", (0, 0), (-2, -1), 4, BLANCO),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ]
        )
    )
    return tbl


def caja(contenido: list[Flowable], ancho: float = ANCHO_UTIL) -> Table:
    """Un recuadro gris claro con contenido, como las tarjetas de la app."""
    tbl = Table([[contenido]], colWidths=[ancho])
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), RENGLON),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ]
        )
    )
    return tbl


# -- fotos --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FotoPdf:
    """Una foto para el reporte. `datos` en None = ya no está en el disco."""

    titulo: str
    pie: str
    datos: bytes | None


def _miniatura(datos: bytes, ancho: float, alto: float) -> Flowable:
    imagen = PilImage.open(io.BytesIO(datos)).convert("RGB")
    imagen.thumbnail((700, 700))
    salida = io.BytesIO()
    imagen.save(salida, "JPEG", quality=72)
    salida.seek(0)
    proporcion = imagen.width / imagen.height
    w, h = (ancho, ancho / proporcion) if proporcion >= ancho / alto else (alto * proporcion, alto)
    return Image(salida, width=w, height=h)


def foto(f: FotoPdf, ancho: float = 160, alto: float = 120) -> Table:
    try:
        visual: Flowable = (
            _miniatura(f.datos, ancho, alto) if f.datos else p("Foto no disponible", SIN_FOTO)
        )
    except Exception:
        visual = p("Foto no disponible", SIN_FOTO)
    celda = Table([[visual]], colWidths=[ancho], rowHeights=[alto])
    celda.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), RENGLON),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    bloque = Table(
        [[celda], [p(f"<b>{t(f.titulo)}</b>", CHICO)], [p(t(f.pie), CHICO)]],
        colWidths=[ancho],
    )
    bloque.setStyle(
        TableStyle(
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return bloque


def galeria(fotos: Sequence[FotoPdf], columnas: int = 3) -> Table | Spacer:
    if not fotos:
        return Spacer(1, 0)
    hueco = 10
    ancho = (ANCHO_UTIL - hueco * (columnas - 1)) / columnas
    celdas = [foto(f, ancho, ancho * 0.72) for f in fotos]
    filas: list[list[Any]] = []
    for i in range(0, len(celdas), columnas):
        fila: list[Any] = celdas[i : i + columnas]
        fila += [""] * (columnas - len(fila))
        filas.append(fila)
    tbl = Table(
        filas, colWidths=[ancho + (hueco if i < columnas - 1 else 0) for i in range(columnas)]
    )
    tbl.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), hueco),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    return tbl


# -- página ---------------------------------------------------------------------------


class _Lienzo(canvas.Canvas):  # type: ignore[misc]
    """Dibuja banda y pie al final, cuando ya se sabe cuántas páginas hay."""

    def __init__(
        self,
        *args: Any,
        titulo: str,
        generado: datetime,
        banda: str = "Mantenimiento y limpieza",
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._paginas: list[dict[str, Any]] = []
        self._titulo = titulo
        self._generado = generado
        self._banda = banda

    def showPage(self) -> None:
        self._paginas.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        total = len(self._paginas)
        for estado in self._paginas:
            self.__dict__.update(estado)
            self._marco(total)
            super().showPage()
        super().save()

    def _marco(self, total: int) -> None:
        ancho, alto = letter
        self.saveState()
        self.setFillColor(NEGRO)
        self.rect(0, alto - BANDA, ancho, BANDA, stroke=0, fill=1)
        if LOGO.exists():
            logo = ImageReader(str(LOGO))
            lw, lh = logo.getSize()
            h = 40
            self.drawImage(
                logo, MARGEN, alto - BANDA + 11, width=h * lw / lh, height=h, mask="auto"
            )
        self.setFillColor(BLANCO)
        self.setFont("Helvetica-Bold", 7.5)
        self.drawRightString(ancho - MARGEN, alto - 30, self._titulo.upper())
        self.setFillColor(CORAL)
        self.setFont("Helvetica", 7.5)
        self.drawRightString(ancho - MARGEN, alto - 42, self._banda.upper())
        self.setFillColor(TEXTO_3)
        self.setFont("Helvetica", 7.5)
        self.drawString(
            MARGEN,
            24,
            f"Picasso · Inspecciones · generado el {fecha_hora(self._generado)} (hora de CDMX)",
        )
        self.drawRightString(ancho - MARGEN, 24, f"página {self._pageNumber} de {total}")
        self.setStrokeColor(LINEA)
        self.setLineWidth(0.5)
        self.line(MARGEN, 36, ancho - MARGEN, 36)
        self.restoreState()


def documento(
    titulo: str,
    generado: datetime,
    contenido: Callable[[], list[Flowable]],
    *,
    asunto: str = "",
    banda: str = "Mantenimiento y limpieza",
) -> bytes:
    """Arma el PDF completo y devuelve sus bytes."""
    salida = io.BytesIO()
    doc = SimpleDocTemplate(
        salida,
        pagesize=letter,
        leftMargin=MARGEN,
        rightMargin=MARGEN,
        topMargin=BANDA + 26,
        bottomMargin=54,
        title=titulo,
        author="Motel Picasso",
        subject=asunto or titulo,
        creator="Picasso · Inspecciones",
    )
    doc.build(
        contenido(), canvasmaker=partial(_Lienzo, titulo=titulo, generado=generado, banda=banda)
    )
    return salida.getvalue()
