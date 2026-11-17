"""Lectura de las respuestas de Kairos (vista móvil, `/kairos/mobil/`).

Kairos no tiene API: su vista móvil pide pedazos de HTML por día
(`ActualizaHome`, `Ventas`…) y dos gráficas en JSON (`UpdateGraphVts`,
`UpdateGraphGts`). Aquí solo se interpreta lo que llega, sin red, para poder
probarlo con ejemplos. Si Kairos cambia su HTML, lo que se rompe está aquí.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from typing import Any

_DINERO = re.compile(r"\$\s*(-?[\d,]*\.?\d*)")


def dinero(texto: str) -> Decimal:
    """«$ 1,000.00» → 1000.00; «$ .00» → 0."""
    m = _DINERO.search(texto or "")
    crudo = (m.group(1) if m else texto or "").replace(",", "").strip()
    if crudo in ("", ".", "-"):
        return Decimal("0.00")
    try:
        return Decimal(crudo).quantize(Decimal("0.01"))
    except InvalidOperation:
        return Decimal("0.00")


def entero(texto: str) -> int:
    m = re.search(r"-?\d+", texto or "")
    return int(m.group(0)) if m else 0


def fecha_kairos(dia: date) -> str:
    """Kairos pide las fechas como dd/mm/aaaa."""
    return dia.strftime("%d/%m/%Y")


# -- tablas ----------------------------------------------------------------------


@dataclass
class Fila:
    attrs: dict[str, str]
    celdas: list[str] = field(default_factory=list)

    @property
    def clases(self) -> set[str]:
        return set((self.attrs.get("class") or "").split())


class _Tablas(HTMLParser):
    """Cada <table> como lista de filas con sus atributos y el texto de cada celda."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tablas: list[list[Fila]] = []
        self._pila: list[list[Fila]] = []
        self._fila: Fila | None = None
        self._celda: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table":
            self._pila.append([])
        elif tag == "tr" and self._pila:
            self._fila = Fila({k: v or "" for k, v in attrs})
            self._pila[-1].append(self._fila)
        elif tag in ("td", "th") and self._fila is not None:
            self._celda = []

    def handle_endtag(self, tag: str) -> None:
        if tag in ("td", "th") and self._celda is not None and self._fila is not None:
            self._fila.celdas.append(" ".join("".join(self._celda).split()))
            self._celda = None
        elif tag == "tr":
            self._fila = None
        elif tag == "table" and self._pila:
            self.tablas.append(self._pila.pop())

    def handle_data(self, data: str) -> None:
        if self._celda is not None:
            self._celda.append(data)


def tablas(html: str) -> list[list[Fila]]:
    lector = _Tablas()
    lector.feed(html)
    lector.close()
    return lector.tablas


def _texto(html: str) -> str:
    sin_scripts = re.sub(r"<(script|style)\b.*?</\1>", " ", html, flags=re.S | re.I)
    sin_comentarios = re.sub(r"<!--.*?-->", " ", sin_scripts, flags=re.S)
    return " ".join(re.sub(r"<[^>]+>", " ", sin_comentarios).split())


# -- resumen del día (ActualizaHome) ----------------------------------------------


@dataclass(frozen=True)
class ResumenDia:
    habitaciones: Decimal
    rentas: int
    extras: Decimal
    extras_n: int
    room_service: Decimal
    comandas: int
    gastos: Decimal
    gastos_n: int
    total: Decimal

    @property
    def vacio(self) -> bool:
        return not (self.rentas or self.extras_n or self.comandas or self.gastos_n or self.total)


class KairosNoEntendido(ValueError):
    """La respuesta no tiene la forma esperada: Kairos cambió o pidió entrar de nuevo."""


def leer_resumen(html: str) -> ResumenDia:
    texto = _texto(html)

    def monto(etiqueta: str) -> Decimal:
        m = re.search(rf"{etiqueta}\s*\$\s*(-?[\d,]*\.?\d*)", texto, flags=re.I)
        if m is None:
            raise KairosNoEntendido(f"No encontré «{etiqueta}» en el resumen del día.")
        return dinero("$ " + m.group(1))

    def cuenta(etiqueta: str) -> int:
        m = re.search(rf"{etiqueta}\s*\((\d+)\)", texto, flags=re.I)
        return int(m.group(1)) if m else 0

    return ResumenDia(
        habitaciones=monto("Habitaciones"),
        rentas=cuenta("Ver Ventas"),
        extras=monto("Ingresos Extras"),
        extras_n=cuenta("Ver Extras"),
        room_service=monto("Room Service"),
        comandas=cuenta("Ver Comandas"),
        gastos=monto("Gastos"),
        gastos_n=cuenta("Ver Gastos"),
        total=monto(r"Total"),
    )


# -- ventas del día (Ventas) -------------------------------------------------------


@dataclass(frozen=True)
class Tarifa:
    tarifa: str
    cantidad: int
    importe: Decimal


@dataclass(frozen=True)
class RentaKairos:
    renglon: int
    folio: str
    habitacion: str
    forma_pago: str
    importe: Decimal
    #: Kairos marca cada renta con milisegundos desde 1970 (data-fecha).
    entrada: datetime | None


@dataclass(frozen=True)
class VentasDia:
    tarifas: list[Tarifa]
    total_tarifas: Decimal
    rentas: list[RentaKairos]
    total_rentas: Decimal


def _encabezados(filas: list[Fila]) -> list[str]:
    return [c.lower() for c in filas[0].celdas] if filas else []


def leer_ventas(html: str) -> VentasDia:
    todas = tablas(html)
    tarifas: list[Tarifa] = []
    total_tarifas = Decimal("0.00")
    rentas: list[RentaKairos] = []
    total_rentas = Decimal("0.00")
    vistas = 0
    for filas in todas:
        cab = _encabezados(filas)
        if cab[:3] == ["tarifa", "cant.", "importe"]:
            vistas += 1
            for f in filas[1:]:
                if len(f.celdas) < 3:
                    continue
                if f.celdas[0].upper() == "TOTAL":
                    total_tarifas = dinero(f.celdas[2])
                    continue
                tarifas.append(Tarifa(f.celdas[0], entero(f.celdas[1]), dinero(f.celdas[2])))
        elif "folio" in cab and "hab." in cab and "forma pago" in cab:
            vistas += 1
            marca: dict[int, datetime] = {}
            # La marca de tiempo va en la fila plegable que sigue a cada renta.
            for i, f in enumerate(filas):
                ms = f.attrs.get("data-fecha")
                if ms and ms.isdigit() and i > 0:
                    marca[i - 1] = datetime.fromtimestamp(int(ms) / 1000, tz=UTC)
            for i, f in enumerate(filas[1:], start=1):
                if f.celdas and f.celdas[0].upper() == "TOTAL" and len(f.celdas) >= 2:
                    total_rentas = dinero(f.celdas[1])
                    continue
                if "emitida" not in f.clases and not (len(f.celdas) >= 5 and f.celdas[0].isdigit()):
                    continue
                c = f.celdas
                rentas.append(
                    RentaKairos(
                        renglon=entero(c[0]),
                        folio=c[1].strip(),
                        habitacion=c[2].strip(),
                        forma_pago=c[3].strip().upper(),
                        importe=dinero(c[4]),
                        entrada=marca.get(i),
                    )
                )
    if vistas == 0 and "Sin " not in html:
        raise KairosNoEntendido("La respuesta de ventas no trae las tablas esperadas.")
    return VentasDia(tarifas, total_tarifas, rentas, total_rentas)


# -- gráficas (UpdateGraphVts) -------------------------------------------------------


def leer_serie_ventas(datos: dict[str, Any], desde: date) -> dict[date, int]:
    """Rentas por día de la gráfica de ventas. El arreglo empieza en `desde`."""
    serie = datos.get("ventas")
    if not isinstance(serie, list):
        raise KairosNoEntendido("La gráfica de ventas no trae el arreglo «ventas».")
    return {desde + timedelta(days=i): int(v or 0) for i, v in enumerate(serie)}


def es_pantalla_de_entrada(html: str) -> bool:
    """Kairos regresa el formulario de entrada cuando la sesión ya no sirve."""
    return 'name="password"' in html and "LoginMobil" in html
